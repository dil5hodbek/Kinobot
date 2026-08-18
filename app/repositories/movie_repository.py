"""Kinolar bilan ishlovchi repository (kod/nom qidiruv, trend, statistika)."""
from __future__ import annotations

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie
from app.models.movie_view import MovieView


class MovieRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, movie_id: int) -> Movie | None:
        result = await self._session.execute(
            select(Movie).where(Movie.id == movie_id)
        )
        return result.scalar_one_or_none()

    async def get_active_by_code(self, code: str) -> Movie | None:
        result = await self._session.execute(
            select(Movie).where(Movie.code == code, Movie.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_by_code_any(self, code: str) -> Movie | None:
        """Faol yoki nofaol — kod bandligini tekshirish uchun."""
        result = await self._session.execute(
            select(Movie).where(Movie.code == code)
        )
        return result.scalar_one_or_none()

    async def get_by_channel_message(
        self, channel_id: int, message_id: int
    ) -> Movie | None:
        """Kanal posti (channel_id + message_id) bo'yicha kino."""
        result = await self._session.execute(
            select(Movie).where(
                Movie.channel_id == channel_id, Movie.message_id == message_id
            )
        )
        return result.scalar_one_or_none()

    async def search_by_title(
        self, query: str, threshold: float, limit: int
    ) -> list[Movie]:
        """pg_trgm bo'yicha fuzzy qidiruv (3 tilda, case-insensitive, indeksli).

        Qidiruv `lower(title)` ifoda indekslari (0002 migratsiya) va trigram `%`
        operatoridan foydalanadi. Chegara joriy tranzaksiya uchun GUC orqali
        beriladi, shunda `%` bizning konfiguratsiyamizga bo'ysunadi.
        """
        q = query.strip().lower()

        # `%` operatori chegarasi (faqat float, injection xavfsiz)
        await self._session.execute(
            text(f"SET LOCAL pg_trgm.similarity_threshold = {float(threshold)}")
        )

        low_uz = func.lower(Movie.title_uz)
        low_ru = func.lower(func.coalesce(Movie.title_ru, ""))
        low_en = func.lower(func.coalesce(Movie.title_en, ""))
        best_sim = func.greatest(
            func.similarity(low_uz, q),
            func.similarity(low_ru, q),
            func.similarity(low_en, q),
        )

        stmt = (
            select(Movie)
            .where(Movie.is_active.is_(True))
            .where(
                or_(
                    low_uz.op("%")(q),
                    low_ru.op("%")(q),
                    low_en.op("%")(q),
                    low_uz.like(f"%{q}%"),
                    low_ru.like(f"%{q}%"),
                    low_en.like(f"%{q}%"),
                )
            )
            .order_by(best_sim.desc(), Movie.views_count.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_all(self, include_inactive: bool = True) -> list[Movie]:
        """Barcha kinolar (Excel hisobot uchun)."""
        stmt = select(Movie)
        if not include_inactive:
            stmt = stmt.where(Movie.is_active.is_(True))
        stmt = stmt.order_by(Movie.genre.asc().nulls_last(), Movie.code.asc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_genres(self) -> list[str]:
        """Faol kinolarda ishlatilgan barcha noyob janrlar (janr bo'yicha guruhlash uchun)."""
        result = await self._session.execute(
            select(func.distinct(Movie.genre))
            .where(Movie.is_active.is_(True), Movie.genre.is_not(None))
            .order_by(Movie.genre.asc())
        )
        return [row[0] for row in result.all()]

    async def get_by_genre(self, genre: str, limit: int = 30) -> list[Movie]:
        """Shu janrdagi faol kinolar (case-insensitive aniq moslik, eng ko'p ko'rilgani birinchi)."""
        result = await self._session.execute(
            select(Movie)
            .where(
                Movie.is_active.is_(True),
                func.lower(Movie.genre) == genre.strip().lower(),
            )
            .order_by(Movie.views_count.desc(), Movie.title_uz.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_trending(self, limit: int) -> list[Movie]:
        """Admin qo'lda belgilagan trend ro'yxati (eng yangi qo'shilgani birinchi)."""
        result = await self._session.execute(
            select(Movie)
            .where(Movie.is_active.is_(True), Movie.is_trending.is_(True))
            .order_by(Movie.trending_added_at.desc(), Movie.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_top(self, limit: int) -> list[Movie]:
        """Eng ko'p ko'rilgan kinolar (statistika uchun — trend ro'yxatidan
        mustaqil, admin qo'lda tanlagan-tanlamaganidan qat'i nazar)."""
        result = await self._session.execute(
            select(Movie)
            .where(Movie.is_active.is_(True))
            .order_by(Movie.views_count.desc(), Movie.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_trending(self) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Movie)
            .where(Movie.is_active.is_(True), Movie.is_trending.is_(True))
        )
        return int(result.scalar_one())

    # Doim shu bir xil (o'zboshimcha, lekin ilovada boshqa hech narsa
    # ishlatmaydigan) kalit bilan chaqiriladi.
    _TRENDING_LOCK_KEY = 872_634_102

    async def lock_trending(self) -> None:
        """PostgreSQL advisory-lock: shu tranzaksiya tugagunicha (commit/rollback)
        boshqa concurrent `add_to_trending` chaqiruvini bloklaydi — "hisobla,
        keyin yoz" race condition'ining oldini oladi (bir vaqtda 2 ta kino
        qo'shilib, trend chegarasi (10 ta) buzilib ketmasligi uchun)."""
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": self._TRENDING_LOCK_KEY}
        )

    async def set_trending(self, movie_id: int, trending: bool) -> None:
        await self._session.execute(
            update(Movie)
            .where(Movie.id == movie_id)
            .values(
                is_trending=trending,
                trending_added_at=func.now() if trending else None,
            )
        )

    _CODE_GEN_LOCK_KEY = 872_634_103

    async def next_auto_code(self) -> str:
        """Faqat raqamli kodlar orasidan keyingi bo'sh raqamni topadi.

        MAX+1 read-modify-write — o'z-o'zidan race'ga moyil (ikki parallel
        "auto" so'rovi bir xil raqam olishi mumkin edi; unique constraint
        oxirida ushlar edi, lekin admin UX'da tushunarsiz xato ko'rinardi).
        pg_advisory_xact_lock bilan tranzaksiya davomida serializatsiya
        qilinadi. Oddiy sequence ishlatmadik: adminlar qo'lda ixtiyoriy
        raqamli kod kiritishi mumkin (masalan 500), sequence undan orqada
        qolib doim to'qnashuv berardi.
        """
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": self._CODE_GEN_LOCK_KEY},
        )
        result = await self._session.execute(
            text(
                "SELECT COALESCE(MAX(code::bigint), 0) + 1 FROM movies "
                "WHERE code ~ '^[0-9]+$'"
            )
        )
        return str(int(result.scalar_one()))

    async def create(
        self,
        code: str,
        title_uz: str,
        title_ru: str | None,
        title_en: str | None,
        year: int | None,
        genre: str | None,
        *,
        source_type: str = "channel",
        channel_id: int | None = None,
        message_id: int | None = None,
        external_url: str | None = None,
    ) -> Movie:
        """
        Kino yaratadi. `source_type` ga qarab ikki xil kombinatsiya:
          • "channel" — channel_id + message_id SHART (copy_message uchun).
          • "link"    — external_url SHART (tashqi havola tugmasi uchun).
        Noto'g'ri kombinatsiya CHECK constraint (ck_movies_source_fields)
        bilan bazaning o'zida rad etiladi — bu yerda qo'shimcha tekshiruv
        shart emas (yagona haqiqat manbai bazada).
        """
        movie = Movie(
            code=code,
            source_type=source_type,
            channel_id=channel_id,
            message_id=message_id,
            external_url=external_url,
            title_uz=title_uz,
            title_ru=title_ru,
            title_en=title_en,
            year=year,
            genre=genre,
        )
        self._session.add(movie)
        await self._session.flush()
        return movie

    async def increment_views(self, movie_id: int) -> None:
        await self._session.execute(
            update(Movie)
            .where(Movie.id == movie_id)
            .values(views_count=Movie.views_count + 1)
        )

    async def add_view(self, user_id: int, movie_id: int) -> None:
        self._session.add(MovieView(user_id=user_id, movie_id=movie_id))

    async def deactivate(self, movie_id: int) -> None:
        await self._session.execute(
            update(Movie).where(Movie.id == movie_id).values(is_active=False)
        )

    async def delete(self, movie_id: int) -> None:
        """Kinoni butunlay o'chiradi (avval bog'liq ko'rishlar, so'ng kino)."""
        await self._session.execute(
            sql_delete(MovieView).where(MovieView.movie_id == movie_id)
        )
        await self._session.execute(
            sql_delete(Movie).where(Movie.id == movie_id)
        )

    async def update_fields(self, movie_id: int, **fields: object) -> None:
        if not fields:
            return
        await self._session.execute(
            update(Movie).where(Movie.id == movie_id).values(**fields)
        )

    async def count_total(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Movie).where(Movie.is_active.is_(True))
        )
        return int(result.scalar_one())

    async def sum_views(self) -> int:
        result = await self._session.execute(select(func.coalesce(func.sum(Movie.views_count), 0)))
        return int(result.scalar_one())

"""MovieService.deliver() — link-manba (source_type='link') testlari.

MUHIM FARQ copy_message yo'lidan: link yuborilmasa (masalan foydalanuvchi
botni bloklagan) — bu HAVOLA muammosi emas, YETKAZISH muammosi, shuning
uchun kino FAOLSIZLANTIRILMAYDI (kanal-manba xatosidan farqli).
"""
from __future__ import annotations

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendMessage

from app.models.movie import Movie
from app.services.movie_service import MovieDeliveryError, MovieService
from tests.helpers import FakeSession, make_bot


class _FakeMovieRepo:
    def __init__(self) -> None:
        self.deactivated_ids: list[int] = []
        self.incremented_ids: list[int] = []
        self.views_added: list[tuple[int, int]] = []

    async def deactivate(self, movie_id: int) -> None:
        self.deactivated_ids.append(movie_id)

    async def increment_views(self, movie_id: int) -> None:
        self.incremented_ids.append(movie_id)

    async def add_view(self, user_db_id: int, movie_id: int) -> None:
        self.views_added.append((user_db_id, movie_id))


def _link_movie(movie_id: int = 9) -> Movie:
    return Movie(
        id=movie_id,
        code="555",
        source_type="link",
        external_url="https://example.com/movie",
        title_uz="Link Kino",
        title_ru=None,
        title_en=None,
        year=2023,
        genre="drama",
        views_count=1,
        is_active=True,
    )


def _service_with_fake_repo() -> tuple[MovieService, _FakeMovieRepo]:
    service = MovieService(session=FakeSession())  # type: ignore[arg-type]
    repo = _FakeMovieRepo()
    service._repo = repo  # type: ignore[attr-defined]
    return service, repo


@pytest.mark.asyncio
async def test_link_delivery_sends_url_button_and_increments_views() -> None:
    service, repo = _service_with_fake_repo()
    bot = make_bot()
    bot.session.return_value = None
    movie = _link_movie()

    await service.deliver(bot, movie, user_db_id=42, chat_id=777, lang="uz")

    method = bot.session.call_args.args[1]
    assert isinstance(method, SendMessage)
    assert method.reply_markup.inline_keyboard[0][0].url == movie.external_url
    assert repo.incremented_ids == [movie.id]
    assert repo.views_added == [(42, movie.id)]


@pytest.mark.asyncio
async def test_link_delivery_does_not_use_copy_message() -> None:
    from aiogram.methods import CopyMessage

    service, _ = _service_with_fake_repo()
    bot = make_bot()
    bot.session.return_value = None
    movie = _link_movie()

    await service.deliver(bot, movie, user_db_id=42, chat_id=777, lang="uz")

    method = bot.session.call_args.args[1]
    assert not isinstance(method, CopyMessage)


@pytest.mark.asyncio
async def test_link_delivery_failure_does_not_deactivate_movie() -> None:
    service, repo = _service_with_fake_repo()
    bot = make_bot()
    movie = _link_movie()
    bot.session.side_effect = TelegramForbiddenError(
        method=SendMessage(chat_id=777, text="x"), message="bot was blocked by the user"
    )

    with pytest.raises(MovieDeliveryError):
        await service.deliver(bot, movie, user_db_id=42, chat_id=777, lang="uz")

    assert repo.deactivated_ids == []  # kanal yo'lidan FARQLI — deactivate yo'q
    assert repo.incremented_ids == []


@pytest.mark.asyncio
async def test_link_delivery_bad_request_also_raises_without_deactivate() -> None:
    service, repo = _service_with_fake_repo()
    bot = make_bot()
    movie = _link_movie()
    bot.session.side_effect = TelegramBadRequest(
        method=SendMessage(chat_id=777, text="x"), message="chat not found"
    )

    with pytest.raises(MovieDeliveryError):
        await service.deliver(bot, movie, user_db_id=42, chat_id=777, lang="uz")

    assert repo.deactivated_ids == []

# 🎬 Kino Bot

Telegram bot: foydalanuvchi **kino kodi** (masalan `777`) yoki **kino nomini** yozadi —
bot yopiq kanaldan videoni `copy_message` orqali yuboradi.

## Imkoniyatlar

- 🌐 3 tilda interfeys: 🇺🇿 O'zbek / 🇷🇺 Русский / 🇬🇧 English
- 🔒 Majburiy obuna (bir yoki bir nechta kanal, dinamik boshqariladi)
- 🔍 Kod va nom bo'yicha qidiruv (fuzzy search, `pg_trgm` — imlo xatolariga chidamli)
- 🔥 Trend kinolar (admin qo'lda tanlaydi, ko'pi bilan `TREND_LIMIT` ta)
- 🛠 Bot ichidagi admin panel (kino qo'shish, tahrirlash, statistika, broadcast, kanallar)
- ⏳ Redis asosidagi rate-limit va obuna keshi
- 📢 Har bir yuborilgan kino ostida botga/kanalga reklama tugmalari (organik o'sish uchun)
- 🧹 Foydalanuvchi o'z so'nggi 48 soatlik yozishmasini bitta tugma bilan tozalashi mumkin

## Texnologiyalar

Python 3.12 · aiogram 3.x · SQLAlchemy 2.x (async) · Alembic · PostgreSQL 16 (`pg_trgm`) ·
Redis · Docker Compose · pydantic-settings

## Struktura

```
app/
├── main.py            # entrypoint (dispatcher, middleware, polling)
├── config.py          # pydantic-settings (.env)
├── database.py        # async engine + session factory
├── models/            # ORM modellar
├── repositories/      # DB kirishlar (faqat shu yerda)
├── services/          # biznes logika
├── middlewares/       # db_session, user_context, rate_limit, subscription
├── keyboards/         # reply + inline
├── handlers/          # yupqa handlerlar (+ admin/)
├── states/            # FSM StatesGroup
└── utils/             # i18n, filtrlar, formatlash
locales/               # uz.json / ru.json / en.json (barcha matnlar)
alembic/               # migratsiyalar (pg_trgm + jadvallar)
```

## O'rnatish (Docker — tavsiya etiladi)

1. **`.env` faylini yarating** (namuna asosida):

   ```bash
   cp .env.example .env
   ```

2. **`.env` ni to'ldiring** (quyidagi bo'limga qarang).

3. **Ishga tushiring:**

   ```bash
   docker compose up -d --build
   ```

   Konteyner avtomatik ravishda `alembic upgrade head` bajaradi (jadvallar + `pg_trgm`),
   so'ng botni polling rejimida ishga tushiradi.

4. **Loglarni ko'rish:**

   ```bash
   docker compose logs -f bot
   ```

Bot ishga tushgach `Bot ishga tushdi: @username` ko'rinadi. Telegram'da `/start` yozing.

## `.env` sozlamalari

| O'zgaruvchi | Tavsif |
|---|---|
| `BOT_TOKEN` | @BotFather bergan token |
| `ADMIN_IDS` | Admin Telegram ID lar (vergul bilan): `111,222` |
| `ADMIN_PHONE` | Foydalanuvchilarga ko'rsatiladigan admin aloqa raqami |
| `STORAGE_CHANNEL_ID` | Kinolar saqlanadigan yopiq kanal ID (bot u yerda **admin** bo'lishi shart) |
| `REQUIRED_CHANNELS` | Majburiy obuna kanallari `username1,username2` (`@` siz). Bo'sh bo'lsa tekshirilmaydi |
| `POSTGRES_*` | Ma'lumotlar bazasi sozlamalari |
| `REDIS_*` | Redis sozlamalari |
| `DEFAULT_LANGUAGE` | Standart til (`uz`/`ru`/`en`) |
| `TREND_LIMIT` | Trend ro'yxatidagi kinolar soni |
| `SEARCH_SIMILARITY_THRESHOLD` | Fuzzy qidiruv chegarasi (0–1, default `0.2`) |
| `RATE_LIMIT_PER_MINUTE` | Foydalanuvchi uchun daqiqadagi limit |
| `PROTECT_CONTENT` | `true` bo'lsa yuborilgan video ko'chirilishdan himoyalanadi |
| `PROMO_BOT_USERNAME` | Har bir yuborilgan kino ostidagi reklama tugmasi bot username'i (`@` siz) |
| `PROMO_CHANNEL_USERNAME` | Har bir yuborilgan kino ostidagi reklama tugmasi kanal username'i (`@` siz) |

> ⚠️ `.env` hech qachon git'ga qo'shilmaydi (`.gitignore` da). Haqiqiy tokenlarni
> faqat `.env` da saqlang — `.env.example` faqat namuna (placeholder) uchun.

## Admin qo'shish

1. Telegram ID ni oling (masalan [@userinfobot](https://t.me/userinfobot) orqali).
2. `.env` dagi `ADMIN_IDS` ga qo'shing: `ADMIN_IDS=111111111,222222222`.
3. Botni qayta ishga tushiring: `docker compose restart bot`.
4. Admin sifatida `/admin` yozing — admin panel ochiladi.

## Kino qo'shish — 2 usul

### A) Eng oson: kanalga caption bilan tashlash (avto)

Videoni **yopiq (storage) kanalga** quyidagi caption bilan tashlang — bot avtomatik qo'shadi:

```
#1
Nom: Robotar
Janr: drama
Yil: 2024
```

- `#1` — kino kodi (`#auto` yozsangiz bot keyingi bo'sh raqamni oladi)
- `Nom:` — kino nomi (majburiy). Aliaslar: `Nomi:` / `Name:` / `Title:` / `Название:`
- `Janr:` — janr (ixtiyoriy). `Yil:` — yil (ixtiyoriy)
- Kalitlar tartibi ahamiyatsiz.

Bot postni oladi, saqlaydi va adminga tasdiq yuboradi. **Postni tahrirlasangiz** — kino ma'lumoti yangilanadi. Kod band bo'lsa yoki format xato bo'lsa — admin ogohlantiriladi.

> ⚠️ Faqat `STORAGE_CHANNEL_ID` dagi postlar qayta ishlanadi. Bot o'sha kanalda **admin** bo'lishi shart. Har bir video **alohida post** bo'lsin (albom emas).

### B) Wizard orqali (uch tilli nom kerak bo'lsa)

1. Videoni yopiq kanalga joylang.
2. Botda `/admin` → **➕ Kino qo'shish**.
3. Kanaldagi video xabarni botga **FORWARD** qiling.
4. Kod (yoki `auto`), nomi (uz/ru/en), yil, janrni kiriting → **✅ Saqlash**.

Foydalanuvchi endi kod yoki nom yozib kinoni oladi.

## Kino o'chirish (admin)

1. `/admin` → **🗑 O'chirish**.
2. Bot so'raydi: *"Kino kodini yoki nomini yuboring"*.
3. Kod (masalan `777`) yoki nom yuboring → bot kinoni topadi.
   - Bitta topilsa — darhol tasdiq oynasi.
   - Bir nechta topilsa — ro'yxatdan tanlaysiz.
4. Tagidagi **🗑 Ha, o'chir** tugmasini bosing → kino **butunlay** o'chadi.

> To'liq o'chirish: kino, uning ko'rish tarixi bazadan o'chadi va **kod bo'shaydi**
> (o'sha kodni yangi kinoga qayta ishlatish mumkin). "Tahrirlash" faqat maydonlarni
> (nom/yil/janr) o'zgartiradi — o'chirish alohida tugmada.

## Trend kinolarni boshqarish (admin)

Trend endi ko'rishlar soniga avtomatik bog'liq emas — admin qo'lda tanlaydi.

1. `/admin` → **📊 Boshqaruv** → **🔥 Trend kinolar**.
2. Bot joriy trend ro'yxatini ko'rsatadi (har biri oldida **🗑** — bosilsa trenddan olib tashlanadi).
3. Qo'shish uchun kino kodi yoki nomini yuboring:
   - Bitta topilsa — darhol trendga qo'shiladi.
   - Bir nechta topilsa — ro'yxatdan tanlaysiz.
4. Ro'yxat to'lgan bo'lsa (standart **10/10**, `TREND_LIMIT` orqali sozlanadi) —
   avval birontasini o'chirish kerak.

Foydalanuvchiga "🔥 Trend kinolar" tugmasida shu ro'yxat (nomi + kodi bilan)
ko'rinadi, bosilganda kino bitta xabar sifatida yuboriladi.

## Reklama yuborish (broadcast)

1. `/admin` → **📣 Xabar yuborish**.
2. Reklama xabarini (matn/rasm/video) botga yuboring.
3. **✅ Yuborish** — tasdiqlaysiz (`N ta foydalanuvchiga yuborilsinmi?`).
4. Reklama **fon rejimida** barcha faol foydalanuvchilarga yuboriladi (~25 msg/sek).
   Handler bloklanmaydi — admin panelda ishlashda davom etaverasiz.
5. Yakunda adminga hisobot keladi: `Yuborildi / Bloklagan / Xato`.

> Botni bloklagan foydalanuvchilar avtomatik `is_blocked=True` bo'ladi va
> keyingi reklamalarga kirmaydi.

## Testlar

```bash
pip install -r requirements-dev.txt
pytest -q
```

Ikki qatlam: sof-logika testlari (config parsing, i18n parity/format, til
fallback, caption parsing, Excel eksport) va biznes-logika testlari (admin
ruxsati, rate-limit, majburiy obuna, kino yuborish/dead-link, broadcast,
kod to'qnashuvi race-condition). Ikkalasi ham **haqiqiy DB/Redis/Telegram
API'siz** ishlaydi — Bot/Redis/Session `unittest.mock` bilan almashtirilgan
(`tests/helpers.py`), shuning uchun CI'da yoki oddiy `pip install`dan keyin
tezda ishga tushadi.

## Lokal ishga tushirish (Docker'siz)

PostgreSQL (`pg_trgm` bilan) va Redis alohida ishlab turgan bo'lsa:

```bash
pip install -r requirements.txt
# .env dagi POSTGRES_HOST=localhost, REDIS_HOST=localhost bo'lsin
alembic upgrade head
python -m app.main
```

## Migratsiyalar

- Yangi migratsiya: `alembic revision -m "xabar"`
- Qo'llash: `alembic upgrade head`
- Orqaga: `alembic downgrade -1`

## Ma'lum cheklovlar

- Ruxsatsiz kino tarqatish qonunga zid bo'lishi va bot/kanal bloklanishiga olib kelishi mumkin —
  faqat huquqiy toza kontent bilan foydalaning.
- Kanaldan xabar o'chirilsa, kino avtomatik `is_active=False` ga o'tadi va adminga video "mavjud emas" deb ko'rsatiladi.

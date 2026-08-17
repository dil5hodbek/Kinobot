# KINO BOT — MASTER PROMPT & TO'LIQ LOYIHA REJASI

> Ushbu hujjat coding agent uchun yakuniy spetsifikatsiya. Barcha talablar majburiy.

---

## 1. LOYIHA TAVSIFI

Telegram bot: foydalanuvchi **kino kodi** (masalan `777`) yoki **kino nomi** (katta-kichik harf, imlo xatolariga chidamli) yozadi — bot yopiq kanaldan videoni `copy_message` orqali yuboradi.

**Asosiy funksiyalar:**
- 3 tilda interfeys: 🇺🇿 O'zbek / 🇷🇺 Русский / 🇬🇧 English
- Majburiy obuna (bir yoki bir nechta kanal)
- Kod va nom bo'yicha qidiruv (fuzzy search, pg_trgm)
- Trend kinolar (eng ko'p ko'rilgan)
- Admin panel (bot ichida)
- Statistika (foydalanuvchilar, ko'rishlar)

---

## 2. TEXNOLOGIK STACK

| Qatlam | Texnologiya |
|---|---|
| Til | Python 3.12+ |
| Bot framework | aiogram 3.x |
| ORM | SQLAlchemy 2.x (async) |
| Migratsiya | Alembic |
| Database | PostgreSQL 16 (pg_trgm extension) |
| Cache / FSM / Rate-limit | Redis |
| Konteynerizatsiya | Docker + docker-compose |
| Config | pydantic-settings (.env) |

---

## 3. .ENV KONFIGURATSIYA

`.env.example` fayli (haqiqiy qiymatlar `.env` da, git'ga qo'shilmaydi):

```env
# === BOT ===
BOT_TOKEN=1234567890:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# === ADMIN ===
# Vergul bilan bir nechta admin Telegram ID kiritish mumkin
ADMIN_IDS=123456789
ADMIN_PHONE=+998935959355

# === KINO SAQLANADIGAN YOPIQ KANAL ===
# Bot shu kanalda ADMIN bo'lishi SHART
STORAGE_CHANNEL_ID=-1001234567890

# === MAJBURIY OBUNA KANALLARI ===
# Format: username1,username2 (@ belgisisiz) — bo'sh bo'lsa obuna tekshirilmaydi
REQUIRED_CHANNELS=mychannel1,mychannel2

# === DATABASE ===
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=kinobot
POSTGRES_USER=kinobot
POSTGRES_PASSWORD=change_me_strong_password
# Connection pool (bo'lim 14 — ko'p auditoriyada standart qiymatlar kam)
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE_SEC=1800

# === REDIS ===
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_MAX_CONNECTIONS=50

# === APP ===
DEFAULT_LANGUAGE=uz
TREND_LIMIT=10
SEARCH_SIMILARITY_THRESHOLD=0.2
RATE_LIMIT_PER_MINUTE=20
```

**Config klass (pydantic-settings):** `.env` dagi barcha qiymatlar type-hint bilan o'qiladi, `ADMIN_IDS` va `REQUIRED_CHANNELS` list'ga parse qilinadi. Hech qanday secret kodga hardcode qilinmaydi.

---

## 4. DATABASE SXEMASI

```sql
-- Foydalanuvchilar
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(64),
    full_name VARCHAR(255),
    language VARCHAR(5) NOT NULL DEFAULT 'uz',        -- uz / ru / en
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,         -- botni bloklagan
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_users_telegram_id ON users (telegram_id);

-- Kinolar
CREATE TABLE movies (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,                  -- '777'
    source_type VARCHAR(10) NOT NULL DEFAULT 'channel', -- 'channel' | 'link'
    channel_id BIGINT,                                 -- source_type='channel' uchun SHART
    message_id BIGINT,                                 -- source_type='channel' uchun SHART
    external_url VARCHAR(500),                         -- source_type='link' uchun SHART
    title_uz VARCHAR(255) NOT NULL,
    title_ru VARCHAR(255),
    title_en VARCHAR(255),
    year SMALLINT,
    genre VARCHAR(100),
    views_count BIGINT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,           -- soft-delete
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX ix_movies_code ON movies (code);
CREATE INDEX ix_movies_genre ON movies (genre);        -- janr bo'yicha guruhlash (bo'lim 5.6)
CREATE INDEX ix_movies_views ON movies (views_count DESC) WHERE is_active;
CREATE INDEX ix_movies_title_uz_trgm ON movies USING gin (lower(title_uz) gin_trgm_ops);
CREATE INDEX ix_movies_title_ru_trgm ON movies USING gin (lower(coalesce(title_ru, '')) gin_trgm_ops);
CREATE INDEX ix_movies_title_en_trgm ON movies USING gin (lower(coalesce(title_en, '')) gin_trgm_ops);
-- Manba turiga qarab majburiy maydonlarni bazaning o'zi kafolatlaydi:
ALTER TABLE movies ADD CONSTRAINT ck_movies_source_fields CHECK (
    (source_type = 'channel' AND channel_id IS NOT NULL AND message_id IS NOT NULL AND external_url IS NULL)
    OR (source_type = 'link' AND external_url IS NOT NULL)
);

-- Ko'rishlar tarixi (statistika uchun)
CREATE TABLE movie_views (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    movie_id BIGINT NOT NULL REFERENCES movies(id),
    viewed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_movie_views_movie_viewed ON movie_views (movie_id, viewed_at);

-- Majburiy obuna kanallari (dinamik boshqarish uchun — .env dagiga qo'shimcha)
CREATE TABLE required_channels (
    id BIGSERIAL PRIMARY KEY,
    channel_username VARCHAR(64) UNIQUE NOT NULL,      -- @ belgisisiz
    channel_title VARCHAR(255),
    invite_link VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

> Barcha jadval o'zgarishlari FAQAT Alembic migratsiya orqali.

---

## 5. FOYDALANUVCHI INTERFEYSI (UX FLOW)

### 5.1. /start oqimi

```
/start
  └─> Yangi foydalanuvchimi?
        ├─ HA  → Til tanlash (inline: 🇺🇿 / 🇷🇺 / 🇬🇧)
        │         └─> Majburiy obuna tekshiruvi
        └─ YO'Q → Majburiy obuna tekshiruvi
                    ├─ Obuna BOR  → Asosiy menyu
                    └─ Obuna YO'Q → Kanallar ro'yxati (inline, har biriga link)
                                    + "✅ Tekshirish" tugmasi
```

### 5.2. Majburiy obuna ekrani (inline keyboard)

```
📢 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:

[ 1-kanal ➕ ]      ← url button (invite link)
[ 2-kanal ➕ ]
[ ✅ Tekshirish ]   ← callback: check_subscription
```

- Har bir xabar/callback oldidan **middleware** obunani tekshiradi (`getChatMember`).
- Natija Redis'da 60 soniya keshlanadi (Telegram API limitini asrash uchun).
- `left`, `kicked` statuslar = obuna yo'q; `member`, `administrator`, `creator` = bor.

### 5.3. Asosiy menyu — Reply Keyboard (2 ta yonma-yon + 1 pastda)

```
┌─────────────────┬─────────────────┐
│   🔍 Qidiruv    │   📢 Kanallar   │
├─────────────────┴─────────────────┤
│         🔥 Trend kinolar          │
└───────────────────────────────────┘
```

aiogram 3 kodi:

```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    labels = {
        "uz": ("🔍 Qidiruv", "📢 Kanallar", "🔥 Trend kinolar"),
        "ru": ("🔍 Поиск", "📢 Каналы", "🔥 Топ фильмы"),
        "en": ("🔍 Search", "📢 Channels", "🔥 Trending"),
    }[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=labels[0]), KeyboardButton(text=labels[1])],
            [KeyboardButton(text=labels[2])],
        ],
        resize_keyboard=True,
    )
```

### 5.4. Tugmalar xatti-harakati

| Tugma | Amal |
|---|---|
| 🔍 Qidiruv | "Kino kodi yoki nomini yuboring" xabari. Keyingi xabar qidiruv sifatida qabul qilinadi (aslida istalgan matn har doim qidiruv — bu tugma faqat yo'naltiruvchi) |
| 📢 Kanallar | Majburiy obuna kanallari ro'yxati (inline url tugmalar) |
| 🔥 Trend kinolar | Top-10 eng ko'p ko'rilgan kino — inline tugmalar: `1. Nomi (👁 12 543)`, bosilsa kino yuboriladi |

### 5.5. Qidiruv natijalari

- **Faqat raqam** (`^\d{1,10}$`) → kod bo'yicha aniq qidiruv → topilsa darhol video.
- **Janr nomiga ANIQ mos kelsa** (masalan "romance") → shu janrdagi kinolar ro'yxati (bo'lim 5.6). Fuzzy nom qidiruvidan OLDIN tekshiriladi.
- **Matn** → pg_trgm fuzzy search (case-insensitive, imlo xatolariga chidamli):
  - 1 ta natija → darhol video + caption (nomi, yili, kodi).
  - 2+ natija → inline ro'yxat (max 10), tanlagach video.
  - 0 natija → "❌ Topilmadi. Kodni tekshiring yoki boshqa nom yozing."
- Yuborish **manba turiga** qarab (bo'lim 6.1-bis):
  - `source_type='channel'` → **`copy_message`** (forward EMAS — kanal manbasi ko'rinmasin, `protect_content` admin sozlamasiga qarab). Xato bo'lsa (manba o'chirilgan) — kino **faolsizlantiriladi**, adminга xabar.
  - `source_type='link'` → **inline havola tugmasi** ("🎬 Filmni ko'rish", tashqi URL). Yuborishda xato bo'lsa (masalan foydalanuvchi botni bloklagan) — bu YETKAZISH muammosi, kino faolsizlantirilMAYDI (havolaning o'zi buzuq degani emas).

### 5.6. Janr bo'yicha guruhlash

Foydalanuvchi mavjud janr nomini (masalan "romance", "drama") aniq (case-insensitive) yozsa — bot shu janrdagi barcha faol kinolarni ro'yxat qilib beradi (inline tugmalar, ko'p ko'rilgani birinchi, limit 30). Kod diapazoni (masalan "1-100 = romance") ISHLATILMAYDI — bu yangi kino qo'shilganda tartibni buzardi; buning o'rniga bazadagi `genre` ustuni bo'yicha to'g'ridan-to'g'ri filtrlanadi (`ix_movies_genre` indeksi bilan). Moslik topilmasa — oddiy fuzzy nom qidiruviga o'tiladi (o'lik oxir emas).

---

## 6. ADMIN PANEL (bot ichida)

Kirish: `telegram_id in ADMIN_IDS`. `/admin` komandasi yoki admin uchun alohida reply keyboard.

Menyu **2 QAVATLI** (HUB + submenu) — 8+ tugmani bitta ekranga tiqishtirish
o'rniga, bo'lim tanlanadi, so'ng aniq amal:

```
HUB:
┌──────────────────┬──────────────────┐
│  🎬 Kinolar      │  📊 Boshqaruv    │
├──────────────────┼──────────────────┤
│  👤 Oddiy menyu  │  🔙 Chiqish      │
└──────────────────┴──────────────────┘

"🎬 Kinolar" →                    "📊 Boshqaruv" →
┌──────────────────┬──────────────────┐  ┌──────────────────┬──────────────────┐
│  ➕ Kino qo'shish │  🔗 Link qo'shish│  │  📊 Statistika   │  📣 Xabar yuborish│
├──────────────────┼──────────────────┤  ├──────────────────┼──────────────────┤
│  📝 Tahrirlash   │  🗑 O'chirish    │  │  📢 Kanal qo'shish│  🔙 Orqaga       │
├──────────────────┼──────────────────┤  └──────────────────┴──────────────────┘
│  📋 Kodlar       │  🔙 Orqaga       │
└──────────────────┴──────────────────┘
```

"👤 Oddiy menyu" — admin oddiy foydalanuvchi ko'radigan menyuni ko'radi
(holat/huquq o'zgarmaydi, `/admin` bilan istalgan payt qaytiladi) —
"🔙 Chiqish"dan farqli, bu faqat ko'rish uchun, FSM holatini ham tozalamaydi.

### 6.1. Kino qo'shish oqimi — KANALDAN (FSM — aiogram states)

```
1. Admin yopiq kanalga video tashlaydi
2. Kanaldagi xabarni botga FORWARD qiladi
   → bot message_id + channel_id ni avtomatik oladi
   → faqat sozlangan STORAGE_CHANNEL_ID dan forward qabul qilinadi
3. Bot so'raydi: Kod? (yoki "auto" — keyingi bo'sh raqam)
4. Nomi (uz)? → Nomi (ru)? (skip mumkin) → Nomi (en)? (skip)
5. Yili? (skip) → Janri? (skip)
6. Tasdiqlash kartochkasi → [✅ Saqlash] [❌ Bekor]
```

- Kod unique constraint bilan himoyalangan; to'qnashuvda xato ko'rsatiladi
  (shu jumladan bir nechta post bir vaqtda kelib RACE bo'lsa ham — bazaning
  CHECK/UNIQUE constraint'i + `IntegrityError` ushlanadi).
- FSM holatlari Redis'da saqlanadi.
- Kanaldan **avtomatik** qo'shish ham bor (`channel_intake.py`): admin
  kanalga to'g'ridan caption bilan (`#kod\nNom: ...\nJanr: ...`) tashlasa,
  bot forward'siz o'zi o'qib qo'shadi.

### 6.1-bis. Kino qo'shish oqimi — LINK ORQALI (FSM)

Admin kino faylini yuklab kanalga joylashtirish o'rniga, boshqa saytdagi
kino havolasini (URL) bersa ham bo'ladi — bot uni **video sifatida
ko'chirmaydi**, faqat inline tugma ("🎬 Filmni ko'rish") bilan havolaga
yo'naltiradi.

```
1. Admin "🔗 Link qo'shish" tugmasini bosadi
2. Bot so'raydi: Kino havolasi (URL)? (https:// bilan boshlanishi shart)
3. Bot so'raydi: Kod? (yoki "auto")
4. Nomi (uz)? → Nomi (ru)? (skip) → Nomi (en)? (skip)
5. Yili? (skip) → Janri? (skip)
6. Tasdiqlash kartochkasi → [✅ Saqlash] [❌ Bekor]
```

- Qolgan qadamlar (kod/nom/yil/janr) kanaldan qo'shish bilan **bir xil**
  — faqat 1-qadam va yuborish mexanizmi farq qiladi.
- `movies.source_type='link'`, `external_url` majburiy (`channel_id`/
  `message_id` esa NULL qoladi — CHECK constraint bazaning o'zida
  noto'g'ri kombinatsiyani rad etadi, bo'lim 4).
- Havola ishlamay qolsa (foydalanuvchi shikoyat qilsa) — kino **avtomatik
  faolsizlantirilMAYDI** (bo'lim 5.5) — admin qo'lda tahrirlashi kerak,
  chunki bot havolaning o'zi buzuqmi yoki foydalanuvchi tomonида muammo
  ekanini ajrata olmaydi.

### 6.2. Statistika

- Jami foydalanuvchilar / bugungi yangi / faol (7 kun)
- Jami kinolar / jami ko'rishlar
- Top-5 kino
- Bloklagan foydalanuvchilar soni

### 6.3. Xabar yuborish (broadcast)

- Barcha faol foydalanuvchilarga xabar.
- Rate-limit: 25 msg/sec (Telegram limiti 30), `asyncio.sleep` bilan.
- `Forbidden` xatosi → user `is_blocked=True` belgilanadi.
- Yakunda hisobot: yuborildi / bloklagan / xato.

### 6.4. Kanal qo'shish/o'chirish

- Majburiy obuna kanallarini dinamik boshqarish (`required_channels` jadvali).
- Kanal qo'shishda bot o'sha kanalda admin ekanini tekshiradi.

### 6.5. Admin bilan aloqa

- Foydalanuvchi menyusida yoki /help da: `👨‍💻 Admin: +998935959355` ko'rsatiladi (matn `.env` dagi `ADMIN_PHONE` dan olinadi).

---

## 7. LOKALIZATSIYA (i18n)

`locales/uz.json`, `locales/ru.json`, `locales/en.json` — barcha matnlar shu yerda, kodda hardcode YO'Q.

```json
// locales/uz.json (namuna)
{
  "start_choose_lang": "Tilni tanlang:",
  "subscribe_required": "📢 Botdan foydalanish uchun kanallarga obuna bo'ling:",
  "subscribe_check": "✅ Tekshirish",
  "subscribe_ok": "✅ Rahmat! Endi botdan foydalanishingiz mumkin.",
  "subscribe_fail": "❌ Hali barcha kanallarga obuna bo'lmadingiz.",
  "main_menu": "Kino kodi yoki nomini yuboring 👇",
  "search_prompt": "🔍 Kino kodi yoki nomini yozing:",
  "not_found": "❌ Hech narsa topilmadi. Kodni tekshiring yoki boshqa nom yozing.",
  "multiple_found": "🔎 Topilgan kinolar — birini tanlang:",
  "movie_caption": "🎬 {title}\n📅 {year} | 🎭 {genre}\n🔢 Kod: {code}\n👁 {views} marta ko'rilgan",
  "trend_title": "🔥 Eng mashhur kinolar:",
  "movie_unavailable": "⚠️ Video vaqtincha mavjud emas. Admin: {admin_phone}",
  "help": "ℹ️ Kino kodi yoki nomini yuboring.\n👨‍💻 Admin: {admin_phone}"
}
```

Middleware har bir update'da user tilini DB'dan (Redis kesh bilan) olib, handler'ga `lang` sifatida uzatadi.

---

## 8. LOYIHA STRUKTURASI

```
kinobot/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── alembic/
│   └── versions/
├── locales/
│   ├── uz.json
│   ├── ru.json
│   └── en.json
└── app/
    ├── main.py                  # entrypoint: bot + dispatcher + polling/webhook
    ├── config.py                # pydantic-settings
    ├── database.py              # async engine, session factory
    ├── models/
    │   ├── user.py
    │   ├── movie.py
    │   ├── movie_view.py
    │   └── required_channel.py
    ├── repositories/
    │   ├── user_repository.py
    │   ├── movie_repository.py
    │   └── channel_repository.py
    ├── services/
    │   ├── user_service.py
    │   ├── movie_service.py        # deliver(): manba turiga qarab tarmoqlanadi
    │   ├── subscription_service.py
    │   ├── broadcast_service.py
    │   ├── stats_service.py        # statistika yig'ish + matn shakllantirish
    │   └── channel_service.py      # kanal CRUD + bot-admin tekshiruvi
    ├── middlewares/
    │   ├── db_session.py         # har update'ga session ochish/yopish
    │   ├── user_context.py       # user + lang inject
    │   ├── subscription.py       # majburiy obuna tekshiruvi
    │   └── rate_limit.py         # Redis flood-control
    ├── keyboards/
    │   ├── reply.py              # asosiy menyu, admin menyu
    │   └── inline.py             # til, obuna, natijalar, trend
    ├── handlers/
    │   ├── start.py
    │   ├── language.py
    │   ├── subscription.py
    │   ├── search.py
    │   ├── trend.py
    │   ├── channels.py
    │   └── admin/
    │       ├── panel.py           # kirish/chiqish + 2 qavatli menyu navigatsiyasi
    │       ├── add_movie.py       # FSM — kanaldan (forward)
    │       ├── add_link_movie.py  # FSM — link orqali (bo'lim 6.1-bis)
    │       ├── edit_movie.py
    │       ├── delete_movie.py
    │       ├── stats.py
    │       ├── broadcast.py
    │       ├── channels.py
    │       └── codes.py           # Excel eksport
    ├── states/
    │   └── admin_states.py       # FSM StatesGroup
    └── utils/
        └── i18n.py               # locale loader, t(key, lang, **kwargs)
```

**Arxitektura qoidalari:**
- Handler'lar YUPQA — faqat request/response, biznes logika service'larda.
- DB access faqat repository'larda. Handler'da hech qanday SQL/ORM query yo'q.
- Dependency injection: session, service'lar middleware/dispatcher orqali uzatiladi.

---

## 9. DOCKER

```yaml
# docker-compose.yml
services:
  bot:
    build: .
    restart: unless-stopped
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

volumes:
  pg_data:
  redis_data:
```

Dockerfile: `python:3.12-slim`, multi-stage kerak emas (bot yengil), lekin `pip install --no-cache-dir`.

---

## 10. XAVFSIZLIK VA CHEGARALAR

1. **Secrets** — faqat `.env`, hech qachon kod/git'da emas. `.gitignore`da `.env` bo'lishi shart.
2. **Rate-limit** — Redis: user_id bo'yicha `RATE_LIMIT_PER_MINUTE` (default 20 xabar/min), oshsa "⏳ Sekinroq..." javob.
3. **Admin tekshiruvi** — har bir admin handler'da `telegram_id in settings.admin_ids` filter (aiogram Filter klassi sifatida).
4. **Input validation** — kino kodi max 20 belgi (bo'lim 4 dagi `code VARCHAR(20)` sxemasiga mos — raqamli qidiruv qat'iy `^\d{1,10}$` bilan cheklangan, admin qo'lda kiritgan kod esa harflarni ham qamrab olishi mumkin, shu sabab 20), qidiruv matni max 100 belgi (trim qilinadi).
5. **Broadcast xavfsizligi** — tasdiqlash bosqichi majburiy ("N ta foydalanuvchiga yuborilsinmi?").
6. **copy_message xatolari** — try/except: xabar o'chirilgan → kino `is_active=False`, adminga xabar.
7. **Loglar** — token/parol hech qachon log'ga yozilmaydi.

---

## 11. MA'LUM KAMCHILIKLAR / RISKLAR

1. **Mualliflik huquqi** — ruxsatsiz kino tarqatish qonunga zid bo'lishi va Telegram tomonidan bot/kanal bloklanishiga olib kelishi mumkin. Faqat huquqiy toza kontent bilan ishlatish tavsiya etiladi.
2. **Bot bloklansa** — barcha message_id'lar yangi botga ko'chmaydi (copy_message huquqi kanal adminligiga bog'liq) — kanal va DB backup muhim.
3. **Dead link'lar** — kanaldan xabar o'chirilsa DB'da qoladi; haftalik tekshiruv job tavsiya etiladi (v2).
4. **getChatMember limiti** — ko'p kanalli obuna tekshiruvi sekinlashtiradi; Redis kesh (60s) shart.

---

## 12. BOSQICHMA-BOSQICH ROADMAP

**Bosqich 1 — MVP (asosiy):**
- [x] Loyiha skeleti, config, Docker, Alembic init
- [x] /start, til tanlash, user registratsiya
- [x] Majburiy obuna middleware + kanallar ekrani
- [x] Asosiy menyu (Qidiruv / Kanallar / Trend)
- [x] Kod bo'yicha kino yuborish
- [x] Admin: kino qo'shish (FSM, forward orqali)

**Bosqich 2 — Qidiruv va trend:**
- [x] pg_trgm fuzzy search (nom bo'yicha, 3 tilda)
- [x] Ko'p natijali inline tanlash
- [x] Trend kinolar (views_count)
- [x] movie_views statistika jadvali

**Bosqich 3 — Admin kengaytmalari:**
- [x] Statistika paneli
- [x] Broadcast (rate-limit bilan)
- [x] Kanallarni dinamik boshqarish
- [x] Kino tahrirlash/o'chirish (soft-delete)

**Bosqich 4 — Polish (v2, ixtiyoriy):**
- [ ] Dead-link tekshiruv cron
- [x] Janr bo'yicha filtr (bo'lim 5.6)
- [ ] Yil bo'yicha filtr
- [ ] Referal tizim
- [ ] Webhook rejimi (bo'lim 14 — hozircha polling yetarli, kerak bo'lganda)

**Bosqich 5 — Katta auditoriya + link kinolar:**
- [x] Link orqali kino qo'shish (bo'lim 6.1-bis) — video yuklamasdan, tashqi havola
- [x] Janr bo'yicha guruhlash (bo'lim 5.6)
- [x] Admin menyu 2 qavatli (HUB + submenu, bo'lim 6)
- [x] DB/Redis connection pool sozlandi (bo'lim 14)
- [ ] Webhook rejimi, Postgres read-replica — hozircha kerak emas (bo'lim 14)

---

## 13. CODING AGENT UCHUN QAT'IY TALABLAR

1. Python 3.12, to'liq type hints, async SQLAlchemy 2.x.
2. Hech qanday placeholder, TODO, tugallanmagan funksiya YO'Q.
3. Har bir fayl to'liq, ishga tushirishga tayyor bo'lsin.
4. Barcha matnlar locales/*.json orqali — kodda hardcode matn taqiqlanadi.
5. Barcha secret'lar .env orqali — kodda hardcode taqiqlanadi.
6. Handler yupqa, service'da biznes logika, repository'da DB.
7. Har bir tashqi chaqiriq (Telegram API, DB) try/except bilan himoyalangan.
8. Alembic bilan initial migratsiya (pg_trgm extension shu yerda yaratiladi).
9. README.md: o'rnatish, .env to'ldirish, `docker compose up -d`, admin qo'shish yo'riqnomasi.
10. Ishga tushirish testi: `docker compose up` → bot polling boshlaydi → /start ishlaydi.

---

## 14. KENGAYISH (SCALING) — HOZIR VA KEYINGI BOSQICH

Katta auditoriya (o'n minglab+ foydalanuvchi) rejalashtirilganда, lekin
hozircha real yuk kam bo'lsa, tamoyil: **poydevorni hozir tayyorla,
murakkab infratuzilmani haqiqiy ehtiyoj chiqqanда qur** (erta optimallash
— behuda murakkablik).

### 14.1. Hozir qilingan (poydevor)

- **DB connection pool aniq sozlangan** — standart SQLAlchemy qiymatlari
  (`pool_size=5, max_overflow=10`) kam auditoriyada navbat hosil qiladi.
  `.env`: `DB_POOL_SIZE` (standart 20), `DB_MAX_OVERFLOW` (standart 20),
  `DB_POOL_RECYCLE_SEC` (standart 1800 — uzoq turgan ulanish yangilanadi).
- **Redis max_connections chegaralangan** — `.env`: `REDIS_MAX_CONNECTIONS`
  (standart 50) — bitta jarayon Redis'ga cheksiz ulanish ochmasin.
- **`genre` ustuniga indeks** — janr bo'yicha guruhlash (bo'lim 5.6) ko'p
  auditoriyada ham sekinlashmasin (`ix_movies_genre`).

### 14.2. Kerak bo'lganда qilinadigan (HOZIR emas)

Quyidagilar ATAYLAB amalga oshirilmagan — ular haqiqiy o'lchov (real
foydalanuvchi soni/sekinlashuv belgisi) ko'rsatganda qo'shiladi, oldindan
emas:

- **Webhook rejimi** (polling o'rniga) — polling minglab kunlik faol
  foydalanuvchigacha yetarli. Webhook HTTPS endpoint + ASGI server talab
  qiladi (qo'shimcha infratuzilma murakkabligi) — faqat юqori tezlik/kam
  kechikish haqiqatan kerak bo'lganda.
- **Postgres read-replica** — botlarda odatda birinchi tirbandlik DB emas
  (pool/polling/Redis). Replica faqat **o'qish** yuki (masalan minglab
  bir vaqtdagi qidiruv) haqiqiy muammo bo'lganда qo'shiladi.
- **Horizontal masshtablash** (bir nechta bot jarayoni) — aiogram polling
  bitta jarayonda yagona bo'lishi kerak (bir nechta jarayon bir xil
  update'ni ikki marta olib ketishi mumkin); ko'p jarayon kerak bo'lsa
  avval webhook rejimiga o'tish SHART.

**Qachon qaytish kerak:** Redis/Postgres CPU/xotira monitoring qizil
chiziqqa yetsa, yoki foydalanuvchilar javob sekinligidan shikoyat qilsa —
shu bo'lim birinchi navbatda ko'rib chiqiladi.
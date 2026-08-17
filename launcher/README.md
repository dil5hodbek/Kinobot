# 🚀 Launcher

Loyihani Windows'da bir tugma bilan ishga tushirish uchun.

## Talab
- **Docker Desktop** o'rnatilgan va **ishlab turgan** bo'lishi kerak
  (https://www.docker.com/products/docker-desktop/). Ilova to'liq ishga
  tushgach (tray'da yashil belgi), `Windows.bat` ni ishlating.

## Ishlatish
1. `Windows.bat` faylni **ikki marta bosing** (yoki o'ng tugma → *Run as administrator*).
2. Menyudan **[1] Ishga tushirish** ni tanlang.
   - Birinchi marta `.env` bo'lmasa, u avtomatik yaratiladi va Notepad'da ochiladi —
     `BOT_TOKEN`, `ADMIN_IDS`, `STORAGE_CHANNEL_ID`, `REQUIRED_CHANNELS` ni to'ldiring,
     saqlang, yopib qaytadan **[1]** ni tanlang.
   - Konteynerlar quriladi (Postgres + Redis + bot), migratsiyalar bajariladi,
     bot polling boshlaydi va loglar ko'rsatiladi.

## Menyu bandlari
| # | Amal | Izoh |
|---|---|---|
| 1 | Ishga tushirish | `docker compose up -d --build` + loglar |
| 2 | Loglar | bot loglarini kuzatish (Ctrl+C — chiqish) |
| 3 | Holat | konteynerlar statusi |
| 4 | Restart | `docker compose restart` |
| 5 | To'xtatish | `docker compose stop` (ma'lumot saqlanadi) |
| 6 | To'liq o'chirish | `docker compose down` (baza volume saqlanadi) |
| 7 | Chiqish | — |

## Eslatma
- Loglar oynasidan **Ctrl+C** bossangiz — faqat loglar ko'rsatuvi to'xtaydi,
  bot orqa fonda ishlab turaveradi.
- Butunlay to'xtatish uchun **[5]** yoki **[6]** ni tanlang.
- Ma'lumotlar bazasi Docker volume'da saqlanadi — `down` ham uni o'chirmaydi
  (butunlay tozalash: `docker compose down -v`).

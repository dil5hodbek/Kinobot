FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (libpq for asyncpg is not required, but keep minimal build tools)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Konteyner ichida root sifatida ishlamaydi — kelajakda RCE bo'lsa ham
# blast radius kichikroq bo'lsin. /app ga yozish huquqi kerak emas
# (kod faqat o'qiladi, hech narsa diskka yozilmaydi — log'lar stdout'ga).
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

# Alembic migratsiyalarni ishga tushirib, so'ng botni start qiladi
CMD ["sh", "-c", "alembic upgrade head && python -m app.main"]

FROM python:3.15-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# curl — Docker healthcheck uchun (/health/ready endpointini so'raydi)
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

# Health/metrics (va webhook rejimida webhook) porti
EXPOSE 8080

# Jarayon tirik bo'lsa-yu, PostgreSQL/Redis uzilgan bo'lsa — konteyner
# "unhealthy" deb belgilanadi (orkestrator qayta ishga tushirishi mumkin).
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8080/health/ready || exit 1

# Alembic migratsiyalarni ishga tushirib, so'ng botni start qiladi
CMD ["sh", "-c", "alembic upgrade head && python -m app.main"]

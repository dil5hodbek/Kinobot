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

# Alembic migratsiyalarni ishga tushirib, so'ng botni start qiladi
CMD ["sh", "-c", "alembic upgrade head && python -m app.main"]

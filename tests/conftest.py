"""Test uchun umumiy sozlamalar: app importidan OLDIN env o'rnatiladi."""
from __future__ import annotations

import os

# app.config import qilinishidan oldin majburiy env qiymatlarni beramiz
os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("STORAGE_CHANNEL_ID", "-1001234567890")
os.environ.setdefault("POSTGRES_PASSWORD", "test_pw")
os.environ.setdefault("ADMIN_IDS", "111,222,333")
os.environ.setdefault("REQUIRED_CHANNELS", "@alpha, beta , gamma")
# .env faylini o'qimasin (test muhitida)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

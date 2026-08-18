"""Prometheus metrikalar — bitta joyda e'lon qilinadi.

Label'larda YUQORI kardinallik (user_id, movie_id) ISHLATILMAYDI —
Prometheus'ni portlatib yuboradi. Faqat kichik, yopiq to'plamlar
(result: sent/blocked/failed va h.k.).
"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# === Update pipeline ===
updates_total = Counter(
    "telegram_updates_total", "Qabul qilingan Telegram update'lar"
)
update_errors_total = Counter(
    "telegram_update_errors_total", "Handlerdan chiqib ketgan xatolar"
)
update_duration_seconds = Histogram(
    "telegram_update_duration_seconds",
    "Update'ni qayta ishlash davomiyligi",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# === Biznes ===
movie_delivery_total = Counter(
    "movie_delivery_total", "Kino yuborish natijalari", ["result"]  # sent|failed
)
search_requests_total = Counter(
    "search_requests_total", "Qidiruv so'rovlari"
)
subscription_degraded_total = Counter(
    "subscription_check_degraded_total",
    "Obuna tekshiruvi degraded rejimda o'tgan holatlar",
)

# === Broadcast ===
broadcast_messages_total = Counter(
    "broadcast_messages_total",
    "Broadcast xabar natijalari",
    ["result"],  # sent|blocked|failed
)
broadcast_jobs_running = Gauge(
    "broadcast_jobs_running", "Hozir ishlanayotgan broadcast joblar"
)

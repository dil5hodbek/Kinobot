"""Barcha handler routerlarini bitta routerga yig'adi.

Ro'yxatga olish tartibi muhim: admin va menyu routerlari umumiy matn
qidiruvidan (search) OLDIN bo'lishi shart, aks holda tugma matnlari
qidiruv sifatida qabul qilinadi.
"""
from aiogram import Router

from app.handlers import (
    channel_intake,
    channels,
    clear_chat,
    language,
    search,
    start,
    subscription,
    trend,
)
from app.handlers.admin import build_admin_router


def build_router() -> Router:
    router = Router(name="root")
    # Kanal postlari (avto kino qo'shish) — alohida oqim
    router.include_router(channel_intake.router)
    router.include_router(start.router)
    router.include_router(language.router)
    router.include_router(subscription.router)
    router.include_router(build_admin_router())
    router.include_router(channels.router)
    router.include_router(trend.router)
    router.include_router(clear_chat.router)
    # search — eng oxirida (umumiy matn handleri barcha qolgan matnni tutadi)
    router.include_router(search.router)
    return router

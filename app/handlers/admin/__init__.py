"""Admin handler routerlari."""
from aiogram import Router

from app.handlers.admin import (
    add_link_movie,
    add_movie,
    broadcast,
    channels,
    codes,
    delete_movie,
    edit_movie,
    panel,
    stats,
)


def build_admin_router() -> Router:
    router = Router(name="admin")
    router.include_router(panel.router)
    router.include_router(add_movie.router)
    router.include_router(add_link_movie.router)
    router.include_router(edit_movie.router)
    router.include_router(delete_movie.router)
    router.include_router(broadcast.router)
    router.include_router(channels.router)
    router.include_router(stats.router)
    router.include_router(codes.router)
    return router

"""AdminMenuInterruptMiddleware — HAQIQIY aiogram Dispatcher orqali integratsion test.

`tests/test_admin_menu_interrupt_middleware.py` middleware'ni izolyatsiyada
(qo'lda yasalgan `handler`/`state` bilan) tekshiradi — bu middleware'ning
o'z mantig'ini tasdiqlaydi, lekin aiogram'da INNER middleware (`.middleware()`)
filtrlar tekshirilib, handler ALLAQACHON tanlangandan KEYIN ishga tushishini
qamrab olmaydi (aiogram Router.trigger() manbasida tasdiqlangan). Shu sabab
avvalgi (`.middleware()` bilan ro'yxatga olingan) versiya production'da
ishlamadi — holat kech tozalanardi.

Bu test ikkita minimal router bilan HAQIQIY Dispatcher.feed_update() orqali
xuddi production'dagi kabi: bitta oqim "kutish" holatida (StateFilter yo'q,
ixtiyoriy matnni yutadi), ikkinchisi alohida tugma bilan boshlanadi
(`StateFilter(None)` + tugma matni). Middleware `dp.message.outer_middleware`
(FILTRLARDAN OLDIN ishlaydigan qatlam) sifatida ro'yxatga olinishi SHART —
aks holda ikkinchi oqim hech qachon boshlanmaydi.
"""
from __future__ import annotations

import pytest
from aiogram import F, Router
from aiogram.dispatcher.dispatcher import Dispatcher
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import SendMessage
from aiogram.types import Update

from app.config import settings
from app.middlewares.admin_menu_interrupt import AdminMenuInterruptMiddleware
from app.utils.i18n import t
from tests.helpers import make_bot, make_message

_BUTTON_A = t("btn_add_link_movie", "uz")
_BUTTON_B = t("btn_codes", "uz")


class _FlowA(StatesGroup):
    waiting_input = State()


def _build_routers() -> tuple[Router, Router]:
    flow_a = Router(name="flow_a")

    @flow_a.message(StateFilter(None), F.text == _BUTTON_A)
    async def start_a(message, state: FSMContext) -> None:  # noqa: ANN001
        await state.set_state(_FlowA.waiting_input)
        await message.answer("A: kirish qiymatini kuting")

    @flow_a.message(_FlowA.waiting_input)
    async def got_a_input(message) -> None:  # noqa: ANN001
        # add_link_movie.got_url / edit_movie.got_edit_code kabi — holat
        # mos kelsa, matn MAZMUNIDAN qat'i nazar shu handler ishlaydi.
        await message.answer(f"A: qabul qilindi -> {message.text!r}")

    flow_b = Router(name="flow_b")

    @flow_b.message(StateFilter(None), F.text == _BUTTON_B)
    async def start_b(message) -> None:  # noqa: ANN001
        await message.answer("B: boshlandi")

    return flow_a, flow_b


def _build_dispatcher(*, outer: bool) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    if outer:
        dp.message.outer_middleware(AdminMenuInterruptMiddleware())
    else:
        dp.message.middleware(AdminMenuInterruptMiddleware())
    flow_a, flow_b = _build_routers()
    dp.include_router(flow_a)
    dp.include_router(flow_b)
    return dp


async def _send(dp: Dispatcher, bot, user_id: int, text: str, update_id: int) -> str:
    message = make_message(bot, user_id, text=text)
    update = Update.model_construct(update_id=update_id, message=message)
    await dp.feed_update(bot, update)
    method = bot.session.call_args.args[1]
    assert isinstance(method, SendMessage)
    return method.text


@pytest.mark.asyncio
async def test_outer_middleware_lets_second_button_interrupt_first_flow() -> None:
    """TUZATILGAN joylashuv: ikkinchi tugma birinchi oqimni to'g'ri bekor qiladi."""
    dp = _build_dispatcher(outer=True)
    bot = make_bot()
    bot.session.return_value = None
    admin_id = settings.admin_ids[0]

    text1 = await _send(dp, bot, admin_id, _BUTTON_A, update_id=1)
    assert text1 == "A: kirish qiymatini kuting"

    # A oqimi "waiting_input" holatida — endi B tugmasini bosamiz.
    text2 = await _send(dp, bot, admin_id, _BUTTON_B, update_id=2)
    assert text2 == "B: boshlandi"


@pytest.mark.asyncio
async def test_inner_middleware_placement_reproduces_the_bug() -> None:
    """Regression-himoya: ESKI (noto'g'ri) joylashuv buzilgan holatni saqlab qolishini
    tasdiqlaydi — shu orqali kelajakda kimdir `.middleware()`ga qaytarib
    qo'ymasin (bu test uni darhol qizil qiladi)."""
    dp = _build_dispatcher(outer=False)
    bot = make_bot()
    bot.session.return_value = None
    admin_id = settings.admin_ids[0]

    text1 = await _send(dp, bot, admin_id, _BUTTON_A, update_id=1)
    assert text1 == "A: kirish qiymatini kuting"

    # BUG: B tugmasi bosilsa ham, matn hali A oqimining "waiting_input"
    # handleriga tushib, tugma matni kirish qiymati sifatida qabul qilinadi.
    text2 = await _send(dp, bot, admin_id, _BUTTON_B, update_id=2)
    assert text2 == f"A: qabul qilindi -> {_BUTTON_B!r}"

"""_MENU_BUTTON_KEYS TO'LIQLIK testi.

Bu bug ikki marta takrorlandi: avval btn_clear_chat, keyin btn_search/
btn_channels/btn_trend/btn_language ro'yxatda yo'q edi — har safar admin
biror FSM oqimida turib o'sha tugmani bossa, matn eski oqimga tushib
"topilmadi" javobini olardi (production'da kuzatilgan haqiqiy bug).

Bu test kelajakda YANA takrorlanmasligini kafolatlaydi: ro'yxatni QO'LDA
emas, balki HAQIQIY reply-klaviatura funksiyalarini chaqirib, ulardagi
BARCHA tugma matnlarini avtomatik yig'ib, _MENU_BUTTON_KEYS shularning
barchasini qamrab olishini tekshiradi. Yangi tugma qo'shilib, ro'yxatga
kiritilishi unutilsa — bu test darhol qizil bo'ladi.
"""
from __future__ import annotations

from app.keyboards.reply import (
    admin_management_menu_keyboard,
    admin_menu_keyboard,
    admin_movies_menu_keyboard,
    main_menu_keyboard,
)
from app.middlewares.admin_menu_interrupt import _menu_button_labels
from app.utils.i18n import SUPPORTED_LANGUAGES


def _all_reply_keyboard_texts() -> set[str]:
    """Loyihadagi HAR BIR reply-klaviatura funksiyasini, HAR BIR tilda
    chaqirib, ko'rinadigan barcha tugma matnlarini yig'adi."""
    builders = (
        main_menu_keyboard,
        admin_menu_keyboard,
        admin_movies_menu_keyboard,
        admin_management_menu_keyboard,
    )
    texts: set[str] = set()
    for build in builders:
        for lang in SUPPORTED_LANGUAGES:
            markup = build(lang)
            for row in markup.keyboard:
                for btn in row:
                    texts.add(btn.text)
    return texts


def test_every_reply_keyboard_button_is_in_the_interrupt_list() -> None:
    missing = _all_reply_keyboard_texts() - _menu_button_labels()
    assert not missing, (
        "Quyidagi tugma(lar) AdminMenuInterruptMiddleware._MENU_BUTTON_KEYS "
        f"ro'yxatida yo'q — admin FSM oqimida bosilsa 'yutib' ketadi: {missing}"
    )

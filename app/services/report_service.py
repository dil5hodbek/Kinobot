"""Excel (.xlsx) hisobot xizmati: kino kodlari ro'yxati.

Bitta fayl ichida:
  • "Hammasi" varag'i — barcha kinolar
  • har bir janr uchun alohida varaq (sheet)
Ustunlar: №, Kino nomi, Kod, Janr, Yil, Ko'rishlar, Holat.

MUHIM: kino nomi, kodi va janri HECH QANDAY cheklovsiz — istalgan belgi
(masalan `& < / * :`) hujayralarga aynan yoziladi. Excel faqat varaq *yorlig'i*
(tab) uchun ba'zi belgilarni taqiqlaydi (bu Excel formatining qat'iy qoidasi),
shu sabab har varaqning ichida aniq janr nomi sarlavha qatorida ko'rsatiladi —
demak matn hech qachon yo'qolmaydi yoki o'zgarmaydi.
"""
from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.models.movie import Movie
from app.utils.format import movie_title
from app.utils.i18n import t

# Ustun kengliklari (Nomi keng, qolganlari o'rtacha)
_COL_WIDTHS = [6, 42, 12, 22, 8, 12, 12]

_TITLE_FONT = Font(bold=True, size=13, color="1F4E78")
_HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
_HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
_CENTER = Alignment(horizontal="center", vertical="center")
_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=False)
_THIN = Side(style="thin", color="D0D0D0")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_ALT_FILL = PatternFill("solid", fgColor="F2F6FC")

# Excel varaq yorlig'ida taqiqlangan belgilar (openpyxl qulamasligi uchun)
_INVALID_SHEET_CHARS = set(r"[]:*?/\\")


def _safe_sheet_tab(name: str, used: set[str]) -> str:
    """Faqat varaq YORLIG'I uchun: Excel qonuniga moslaydi va unikal qiladi.

    Bu faqat tab nomi — janrning haqiqiy matni varaq ichida to'liq saqlanadi.
    """
    cleaned = "".join(" " if ch in _INVALID_SHEET_CHARS else ch for ch in name).strip()
    cleaned = cleaned[:31] or "Sheet"
    base = cleaned
    i = 2
    while cleaned.lower() in used:
        suffix = f" ({i})"
        cleaned = (base[: 31 - len(suffix)]).rstrip() + suffix
        i += 1
    used.add(cleaned.lower())
    return cleaned


def _headers(lang: str) -> list[str]:
    return [
        t("xls_col_num", lang),
        t("xls_col_name", lang),
        t("xls_col_code", lang),
        t("xls_col_genre", lang),
        t("xls_col_year", lang),
        t("xls_col_views", lang),
        t("xls_col_status", lang),
    ]


def _fill_sheet(
    ws: Worksheet, movies: list[Movie], lang: str, title_text: str
) -> None:
    headers = _headers(lang)
    ncols = len(headers)
    dash = "—"
    no_genre = t("xls_no_genre", lang)

    # 1-qator: sarlavha (aniq matn — istalgan belgi bilan)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    title_cell = ws.cell(row=1, column=1, value=f"{title_text}  ({len(movies)})")
    title_cell.font = _TITLE_FONT
    title_cell.alignment = _LEFT
    ws.row_dimensions[1].height = 22

    # 2-qator: ustun sarlavhalari
    for col_idx, name in enumerate(headers, start=1):
        cell = ws.cell(row=2, column=col_idx, value=name)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = _CENTER
        cell.border = _BORDER

    # 3-qatordan: ma'lumotlar (hujayra qiymatlari o'zgartirilmaydi)
    for idx, movie in enumerate(movies, start=1):
        values = [
            idx,
            movie_title(movie, lang),
            movie.code,
            movie.genre or no_genre,
            movie.year or dash,
            movie.views_count,
            t("xls_active", lang) if movie.is_active else t("xls_inactive", lang),
        ]
        excel_row = idx + 2
        for col_idx, value in enumerate(values, start=1):
            cell = ws.cell(row=excel_row, column=col_idx, value=value)
            cell.border = _BORDER
            cell.alignment = _LEFT if col_idx == 2 else _CENTER
            if idx % 2 == 0:
                cell.fill = _ALT_FILL

    # Ustun kengliklari
    for col_idx, width in enumerate(_COL_WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # Sarlavha + ustun qatorini muzlatish + filtr
    ws.freeze_panes = "A3"
    last_col = get_column_letter(ncols)
    ws.auto_filter.ref = f"A2:{last_col}{max(len(movies) + 2, 2)}"


def build_movies_workbook(movies: list[Movie], lang: str) -> bytes:
    """Kinolar ro'yxatidan .xlsx bayt-massivini yaratadi."""
    wb = Workbook()
    used_tabs: set[str] = set()

    # 1) "Hammasi" varag'i
    all_label = t("xls_sheet_all", lang)
    all_ws = wb.active
    all_ws.title = _safe_sheet_tab(all_label, used_tabs)
    _fill_sheet(all_ws, movies, lang, all_label)

    # 2) Janrlar bo'yicha guruhlash — har biriga alohida varaq
    groups: dict[str, list[Movie]] = {}
    no_genre = t("xls_no_genre", lang)
    for movie in movies:
        key = (movie.genre or "").strip() or no_genre
        groups.setdefault(key, []).append(movie)

    for genre in sorted(groups, key=str.lower):
        # Yorliq xavfsiz nomlanadi, aniq janr matni varaq ichida (sarlavhada)
        ws = wb.create_sheet(title=_safe_sheet_tab(genre, used_tabs))
        _fill_sheet(ws, groups[genre], lang, genre)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()

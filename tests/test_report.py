"""Excel hisobot (report_service) testlari."""
from __future__ import annotations

import io

from openpyxl import load_workbook

from app.models.movie import Movie
from app.services.report_service import build_movies_workbook
from app.utils.i18n import t


def _movie(code: str, title: str, genre: str | None, views: int = 0) -> Movie:
    return Movie(
        code=code,
        channel_id=-100,
        message_id=1,
        title_uz=title,
        genre=genre,
        year=2024,
        views_count=views,
        is_active=True,
    )


def _sample() -> list[Movie]:
    return [
        _movie("777", "Avatar", "Fantastika", 12543),
        _movie("778", "Titanic", "Drama", 900),
        _movie("779", "Tom & Jerry", "Multfilm", 50),
        _movie("A1", "No Genre Movie", None),
    ]


def _all_sheet_name() -> str:
    return t("xls_sheet_all", "uz")[:31]


def test_workbook_has_all_sheet_and_genre_sheets() -> None:
    data = build_movies_workbook(_sample(), "uz")
    wb = load_workbook(io.BytesIO(data))
    names = wb.sheetnames
    assert _all_sheet_name() in names
    for genre in ("Fantastika", "Drama", "Multfilm", t("xls_no_genre", "uz")):
        assert genre in names


def test_all_sheet_title_headers_and_rows() -> None:
    movies = _sample()
    data = build_movies_workbook(movies, "uz")
    wb = load_workbook(io.BytesIO(data))
    ws = wb[_all_sheet_name()]

    # 1-qator — sarlavha, 2-qator — ustun nomlari
    assert t("xls_sheet_all", "uz") in str(ws.cell(row=1, column=1).value)
    header = [ws.cell(row=2, column=c).value for c in range(1, 8)]
    assert header == [
        t("xls_col_num", "uz"),
        t("xls_col_name", "uz"),
        t("xls_col_code", "uz"),
        t("xls_col_genre", "uz"),
        t("xls_col_year", "uz"),
        t("xls_col_views", "uz"),
        t("xls_col_status", "uz"),
    ]
    # sarlavha + ustun qatori + 4 kino
    assert ws.max_row == len(movies) + 2
    # Ma'lumot 3-qatordan: nom (2-ustun), kod (3-ustun)
    assert ws.cell(row=3, column=2).value == "Avatar"
    assert ws.cell(row=3, column=3).value == "777"


def test_any_character_is_accepted_no_restriction() -> None:
    """Nom/kod/janrda istalgan belgi bo'lsa ham xato bo'lmaydi va matn saqlanadi."""
    wild_genre = "Sci-Fi / Action * [2024]: ?"
    wild_title = "Tom & Jerry <HD> \"100%\" / #1"
    wild_code = "7*7/7"
    data = build_movies_workbook([_movie(wild_code, wild_title, wild_genre)], "uz")

    wb = load_workbook(io.BytesIO(data))
    ws = wb[_all_sheet_name()]
    # Hujayra qiymatlari AYNAN saqlanadi (o'zgartirilmaydi)
    assert ws.cell(row=3, column=2).value == wild_title
    assert ws.cell(row=3, column=3).value == wild_code
    assert ws.cell(row=3, column=4).value == wild_genre

    # Janr varag'i bor (yorlig'i xavfsiz), ichida ANIQ janr matni ko'rinadi
    genre_sheet = [n for n in wb.sheetnames if n != _all_sheet_name()][0]
    ws2 = wb[genre_sheet]
    assert wild_genre in str(ws2.cell(row=1, column=1).value)


def test_many_genres_with_same_prefix_get_unique_tabs() -> None:
    # 31 belgidan uzun va bir xil boshlangan janrlar — yorliqlar unikal bo'lishi kerak
    movies = [
        _movie("1", "A", "Juda uzun janr nomi bir xil boshlanadi variant bitta"),
        _movie("2", "B", "Juda uzun janr nomi bir xil boshlanadi variant ikki"),
    ]
    data = build_movies_workbook(movies, "uz")
    wb = load_workbook(io.BytesIO(data))
    # Hech qanday nom takrorlanmasligi kerak
    assert len(wb.sheetnames) == len(set(wb.sheetnames))

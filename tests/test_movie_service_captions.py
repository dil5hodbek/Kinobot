from app.models.movie import Movie
from app.services.movie_service import MovieService


def _make_movie(**overrides) -> Movie:
    defaults = dict(
        id=1,
        code="777",
        source_type="link",
        title_uz="Test kino",
        title_ru=None,
        title_en=None,
        year=2024,
        genre="drama",
        views_count=5,
        is_active=True,
    )
    defaults.update(overrides)
    return Movie(**defaults)


def test_link_caption_appends_vpn_note():
    service = MovieService(session=None)
    movie = _make_movie(source_type="link")

    base = service.caption_for(movie, "uz")
    link_caption = service._link_caption_for(movie, "uz")

    assert link_caption.startswith(base)
    assert "VPN" in link_caption
    assert link_caption != base


def test_channel_caption_has_no_vpn_note():
    service = MovieService(session=None)
    movie = _make_movie(source_type="channel", channel_id=123, message_id=456)

    caption = service.caption_for(movie, "uz")

    assert "VPN" not in caption

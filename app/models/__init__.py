"""ORM modellari."""
from app.models.movie import Movie
from app.models.movie_view import MovieView
from app.models.required_channel import RequiredChannel
from app.models.user import User

__all__ = ["User", "Movie", "MovieView", "RequiredChannel"]

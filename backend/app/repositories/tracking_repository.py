from app.models import Track
from app.repositories.base import BaseRepository


class TrackRepository(BaseRepository[Track]):
    model = Track

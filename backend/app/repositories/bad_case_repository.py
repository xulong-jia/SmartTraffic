from app.models import BadCase
from app.repositories.base import BaseRepository


class BadCaseRepository(BaseRepository[BadCase]):
    model = BadCase

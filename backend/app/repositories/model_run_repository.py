from app.models import ModelRun
from app.repositories.base import BaseRepository


class ModelRunRepository(BaseRepository[ModelRun]):
    model = ModelRun

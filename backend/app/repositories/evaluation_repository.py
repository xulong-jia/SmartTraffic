from app.models import EvaluationDataset, EvaluationResult
from app.repositories.base import BaseRepository


class EvaluationDatasetRepository(BaseRepository[EvaluationDataset]):
    model = EvaluationDataset


class EvaluationResultRepository(BaseRepository[EvaluationResult]):
    model = EvaluationResult

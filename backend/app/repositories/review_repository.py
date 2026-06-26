from app.models import ReviewComment
from app.repositories.base import BaseRepository


class ReviewCommentRepository(BaseRepository[ReviewComment]):
    model = ReviewComment

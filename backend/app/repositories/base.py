from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session


ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **values: Any) -> ModelT:
        item = self.model(**values)
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)
        return item

    def bulk_create(self, items: list[dict[str, Any]]) -> list[ModelT]:
        objects = [self.model(**item) for item in items]
        self.session.add_all(objects)
        self.session.flush()
        for item in objects:
            self.session.refresh(item)
        return objects

    def get(self, item_id: str) -> ModelT | None:
        return self.session.get(self.model, item_id)

    def list(self, **filters: Any) -> list[ModelT]:
        statement = select(self.model)
        for field, value in filters.items():
            if value is None:
                continue
            statement = statement.where(getattr(self.model, field) == value)
        statement = statement.order_by(getattr(self.model, "created_at"), getattr(self.model, "id"))
        return list(self.session.scalars(statement).all())

    def update(self, item_id: str, **values: Any) -> ModelT | None:
        item = self.get(item_id)
        if item is None:
            return None
        for field, value in values.items():
            setattr(item, field, value)
        self.session.flush()
        self.session.refresh(item)
        return item

    def delete(self, item_id: str) -> bool:
        item = self.get(item_id)
        if item is None:
            return False
        self.session.delete(item)
        self.session.flush()
        return True

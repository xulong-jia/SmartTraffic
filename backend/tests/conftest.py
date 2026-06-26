from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
import app.models  # noqa: F401


@pytest.fixture(autouse=True)
def app_uses_temp_sqlite(tmp_path: Path) -> Generator[None, None, None]:
    database_path = tmp_path / "api-test.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )

    def override_get_db() -> Generator[Session, None, None]:
        with TestingSessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        yield
    finally:
        fastapi_app.dependency_overrides.pop(get_db, None)
        engine.dispose()

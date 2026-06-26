from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


_ENGINES: dict[str, Engine] = {}
_SESSIONMAKERS: dict[str, sessionmaker[Session]] = {}


def _sqlite_connect_args(database_url: str) -> dict[str, bool]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def get_engine(database_url: str | None = None) -> Engine:
    resolved_url = database_url or get_settings().database_url
    if resolved_url not in _ENGINES:
        _ENGINES[resolved_url] = create_engine(
            resolved_url,
            connect_args=_sqlite_connect_args(resolved_url),
            future=True,
        )
    return _ENGINES[resolved_url]


def get_sessionmaker(
    engine: Engine | None = None,
    database_url: str | None = None,
) -> sessionmaker[Session]:
    if engine is not None:
        return sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            future=True,
        )

    resolved_url = database_url or get_settings().database_url
    if resolved_url not in _SESSIONMAKERS:
        _SESSIONMAKERS[resolved_url] = sessionmaker(
            bind=get_engine(resolved_url),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            future=True,
        )
    return _SESSIONMAKERS[resolved_url]


class _SessionLocalFactory:
    def __call__(self) -> Session:
        return get_sessionmaker()()


SessionLocal = _SessionLocalFactory()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

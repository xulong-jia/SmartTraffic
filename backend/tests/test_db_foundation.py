from pathlib import Path

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal, get_db, get_engine, get_sessionmaker


def test_database_url_defaults_to_local_sqlite(monkeypatch):
    monkeypatch.delenv("SMARTTRAFFIC_DATABASE_URL", raising=False)

    assert get_settings().database_url == "sqlite:///./smarttraffic.db"


def test_database_url_reads_environment(monkeypatch):
    monkeypatch.setenv("SMARTTRAFFIC_DATABASE_URL", "sqlite:////tmp/smarttraffic-test.db")

    assert get_settings().database_url == "sqlite:////tmp/smarttraffic-test.db"


def test_engine_can_be_created_and_connected(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path / 'foundation.db'}")

    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1


def test_sessionmaker_can_create_session(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path / 'sessionmaker.db'}")
    TestSessionLocal = get_sessionmaker(engine=engine)

    with TestSessionLocal() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1


def test_sessionlocal_can_create_session(monkeypatch, tmp_path):
    monkeypatch.setenv("SMARTTRAFFIC_DATABASE_URL", f"sqlite:///{tmp_path / 'sessionlocal.db'}")

    with SessionLocal() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1


def test_get_db_yields_and_closes_session(monkeypatch, tmp_path):
    monkeypatch.setenv("SMARTTRAFFIC_DATABASE_URL", f"sqlite:///{tmp_path / 'dependency.db'}")

    db_generator = get_db()
    session = next(db_generator)
    assert session.execute(text("SELECT 1")).scalar_one() == 1

    with pytest.raises(StopIteration):
        next(db_generator)
    assert not session.in_transaction()


def test_alembic_foundation_files_exist():
    backend_dir = Path(__file__).resolve().parents[1]

    assert (backend_dir / "alembic.ini").is_file()
    assert (backend_dir / "alembic" / "env.py").is_file()
    assert (backend_dir / "alembic" / "script.py.mako").is_file()
    assert (backend_dir / "alembic" / "versions").is_dir()


def test_env_example_documents_database_url():
    repo_root = Path(__file__).resolve().parents[2]

    assert "SMARTTRAFFIC_DATABASE_URL=sqlite:///./smarttraffic.db" in (
        repo_root / ".env.example"
    ).read_text(encoding="utf-8")


def test_gitignore_excludes_local_sqlite_files():
    repo_root = Path(__file__).resolve().parents[2]
    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "*.db" in gitignore
    assert "*.sqlite" in gitignore
    assert "*.sqlite3" in gitignore

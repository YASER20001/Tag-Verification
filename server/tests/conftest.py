"""
Pytest configuration — shared fixtures for all test modules.
Run from server/ directory:  pytest tests/ -v
"""
import sys
import os

# Ensure server/ is importable when pytest runs from within server/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def patched_db(monkeypatch):
    """
    Fresh in-memory SQLite DB wired into db.db_sync for one test.
    Tables are created but NOT seeded.
    """
    import db.db_sync as db_sync
    from db.models import Base

    mem_engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    TestSession = sessionmaker(bind=mem_engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=mem_engine)

    monkeypatch.setattr(db_sync, "engine", mem_engine)
    monkeypatch.setattr(db_sync, "SessionLocal", TestSession)
    return mem_engine


@pytest.fixture
def seeded_db(patched_db, monkeypatch):
    """
    In-memory DB populated with the 50 standard sample tags via init_db().
    """
    import db.db_sync as db_sync
    db_sync.init_db()
    return patched_db


# ---------------------------------------------------------------------------
# Helpers used across test modules
# ---------------------------------------------------------------------------

SAMPLE_DOCS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "sample_docs"
)


def read_sample_pdf(name: str) -> bytes:
    path = os.path.join(SAMPLE_DOCS_DIR, name)
    with open(path, "rb") as f:
        return f.read()

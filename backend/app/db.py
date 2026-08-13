from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from .config import load_settings
from .models import Base

_settings = load_settings()

_engine: Engine = create_engine(
    _settings.sqlalchemy_dsn,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


@contextmanager
def get_session() -> Session:
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


def init_db() -> None:
    Base.metadata.create_all(bind=_engine)


def db_healthcheck() -> bool:
    with _engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return result.scalar() == 1

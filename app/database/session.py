"""Database engine and unit-of-work session factories."""

import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import get_settings


def _normalize_database_url(url: str) -> str:
    """Ensure PostgreSQL URLs use the psycopg (v3) driver, not psycopg2."""

    if url.startswith("postgresql://") or url.startswith("postgres://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1).replace(
            "postgres://", "postgresql+psycopg://", 1
        )
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        relative_path = url[len("sqlite:///"):]
        if not relative_path.startswith("/"):
            absolute_path = os.path.abspath(relative_path)
            return f"sqlite:///{absolute_path}"
    return url


def create_engine_from_settings() -> Engine:
    """Build an engine for the configured PostgreSQL or SQLite database."""

    database_url = _normalize_database_url(get_settings().database_url)
    engine_options: dict[str, object] = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}
    return create_engine(database_url, **engine_options)


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Create a transaction-capable session factory."""

    database_engine = engine or create_engine_from_settings()
    return sessionmaker(bind=database_engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Yield a session and atomically commit or roll back its work."""

    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_all_tables(engine: Engine | None = None) -> None:
    """Create all SQLAlchemy model tables if they do not already exist."""

    from app.database.base import Base
    from app.models import (  # noqa: PLC0415
        Business,
        BusinessMemory,
        Customer,
        Invoice,
        InvoiceItem,
        Inventory,
        Product,
        Reminder,
        Settings,
        Supplier,
    )

    db_engine = engine or create_engine_from_settings()
    Base.metadata.create_all(bind=db_engine)

    # Verify tables were actually created
    from sqlalchemy import inspect
    inspector = inspect(db_engine)
    existing = set(inspector.get_table_names())
    required = {table.name for table in Base.metadata.tables.values()}
    missing = required - existing
    if missing:
        raise RuntimeError(
            f"Table creation failed. Missing tables: {missing}. "
            f"Existing tables: {existing}."
        )

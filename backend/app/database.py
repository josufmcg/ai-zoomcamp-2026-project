"""Database engine, session, and declarative base (backlog task 5).

The :class:`Database` object owns the SQLAlchemy engine and session factory for
one application instance. It is created by the application factory from the
``DATABASE_URL`` setting and stored on ``app.state.db`` so that request
dependencies and tests can reach it without importing a process-wide global.

Development and tests use separate URLs: ``DATABASE_URL`` for the running
application and ``TEST_DATABASE_URL`` for the test suite. The default test URL
is an in-memory SQLite database, which is created fresh for every test.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def _is_memory_sqlite(url: str) -> bool:
    """Return True for an in-memory SQLite URL such as ``sqlite:///:memory:``."""
    return url.startswith("sqlite") and ":memory:" in url


def create_db_engine(url: str, *, echo: bool = False) -> Engine:
    """Create an engine for ``url`` with sensible per-dialect options.

    In-memory SQLite databases need a single shared connection (``StaticPool``)
    so that tables created on one connection are visible to the next; the
    default pool would hand out a fresh, empty database each time.
    """
    if _is_memory_sqlite(url):
        return create_engine(
            url,
            echo=echo,
            future=True,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    return create_engine(url, echo=echo, future=True)


class Database:
    """Owns the engine and session factory for one application instance."""

    def __init__(self, url: str, *, echo: bool = False) -> None:
        self.url = url
        self.engine = create_db_engine(url, echo=echo)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
            class_=Session,
        )

    def create_all(self) -> None:
        """Create every table declared on :class:`Base`."""
        Base.metadata.create_all(self.engine)

    def drop_all(self) -> None:
        """Drop every table declared on :class:`Base`."""
        Base.metadata.drop_all(self.engine)

    def session(self) -> Session:
        """Return a new session bound to this database's engine."""
        return self.session_factory()

    def dispose(self) -> None:
        """Dispose of the connection pool. Safe to call more than once."""
        self.engine.dispose()


def get_db_session(database: Database) -> Iterator[Session]:
    """Yield a session and always close it, rolling back on error."""
    session = database.session()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

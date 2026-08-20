"""Short-lived database sessions for FastAPI dependency injection."""

from collections.abc import Iterator

from sqlalchemy.orm import Session

from .connection import get_engine


def get_session() -> Iterator[Session]:
    session = Session(get_engine())
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

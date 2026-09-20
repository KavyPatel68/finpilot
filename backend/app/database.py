from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

Base = declarative_base()

# Engine is created lazily; tests can call set_engine() to inject a test engine
_engine = None


def set_engine(engine):
    """Override the engine (used by tests to inject an in-memory engine)."""
    global _engine
    _engine = engine


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.DATABASE_URL, connect_args={"check_same_thread": False}
        )

        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return _engine


def get_session_factory(engine=None):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine or get_engine())


def get_db():
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(engine=None):
    """Create all tables. Pass an engine to use a specific DB (e.g. test in-memory)."""
    import app.models  # noqa: F401
    target = engine or get_engine()
    Base.metadata.create_all(bind=target)

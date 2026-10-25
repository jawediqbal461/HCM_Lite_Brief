from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# create_all() only creates missing *tables*, never missing columns, so adding a
# field to a model would otherwise break every existing deployment. These are
# plain additive columns, safe to apply on startup; anything that needs data
# moved or a column dropped deserves a real migration tool instead.
ADDITIVE_COLUMNS: list[tuple[str, str, str]] = [
    ("payslips", "late_penalty_days", "FLOAT DEFAULT 0"),
]


def ensure_additive_columns() -> list[str]:
    from sqlalchemy import inspect, text

    applied = []
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    for table, column, ddl in ADDITIVE_COLUMNS:
        if table not in existing_tables:
            continue  # create_all will build it with the column already present
        columns = {c["name"] for c in inspector.get_columns(table)}
        if column in columns:
            continue
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
        applied.append(f"{table}.{column}")
    return applied

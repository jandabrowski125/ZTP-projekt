"""Ensure PostgreSQL schema matches Alembic head (repairs stale alembic_version)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from user_app.db.base import Base
from user_app.db import models  # noqa: F401
from user_app.db.session import get_engine

logger = logging.getLogger(__name__)

SERVICE_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_TABLES = frozenset({"users", "custom_events", "user_saved_events"})


def _missing_tables(engine) -> set[str]:
    existing = set(inspect(engine).get_table_names())
    return REQUIRED_TABLES - existing


def ensure_schema() -> None:
    """Apply pending Alembic migrations and repair when tables are missing."""
    engine = get_engine()
    cfg = Config(str(SERVICE_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(SERVICE_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", str(engine.url))

    logger.info("Applying Alembic migrations")
    command.upgrade(cfg, "head")

    missing = _missing_tables(engine)
    if not missing:
        logger.info("Database schema is up to date")
        return

    logger.warning("Missing tables %s — rebuilding schema", sorted(missing))

    if inspect(engine).has_table("alembic_version"):
        logger.warning("Resetting alembic stamp (version row without tables)")
        command.stamp(cfg, "base")

    command.upgrade(cfg, "head")

    missing = _missing_tables(engine)
    if missing:
        logger.warning("Alembic upgrade incomplete; creating tables via metadata (%s)", sorted(missing))
        Base.metadata.create_all(engine)

    still_missing = _missing_tables(engine)
    if still_missing:
        msg = f"Failed to create tables: {sorted(still_missing)}"
        raise RuntimeError(msg)


def verify_schema() -> None:
    engine = get_engine()
    missing = _missing_tables(engine)
    if missing:
        msg = f"Database schema incomplete; missing: {sorted(missing)}"
        raise RuntimeError(msg)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1 FROM users LIMIT 1"))


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    try:
        ensure_schema()
        verify_schema()
    except Exception:
        logger.exception("Database bootstrap failed")
        return 1
    logger.info("Database bootstrap succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())

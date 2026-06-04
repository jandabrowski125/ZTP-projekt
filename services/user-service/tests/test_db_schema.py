"""Database schema readiness and bootstrap repair tests."""

from sqlalchemy import inspect, text

from user_app.db.bootstrap import REQUIRED_TABLES, ensure_schema, verify_schema


def test_required_tables_exist(engine) -> None:
    existing = set(inspect(engine).get_table_names())
    assert REQUIRED_TABLES.issubset(existing)


def test_verify_schema_passes_when_tables_exist(engine) -> None:
    verify_schema()


def test_bootstrap_repairs_missing_users_table(engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS user_saved_events CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS custom_events CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version "
                "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
        conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('001')"))
        conn.commit()

    missing = REQUIRED_TABLES - set(inspect(engine).get_table_names())
    assert "users" in missing

    ensure_schema()
    verify_schema()


def test_health_reports_database_ready(api_client) -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ready"

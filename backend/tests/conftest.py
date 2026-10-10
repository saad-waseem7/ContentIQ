"""Removes the rows the test run created in the configured database.

Several tests write users, channels, content and recommendations through the application's
own session, and nothing else cleans them up. After the session, any user that did not exist
before it started and was created after it started is deleted. The foreign keys cascade, so
channels, content, metrics, baselines and recommendations of those users go with them.

Only users that were absent when the session started and were created after it started are
deleted. Do not ingest into the same database while the suite runs.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import text


def _existing_user_ids(connection) -> set:
    return {row[0] for row in connection.execute(text("SELECT id FROM users"))}


@pytest.fixture(scope="session", autouse=True)
def remove_rows_created_by_the_test_run():
    from app.database import engine

    try:
        with engine.connect() as connection:
            before = _existing_user_ids(connection)
    except Exception:
        # No database reachable: tests that need it will report that themselves.
        yield
        return

    started_at = datetime.now(timezone.utc)
    yield

    with engine.begin() as connection:
        created = _existing_user_ids(connection) - before
        if created:
            connection.execute(
                text("DELETE FROM users WHERE id = ANY(:ids) AND created_at >= :started_at"),
                {"ids": list(created), "started_at": started_at},
            )

"""Pytest unit tests for the Resource SQL Tables"""

import pytest
from madsci.resource_manager.resource_tables import (
    ResourceHistoryTable,
    ResourceTable,
    create_session,
)
from pytest_mock_resources import PostgresConfig, create_postgres_fixture
from sqlalchemy import Engine
from sqlmodel import Session as SQLModelSession
from sqlmodel import select


@pytest.fixture(scope="session")
def pmr_postgres_config() -> PostgresConfig:
    """Configure the Postgres fixture"""
    return PostgresConfig(image="postgres:17")


# Create a Postgres fixture
postgres_engine = create_postgres_fixture(ResourceTable)


@pytest.fixture
def session(postgres_engine: Engine) -> SQLModelSession:
    """Session fixture"""
    return create_session(postgres_engine)


def test_insert(session: SQLModelSession) -> None:
    """Test inserting a resource table entry"""
    resource1 = ResourceTable(resource_name="resource1")
    session.add(resource1)
    session.commit()

    assert resource1.resource_id is not None
    assert resource1.resource_name == "resource1"
    assert resource1.removed is False
    session.close()


def test_history(session: SQLModelSession) -> None:
    """Test history of a resource table entry"""
    resource1 = ResourceTable(resource_name="resource1")
    session.add(resource1)
    session.commit()

    resource1.resource_name = "resource2"
    session.commit()

    history = session.exec(
        select(ResourceHistoryTable)
        .where(ResourceHistoryTable.resource_id == resource1.resource_id)
        .order_by(ResourceHistoryTable.changed_at.asc())
    ).all()

    assert len(history) == 2
    assert history[0].resource_name == "resource1"
    assert history[0].change_type == "Added"
    assert history[1].resource_name == "resource2"
    assert history[1].change_type == "Updated"
    session.close()


def test_remove(session: SQLModelSession) -> None:
    """Test removing a resource table entry"""
    resource1 = ResourceTable(resource_name="resource1")
    session.add(resource1)
    session.commit()

    session.delete(resource1)
    session.commit()
    resource1_live = session.exec(
        select(ResourceTable).where(ResourceTable.resource_id == resource1.resource_id)
    ).all()
    assert len(resource1_live) == 0  # * deleted resource1 is removed
    resource1_history = session.exec(
        select(ResourceHistoryTable)
        .where(ResourceHistoryTable.resource_id == resource1.resource_id)
        .order_by(ResourceHistoryTable.changed_at.asc())
    ).all()
    # * deleted resource1 is in history
    assert len(resource1_history) == 2
    assert (
        resource1_history[1].removed is True
    )  # * deleted resource1 is marked as removed
    assert (
        resource1_history[1].change_type == "Removed"
    )  # * deleted resource1 has removal history
    assert (
        resource1_history[0].removed is False
    )  # * deleted resource1 has pre-deletion history
    assert (
        resource1_history[0].change_type == "Added"
    )  # * deleted resource1 has pre-deletion history
    session.close()

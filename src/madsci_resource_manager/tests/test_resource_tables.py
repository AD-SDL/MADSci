"""Pytest unit tests for the Resource SQL Tables"""

from madsci.resource_manager.resource_tables import (
    ResourceHistoryTable,
    ResourceTable,
    add_automated_history,
)
from pytest_mock_resources import create_postgres_fixture
from sqlalchemy.engine.base import Engine
from sqlmodel import Session as SQLModelSession
from sqlmodel import select, true

# Create a Postgres fixture
postgres_engine = create_postgres_fixture(ResourceTable)


def test_insert(postgres_engine: Engine) -> None:
    """Test inserting a resource table entry"""
    session = SQLModelSession(postgres_engine)
    add_automated_history(session)
    resource1 = ResourceTable(resource_name="resource1")
    session.add(resource1)
    session.commit()

    assert resource1.resource_id is not None
    assert resource1.resource_name == "resource1"
    assert resource1.removed is False


def test_remove(postgres_engine: Engine) -> None:
    """Test removing a resource table entry"""
    session = SQLModelSession(postgres_engine)
    add_automated_history(session)
    resource1 = ResourceTable(resource_name="resource1")
    session.add(resource1)
    session.commit()

    session.delete(resource1)
    session.commit()
    session.exec(
        select(ResourceHistoryTable).where(
            ResourceHistoryTable.resource_id == resource1.resource_id
        )
    ).where(ResourceHistoryTable.removed == true()).all()

"""
Test the Experiment Manager's REST server.

Uses pytest-mock-resources to create a MongoDB fixture. Note that this _requires_
a working docker installation.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentDesign,
    ExperimentManagerDefinition,
    ExperimentRegistration,
    ExperimentStatus,
)
from madsci.experiment_manager.experiment_server import create_experiment_server
from pymongo.database import Database
from pytest_mock_resources import MongoConfig, create_mongo_fixture

experiment_manager_def = ExperimentManagerDefinition(
    name="test_experiment_manager",
)


@pytest.fixture(scope="session")
def pmr_mongo_config() -> MongoConfig:
    """Congifure the MongoDB fixture."""
    return MongoConfig(image="mongo:8.0")


db_connection = create_mongo_fixture()


@pytest.fixture()
def test_client(db_connection: Database) -> TestClient:
    """Test client fixture for the Experiment Manager's server."""
    app = create_experiment_server(
        experiment_manager_definition=experiment_manager_def,
        db_connection=db_connection,
    )
    return TestClient(app)


def test_experiment_definition(test_client: TestClient) -> None:
    """
    Test the definition endpoint for the Experiment Manager's server.
    Should return an ExperimentManagerDefinition.
    """
    result = test_client.get("/definition").json()
    ExperimentManagerDefinition.model_validate(result)


def test_experiment_roundtrip(test_client: TestClient) -> None:
    """
    Test that we can send and then retrieve an experiment by ID.
    """
    test_experiment_design = ExperimentDesign(
        experiment_name="Test Experiment",
        experiment_description="This is a test experiment.",
    )
    payload = ExperimentRegistration(
        experiment_design=test_experiment_design,
        run_name="Test Run",
        run_description="This is a test run.",
    )
    response = test_client.post("/experiment", json=payload.model_dump(mode="json"))
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is not None
    test_experiment = Experiment.model_validate(response.json())
    response = test_client.get(f"/experiment/{test_experiment.experiment_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is not None
    assert Experiment.model_validate(response.json()) == test_experiment


def test_get_experiments(test_client: TestClient) -> None:
    """
    Test that we can retrieve all experiments and they are returned as a list in reverse-chronological order, with the correct number of experiments.
    """
    test_experiment_design = ExperimentDesign(
        experiment_name="Test Experiment",
        experiment_description="This is a test experiment.",
    )
    for i in range(10):
        payload = ExperimentRegistration(
            experiment_design=test_experiment_design,
            run_name=f"Test Experiment {i}",
            run_description=f"This is test experiment {i}.",
        )
        response = test_client.post(
            "/experiment",
            json=payload.model_dump(mode="json"),
        ).json()
        Experiment.model_validate(response)
    query_number = 5
    result = test_client.get("/experiments", params={"number": query_number}).json()
    # * Check that the number of experiments returned is correct
    assert len(result) == query_number
    previous_timestamp = float("inf")
    for experiment_data in result:
        experiment = Experiment.model_validate(experiment_data)
        # * Check that the experiments are in reverse-chronological order
        assert previous_timestamp >= experiment.started_at.timestamp()
        previous_timestamp = experiment.started_at.timestamp()


def test_end_experiment(test_client: TestClient) -> None:
    """
    Test that we can end an experiment by ID.
    """
    test_experiment_design = ExperimentDesign(
        experiment_name="Test Experiment",
        experiment_description="This is a test experiment.",
    )
    payload = ExperimentRegistration(
        experiment_design=test_experiment_design,
        run_name="Test Run",
        run_description="This is a test run.",
    )
    result = test_client.post(
        "/experiment", json=payload.model_dump(mode="json")
    ).json()
    test_experiment = Experiment.model_validate(result)
    result = test_client.post(f"/experiment/{test_experiment.experiment_id}/end").json()
    ended_experiment = Experiment.model_validate(result)
    assert ended_experiment.ended_at is not None
    assert ended_experiment.experiment_id == test_experiment.experiment_id


def test_cancel_experiment(test_client: TestClient) -> None:
    """
    Test that we can cancel an experiment by ID.
    """
    test_experiment_design = ExperimentDesign(
        experiment_name="Test Experiment",
        experiment_description="This is a test experiment.",
    )
    payload = ExperimentRegistration(
        experiment_design=test_experiment_design,
        run_name="Test Run",
        run_description="This is a test run.",
    )
    result = test_client.post(
        "/experiment", json=payload.model_dump(mode="json")
    ).json()
    test_experiment = Experiment.model_validate(result)
    result = test_client.post(
        f"/experiment/{test_experiment.experiment_id}/cancel"
    ).json()
    cancelled_experiment = Experiment.model_validate(result)
    assert cancelled_experiment.status == ExperimentStatus.CANCELLED
    assert cancelled_experiment.experiment_id == test_experiment.experiment_id


def test_pause_and_resume_experiment(test_client: TestClient) -> None:
    """
    Test that we can pause and resume an experiment by ID.
    """
    test_experiment_design = ExperimentDesign(
        experiment_name="Test Experiment",
        experiment_description="This is a test experiment.",
    )
    payload = ExperimentRegistration(
        experiment_design=test_experiment_design,
        run_name="Test Run",
        run_description="This is a test run.",
    )
    result = test_client.post(
        "/experiment", json=payload.model_dump(mode="json")
    ).json()
    test_experiment = Experiment.model_validate(result)
    result = test_client.post(
        f"/experiment/{test_experiment.experiment_id}/pause"
    ).json()
    paused_experiment = Experiment.model_validate(result)
    assert paused_experiment.status == ExperimentStatus.PAUSED
    assert paused_experiment.experiment_id == test_experiment.experiment_id
    result = test_client.post(
        f"/experiment/{test_experiment.experiment_id}/continue"
    ).json()
    resumed_experiment = Experiment.model_validate(result)
    assert resumed_experiment.status == ExperimentStatus.IN_PROGRESS
    assert resumed_experiment.experiment_id == test_experiment.experiment_id


def test_fail_experiment(test_client: TestClient) -> None:
    """
    Test that we can fail an experiment by ID.
    """
    test_experiment_design = ExperimentDesign(
        experiment_name="Test Experiment",
        experiment_description="This is a test experiment.",
    )
    payload = ExperimentRegistration(
        experiment_design=test_experiment_design,
        run_name="Test Run",
        run_description="This is a test run.",
    )
    result = test_client.post(
        "/experiment", json=payload.model_dump(mode="json")
    ).json()
    test_experiment = Experiment.model_validate(result)
    result = test_client.post(
        f"/experiment/{test_experiment.experiment_id}/fail"
    ).json()
    failed_experiment = Experiment.model_validate(result)
    assert failed_experiment.status == ExperimentStatus.FAILED
    assert failed_experiment.experiment_id == test_experiment.experiment_id

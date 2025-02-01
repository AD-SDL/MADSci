"""
Test the Experiment Manager's REST server.

Uses pytest-mock-resources to create a MongoDB fixture. Note that this _requires_
a working docker installation.
"""

from fastapi.testclient import TestClient
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentDesign,
    ExperimentManagerDefinition,
)
from madsci.experiment_manager.experiment_server import ExperimentServer
from pymongo.database import Database
from pytest_mock_resources import create_mongo_fixture

db_connection = create_mongo_fixture()

experiment_manager_def = ExperimentManagerDefinition(
    name="test_experiment_manager",
)


def test_experiment_definition(db_connection: Database) -> None:
    """
    Test the definition endpoint for the Experiment Manager's server.
    Should return an ExperimentManagerDefinition.
    """
    experiment_manager_server = ExperimentServer(
        experiment_manager_definition=experiment_manager_def,
        db_connection=db_connection,
        enable_ui=False,
    )
    test_client = TestClient(experiment_manager_server.app)
    result = test_client.get("/definition").json()
    ExperimentManagerDefinition.model_validate(result)


def test_experiment_roundtrip(db_connection: Database) -> None:
    """
    Test that we can send and then retrieve an experiment by ID.
    """
    experiment_manager_server = ExperimentServer(
        experiment_manager_definition=experiment_manager_def,
        db_connection=db_connection,
        enable_ui=False,
    )
    test_client = TestClient(experiment_manager_server.app)
    test_experiment_design = ExperimentDesign(
        experiment_name="Test Experiment",
        experiment_description="This is a test experiment.",
    )
    result = test_client.post(
        "/experiment", json=test_experiment_design.model_dump(mode="json")
    ).json()
    test_experiment = Experiment.model_validate(result)
    result = test_client.get(f"/experiment/{test_experiment.experiment_id}").json()
    assert Experiment.model_validate(result) == test_experiment


def test_get_experiments(db_connection: Database) -> None:
    """
    Test that we can retrieve all experiments and they are returned as a list in reverse-chronological order, with the correct number of experiments.
    """
    experiment_manager_server = ExperimentServer(
        experiment_manager_definition=experiment_manager_def,
        db_connection=db_connection,
        enable_ui=False,
    )
    test_client = TestClient(experiment_manager_server.app)
    test_experiment_design = ExperimentDesign(
        experiment_name="Test Experiment",
        experiment_description="This is a test experiment.",
    )
    for i in range(10):
        response = test_client.post(
            "/experiment",
            json=test_experiment_design.model_dump(mode="json"),
            params={
                "run_name": f"Test Experiment {i}",
                "run_description": f"This is test experiment {i}.",
            },
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


def test_end_experiment(db_connection: Database) -> None:
    """
    Test that we can end an experiment by ID.
    """
    experiment_manager_server = ExperimentServer(
        experiment_manager_definition=experiment_manager_def,
        db_connection=db_connection,
        enable_ui=False,
    )
    test_client = TestClient(experiment_manager_server.app)
    test_experiment_design = ExperimentDesign(
        experiment_name="Test Experiment",
        experiment_description="This is a test experiment.",
    )
    result = test_client.post(
        "/experiment", json=test_experiment_design.model_dump(mode="json")
    ).json()
    test_experiment = Experiment.model_validate(result)
    result = test_client.post(f"/experiment/{test_experiment.experiment_id}/end").json()
    ended_experiment = Experiment.model_validate(result)
    assert ended_experiment.ended_at is not None
    assert ended_experiment.experiment_id == test_experiment.experiment_id

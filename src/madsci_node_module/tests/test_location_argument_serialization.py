"""Tests for LocationArgument serialization in REST client."""

from unittest.mock import MagicMock, patch

from madsci.client.node.rest_node_client import RestNodeClient, _serialize_for_json
from madsci.common.types.action_types import ActionRequest
from madsci.common.types.location_types import LocationArgument


class TestLocationArgumentSerialization:
    """Test LocationArgument serialization functionality."""

    def test_serialize_for_json_with_location_argument(self):
        """Test that _serialize_for_json properly handles LocationArgument."""
        location_arg = LocationArgument(
            representation="test_location",
            resource_id="resource_123",
            location_name="test_location_name",
        )

        result = _serialize_for_json(location_arg)

        # Should be a dictionary with all fields
        assert isinstance(result, dict)
        assert result["representation"] == "test_location"
        assert result["resource_id"] == "resource_123"
        assert result["location_name"] == "test_location_name"
        assert result["reservation"] is None

    def test_serialize_for_json_with_nested_location_arguments(self):
        """Test serialization of complex structures containing LocationArguments."""
        location1 = LocationArgument(representation="loc1", location_name="location1")
        location2 = LocationArgument(representation="loc2", location_name="location2")

        complex_structure = {
            "target_location": location1,
            "source_location": location2,
            "speed": 50,
            "locations_list": [location1, location2],
            "nested": {"inner_location": location1, "value": "test"},
        }

        result = _serialize_for_json(complex_structure)

        # Check that all LocationArguments were serialized
        assert isinstance(result["target_location"], dict)
        assert result["target_location"]["representation"] == "loc1"

        assert isinstance(result["source_location"], dict)
        assert result["source_location"]["representation"] == "loc2"

        # Check list serialization
        assert isinstance(result["locations_list"], list)
        assert len(result["locations_list"]) == 2
        assert isinstance(result["locations_list"][0], dict)
        assert result["locations_list"][0]["representation"] == "loc1"

        # Check nested dict serialization
        assert isinstance(result["nested"]["inner_location"], dict)
        assert result["nested"]["inner_location"]["representation"] == "loc1"
        assert result["nested"]["value"] == "test"

        # Check that non-LocationArgument values are preserved
        assert result["speed"] == 50

    def test_serialize_for_json_with_var_args_and_kwargs(self):
        """Test serialization of var_args and var_kwargs containing LocationArguments."""
        location_arg = LocationArgument(
            representation="var_location", location_name="var_loc"
        )

        var_args = [location_arg, "string_arg", 42]
        var_kwargs = {"location_kwarg": location_arg, "regular_kwarg": "value"}

        serialized_var_args = _serialize_for_json(var_args)
        serialized_var_kwargs = _serialize_for_json(var_kwargs)

        # Check var_args
        assert isinstance(serialized_var_args, list)
        assert len(serialized_var_args) == 3
        assert isinstance(serialized_var_args[0], dict)
        assert serialized_var_args[0]["representation"] == "var_location"
        assert serialized_var_args[1] == "string_arg"
        assert serialized_var_args[2] == 42

        # Check var_kwargs
        assert isinstance(serialized_var_kwargs, dict)
        assert isinstance(serialized_var_kwargs["location_kwarg"], dict)
        assert (
            serialized_var_kwargs["location_kwarg"]["representation"] == "var_location"
        )
        assert serialized_var_kwargs["regular_kwarg"] == "value"

    @patch("requests.post")
    def test_rest_client_serializes_location_arguments(self, mock_post):
        """Test that RestNodeClient properly serializes LocationArguments."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"action_id": "test_action_id"}
        mock_post.return_value = mock_response

        # Create client and LocationArgument
        client = RestNodeClient(url="http://localhost:8000")
        location_arg = LocationArgument(
            representation="client_location",
            resource_id="client_resource",
            location_name="client_location_name",
        )

        # Create ActionRequest with LocationArgument
        action_request = ActionRequest(
            action_name="test_action",
            args={"target_location": location_arg, "speed": 75},
        )

        # Call _create_action
        result = client._create_action(action_request)

        # Verify the result
        assert result == "test_action_id"

        # Verify the call was made correctly
        assert mock_post.called
        call_args = mock_post.call_args

        # Check the JSON payload structure
        json_payload = call_args[1]["json"]
        assert "args" in json_payload

        args = json_payload["args"]
        assert "target_location" in args
        assert "speed" in args

        # LocationArgument should be serialized to dict
        target_location = args["target_location"]
        assert isinstance(target_location, dict)
        assert target_location["representation"] == "client_location"
        assert target_location["resource_id"] == "client_resource"
        assert target_location["location_name"] == "client_location_name"
        assert target_location["reservation"] is None

        # Other args should be preserved
        assert args["speed"] == 75

    @patch("requests.post")
    def test_rest_client_serializes_location_arguments_in_var_args_kwargs(
        self, mock_post
    ):
        """Test that RestNodeClient serializes LocationArguments in var_args and var_kwargs."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"action_id": "test_action_id"}
        mock_post.return_value = mock_response

        client = RestNodeClient(url="http://localhost:8000")
        location_arg = LocationArgument(
            representation="var_location", location_name="var_loc"
        )

        # Create ActionRequest with LocationArgument in var_args and var_kwargs
        action_request = ActionRequest(
            action_name="test_action",
            args={"base_param": "value"},
            var_args=[location_arg, "extra_param"],
            var_kwargs={"extra_location": location_arg, "extra_value": 42},
        )

        # Call _create_action
        client._create_action(action_request)

        # Verify the call
        call_args = mock_post.call_args
        json_payload = call_args[1]["json"]

        # Check var_args serialization
        assert "var_args" in json_payload
        var_args = json_payload["var_args"]
        assert isinstance(var_args, list)
        assert len(var_args) == 2
        assert isinstance(var_args[0], dict)  # LocationArgument should be serialized
        assert var_args[0]["representation"] == "var_location"
        assert var_args[1] == "extra_param"

        # Check var_kwargs serialization
        assert "var_kwargs" in json_payload
        var_kwargs = json_payload["var_kwargs"]
        assert isinstance(var_kwargs, dict)
        assert isinstance(
            var_kwargs["extra_location"], dict
        )  # LocationArgument should be serialized
        assert var_kwargs["extra_location"]["representation"] == "var_location"
        assert var_kwargs["extra_value"] == 42

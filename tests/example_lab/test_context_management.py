"""
Test context and ownership management.

These tests validate OwnershipInfo usage and MadsciContext configuration
for proper service integration in the example lab.
"""

from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.context_types import MadsciContext
from madsci.common.utils import new_ulid_str


class TestOwnershipInfo:
    """Test OwnershipInfo structure and validation."""

    def test_ownership_info_structure(self, ownership_info):
        """Test OwnershipInfo structure and validation."""
        assert ownership_info.user_id is not None
        assert ownership_info.lab_id is not None
        assert ownership_info.experiment_id is not None
        assert len(ownership_info.user_id) > 0

    def test_ownership_info_optional_fields(self):
        """Test OwnershipInfo with only required fields."""
        minimal_ownership = OwnershipInfo(user_id=new_ulid_str())
        assert minimal_ownership.user_id is not None
        assert minimal_ownership.lab_id is None  # Optional field

    def test_ownership_comparison(self, ownership_info):
        """Test ownership comparison functionality."""
        other_ownership = OwnershipInfo(
            user_id=ownership_info.user_id,
            lab_id=ownership_info.lab_id,
            experiment_id=ownership_info.experiment_id,
        )

        # Test comparison method
        assert ownership_info.check(other_ownership) is True

        # Test with different ownership
        different_ownership = OwnershipInfo(user_id=new_ulid_str())
        assert ownership_info.check(different_ownership) is False


class TestMadsciContext:
    """Test MadsciContext configuration for services."""

    def test_context_service_urls(self, madsci_context):
        """Test MadsciContext service URL configuration."""
        assert madsci_context.lab_server_url is not None
        assert madsci_context.event_server_url is not None
        assert madsci_context.resource_server_url is not None
        assert madsci_context.workcell_server_url is not None

    def test_context_url_format(self, madsci_context):
        """Test that service URLs are properly formatted."""
        urls = [
            madsci_context.lab_server_url,
            madsci_context.event_server_url,
            madsci_context.resource_server_url,
            madsci_context.workcell_server_url,
        ]

        for url in urls:
            if url:
                assert str(url).startswith("http")
                assert "localhost" in str(url)

    def test_context_creation_with_custom_urls(self):
        """Test creating context with custom service URLs."""
        custom_context = MadsciContext(
            event_server_url="http://custom-event:8001",
            resource_server_url="http://custom-resource:8003",
        )

        assert "custom-event" in str(custom_context.event_server_url)
        assert "custom-resource" in str(custom_context.resource_server_url)


class TestContextIntegration:
    """Test context integration patterns."""

    def test_ownership_in_resource_operations(self, ownership_info):
        """Test ownership context in resource operations."""
        resource_operation = {
            "operation_type": "create_resource",
            "resource_data": {"name": "test-plate", "type": "container"},
            "ownership": ownership_info.model_dump(exclude_none=True),
        }

        # Validate ownership is included
        assert "ownership" in resource_operation
        assert resource_operation["ownership"]["user_id"] == ownership_info.user_id

    def test_context_in_workflow_execution(self, ownership_info, madsci_context):
        """Test context integration during workflow execution."""
        workflow_execution = {
            "workflow_id": new_ulid_str(),
            "execution_id": new_ulid_str(),
            "ownership": ownership_info.model_dump(exclude_none=True),
            "service_context": {
                "workcell_url": str(madsci_context.workcell_server_url),
                "resource_url": str(madsci_context.resource_server_url),
            },
        }

        # Validate context integration
        assert "ownership" in workflow_execution
        assert "service_context" in workflow_execution
        assert "workcell_url" in workflow_execution["service_context"]

    def test_ownership_serialization(self, ownership_info):
        """Test ownership info serialization excludes None values."""
        serialized = ownership_info.model_dump(exclude_none=True)

        # Should only include non-None values
        for value in serialized.values():
            assert value is not None

        # Required fields should be present
        assert "user_id" in serialized


class TestOwnershipPatterns:
    """Test common ownership usage patterns."""

    def test_experiment_ownership_tracking(self, ownership_info):
        """Test experiment ownership tracking patterns."""
        experiment_data = {
            "experiment_id": ownership_info.experiment_id,
            "owner": ownership_info.model_dump(exclude_none=True),
            "created_at": "2024-01-01T12:00:00Z",
            "status": "active",
        }

        assert experiment_data["experiment_id"] == ownership_info.experiment_id
        assert "owner" in experiment_data

    def test_resource_ownership_allocation(self, ownership_info):
        """Test resource ownership during allocation."""
        resource_allocation = {
            "resource_id": new_ulid_str(),
            "allocated_to": ownership_info.model_dump(exclude_none=True),
            "allocation_timestamp": "2024-01-01T12:00:00Z",
            "allocation_type": "experiment",
        }

        # Validate allocation structure
        assert "allocated_to" in resource_allocation
        assert resource_allocation["allocated_to"]["user_id"] == ownership_info.user_id

    def test_ownership_transfer_validation(self, ownership_info):
        """Test ownership transfer validation patterns."""
        transfer_data = {
            "current_owner": ownership_info.model_dump(exclude_none=True),
            "new_owner": {
                "user_id": new_ulid_str(),
                "lab_id": ownership_info.lab_id,  # Same lab
            },
            "transfer_reason": "experiment_handoff",
        }

        # Validate transfer structure
        assert "current_owner" in transfer_data
        assert "new_owner" in transfer_data
        assert transfer_data["new_owner"]["lab_id"] == ownership_info.lab_id

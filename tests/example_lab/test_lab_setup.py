"""
Test lab initialization and setup functionality.

These tests validate that the example lab can be properly initialized,
services are healthy, and basic lab configuration is correct.
"""

import httpx
import pytest

from .conftest import TestConfig


class TestLabSetup:
    """Test lab initialization and basic setup."""

    def test_service_health_checks(self, lab_services_health_check):
        """Test that all required MADSci services are running and healthy."""
        assert lab_services_health_check is True

    @pytest.mark.requires_services
    def test_event_manager_connectivity(self):
        """Test connectivity to event manager service."""
        try:
            response = httpx.get(f"{TestConfig.EVENT_MANAGER_URL}", timeout=5.0)
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Event manager service not available")

    @pytest.mark.requires_services
    def test_resource_manager_connectivity(self):
        """Test connectivity to resource manager service."""
        try:
            response = httpx.get(f"{TestConfig.RESOURCE_MANAGER_URL}", timeout=5.0)
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Resource manager service not available")

    @pytest.mark.requires_services
    def test_workcell_manager_connectivity(self):
        """Test connectivity to workcell manager service."""
        try:
            response = httpx.get(f"{TestConfig.WORKCELL_MANAGER_URL}", timeout=5.0)
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Workcell manager service not available")

    @pytest.mark.requires_services
    def test_experiment_manager_connectivity(self):
        """Test connectivity to experiment manager service."""
        try:
            response = httpx.get(f"{TestConfig.EXPERIMENT_MANAGER_URL}", timeout=5.0)
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Experiment manager service not available")

    @pytest.mark.requires_services
    def test_data_manager_connectivity(self):
        """Test connectivity to data manager service."""
        try:
            response = httpx.get(f"{TestConfig.DATA_MANAGER_URL}", timeout=5.0)
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Data manager service not available")

    def test_lab_config_structure(self, example_lab_config):
        """Test that lab configuration has required structure."""
        assert "lab_id" in example_lab_config
        assert "name" in example_lab_config
        assert "managers" in example_lab_config
        assert len(example_lab_config["managers"]) >= 4  # Minimum required managers

    def test_lab_config_manager_ports(self, example_lab_config):
        """Test that manager ports are properly configured."""
        managers = example_lab_config["managers"]
        expected_ports = {8001, 8002, 8003, 8004, 8005}
        configured_ports = {manager["port"] for manager in managers.values()}
        assert expected_ports.issubset(configured_ports)


class TestLabInitialization:
    """Test lab initialization sequence."""

    def test_lab_registration(self, example_lab_config, madsci_context):
        """Test lab registration process."""
        # This test would validate lab registration with the lab manager
        # For now, we'll test the configuration structure
        assert example_lab_config["lab_id"] is not None
        assert madsci_context.lab_server_url is not None

    def test_manager_registration(self, lab_services_health_check):
        """Test that managers can be registered and discovered."""
        if not lab_services_health_check:
            pytest.skip("Services not available for manager registration test")

        # Test would validate manager discovery and registration
        # This is a placeholder for when manager registration is implemented
        assert True

    def test_node_discovery(self, lab_services_health_check):
        """Test node discovery and registration."""
        if not lab_services_health_check:
            pytest.skip("Services not available for node discovery test")

        # Test would validate that example nodes can be discovered
        # This is a placeholder for when node discovery is implemented
        assert True

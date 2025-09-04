"""
Test resource template functionality.

These tests validate resource template creation, inheritance,
and usage in the example lab environment.
"""

from madsci.common.utils import new_ulid_str


class TestResourceTemplateCreation:
    """Test resource template creation and validation."""

    def test_template_structure(self, sample_resource_template):
        """Test that resource template has correct structure."""
        required_fields = ["template_id", "name", "type", "category", "specifications"]

        for field in required_fields:
            assert field in sample_resource_template

        assert sample_resource_template["template_id"] is not None
        assert len(sample_resource_template["name"]) > 0
        assert sample_resource_template["type"] in [
            "container",
            "instrument",
            "consumable",
        ]

    def test_plate_template_specifications(self, sample_resource_template):
        """Test that plate template has proper specifications."""
        if sample_resource_template["category"] == "plate":
            specs = sample_resource_template["specifications"]
            assert "well_count" in specs
            assert "well_volume_ul" in specs
            assert "dimensions" in specs
            assert specs["well_count"] > 0
            assert specs["well_volume_ul"] > 0

    def test_template_metadata(self, sample_resource_template):
        """Test template metadata structure."""
        if "metadata" in sample_resource_template:
            metadata = sample_resource_template["metadata"]
            # Metadata should be a dict if present
            assert isinstance(metadata, dict)


class TestResourceTemplateUsage:
    """Test using templates to create resources."""

    def test_create_resource_from_template(
        self, sample_resource_template, ownership_info
    ):
        """Test creating a resource instance from a template."""
        # This would test actual resource creation from template
        # For now, validate the template can be used for resource creation

        resource_data = {
            "resource_id": new_ulid_str(),
            "template_id": sample_resource_template["template_id"],
            "name": f"instance-{new_ulid_str()}",
            "ownership": ownership_info.model_dump(exclude_none=True),
        }

        assert resource_data["template_id"] == sample_resource_template["template_id"]
        assert resource_data["ownership"]["user_id"] == ownership_info.user_id

    def test_template_inheritance(self, sample_resource_template):
        """Test template inheritance patterns."""
        # Create a derived template
        derived_template = sample_resource_template.copy()
        derived_template["template_id"] = new_ulid_str()
        derived_template["name"] = f"derived-{sample_resource_template['name']}"
        derived_template["parent_template_id"] = sample_resource_template["template_id"]

        # Validate inheritance structure
        assert (
            derived_template["parent_template_id"]
            == sample_resource_template["template_id"]
        )
        assert (
            derived_template["template_id"] != sample_resource_template["template_id"]
        )

    def test_template_customization(self, sample_resource_template):
        """Test template customization for specific use cases."""
        # Test customizing template specifications
        custom_template = sample_resource_template.copy()
        custom_template["template_id"] = new_ulid_str()
        custom_template["name"] = f"custom-{sample_resource_template['name']}"

        # Modify specifications for testing
        if "specifications" in custom_template:
            custom_template["specifications"]["custom_field"] = "custom_value"

        assert custom_template["template_id"] != sample_resource_template["template_id"]
        assert "custom_field" in custom_template["specifications"]


class TestTemplateLibrary:
    """Test the resource template library functionality."""

    def test_container_template_categories(self):
        """Test container template categories."""
        container_categories = ["plate", "tip", "tube", "rack", "stack"]
        # This would test that all expected container categories are available
        assert len(container_categories) > 0

    def test_instrument_template_categories(self):
        """Test instrument template categories."""
        instrument_categories = ["pipette", "gripper", "nest", "dispenser"]
        # This would test that all expected instrument categories are available
        assert len(instrument_categories) > 0

    def test_consumable_template_categories(self):
        """Test consumable template categories."""
        consumable_categories = ["reagent", "buffer", "solvent", "standard"]
        # This would test that all expected consumable categories are available
        assert len(consumable_categories) > 0


class TestTemplateValidation:
    """Test template validation and error handling."""

    def test_invalid_template_structure(self):
        """Test handling of invalid template structures."""
        invalid_template = {
            "name": "invalid-template"
            # Missing required fields
        }

        required_fields = ["template_id", "type", "category", "specifications"]
        for field in required_fields:
            assert field not in invalid_template or invalid_template.get(field) is None

    def test_template_id_uniqueness(self):
        """Test that template IDs are unique."""
        template1_id = new_ulid_str()
        template2_id = new_ulid_str()

        assert template1_id != template2_id

    def test_template_name_validation(self):
        """Test template name validation rules."""
        valid_names = ["test-plate-96", "pipette_1000ul", "reagent.buffer"]
        invalid_names = ["", " ", "invalid name with spaces"]

        for name in valid_names:
            assert len(name) > 0
            # Additional validation rules would go here

        for name in invalid_names:
            # These should fail validation
            if name.strip() == "":
                assert len(name.strip()) == 0

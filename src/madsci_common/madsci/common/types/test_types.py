"""Types used for testing MADSci type components."""

from madsci.common.types.base_types import MadsciBaseSettings


class TestSettings(MadsciBaseSettings, env_file="*test.env", env_prefix="TEST_"):
    """Settings for testing MADSci components."""

    test_field_1: str = "test_value_1"
    test_field_2: int = 42

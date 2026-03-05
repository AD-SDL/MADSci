"""Tests for the deprecation utilities."""

import warnings
from pathlib import Path
from typing import Optional

from madsci.common.deprecation import (
    DEPRECATED_IN,
    REMOVAL_IN,
    MadsciDeprecationWarning,
    deprecated,
    deprecated_parameter,
    emit_definition_deprecation_warning,
)


class TestEmitDefinitionDeprecationWarning:
    """Tests for the emit_definition_deprecation_warning function."""

    def test_emits_warning(self, tmp_path: Path) -> None:
        """Test that the function emits a deprecation warning."""
        def_path = tmp_path / "test.manager.yaml"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            emit_definition_deprecation_warning(def_path, "manager")

            assert len(w) == 1
            assert issubclass(w[0].category, MadsciDeprecationWarning)
            assert "manager" in str(w[0].message)
            assert str(def_path) in str(w[0].message)

    def test_includes_version_info(self, tmp_path: Path) -> None:
        """Test that the warning includes version information."""
        def_path = tmp_path / "test.manager.yaml"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            emit_definition_deprecation_warning(def_path, "manager")

            message = str(w[0].message)
            assert DEPRECATED_IN in message
            assert REMOVAL_IN in message

    def test_includes_migration_command(self, tmp_path: Path) -> None:
        """Test that the warning includes the migration command."""
        def_path = tmp_path / "test.manager.yaml"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            emit_definition_deprecation_warning(
                def_path,
                "manager",
                migration_command="madsci migrate convert test.manager.yaml",
            )

            message = str(w[0].message)
            assert "madsci migrate convert test.manager.yaml" in message

    def test_default_migration_hint(self, tmp_path: Path) -> None:
        """Test default migration hint when no command specified."""
        def_path = tmp_path / "test.manager.yaml"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            emit_definition_deprecation_warning(def_path, "manager")

            message = str(w[0].message)
            assert "madsci migrate" in message


class TestDeprecatedDecorator:
    """Tests for the @deprecated decorator."""

    def test_emits_warning_on_call(self) -> None:
        """Test that decorated function emits warning when called."""

        @deprecated(reason="Use new_func instead")
        def old_func() -> str:
            return "result"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = old_func()

            assert result == "result"
            assert len(w) == 1
            assert issubclass(w[0].category, MadsciDeprecationWarning)
            assert "old_func" in str(w[0].message)
            assert "Use new_func instead" in str(w[0].message)

    def test_includes_replacement(self) -> None:
        """Test that warning includes replacement suggestion."""

        @deprecated(reason="Obsolete", replacement="new_function")
        def old_function() -> None:
            pass

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            old_function()

            message = str(w[0].message)
            assert "new_function" in message

    def test_includes_version_info(self) -> None:
        """Test that warning includes version information."""

        @deprecated(reason="Test", deprecated_in="0.5.0", removal_in="0.6.0")
        def versioned_func() -> None:
            pass

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            versioned_func()

            message = str(w[0].message)
            assert "0.5.0" in message
            assert "0.6.0" in message

    def test_preserves_function_metadata(self) -> None:
        """Test that decorator preserves function metadata."""

        @deprecated(reason="Test")
        def documented_func() -> None:
            """This is my docstring."""

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This is my docstring."

    def test_passes_arguments(self) -> None:
        """Test that decorator passes arguments correctly."""

        @deprecated(reason="Test")
        def func_with_args(a: int, b: str, c: bool = False) -> tuple:
            return (a, b, c)

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = func_with_args(1, "hello", c=True)

            assert result == (1, "hello", True)


class TestDeprecatedParameterDecorator:
    """Tests for the @deprecated_parameter decorator."""

    def test_warns_when_parameter_used(self) -> None:
        """Test that warning is emitted when deprecated parameter is used."""

        @deprecated_parameter("old_param", reason="Use new_param")
        def my_func(
            new_param: Optional[str] = None, old_param: Optional[str] = None
        ) -> str:
            return old_param or new_param or "default"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = my_func(old_param="value")

            assert result == "value"
            assert len(w) == 1
            assert issubclass(w[0].category, MadsciDeprecationWarning)
            assert "old_param" in str(w[0].message)

    def test_no_warning_when_parameter_not_used(self) -> None:
        """Test that no warning is emitted when deprecated parameter is not used."""

        @deprecated_parameter("old_param", reason="Use new_param")
        def my_func(
            new_param: Optional[str] = None,
            old_param: Optional[str] = None,  # noqa: ARG001
        ) -> str:
            return new_param or "default"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = my_func(new_param="value")

            assert result == "value"
            assert len(w) == 0

    def test_no_warning_when_parameter_is_none(self) -> None:
        """Test that no warning is emitted when parameter is explicitly None."""

        @deprecated_parameter("old_param", reason="Use new_param")
        def my_func(
            new_param: Optional[str] = None,
            old_param: Optional[str] = None,  # noqa: ARG001
        ) -> str:
            return new_param or "default"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = my_func(old_param=None)

            assert result == "default"
            assert len(w) == 0

    def test_includes_replacement(self) -> None:
        """Test that warning includes replacement suggestion."""

        @deprecated_parameter("old_param", reason="Obsolete", replacement="new_param")
        def my_func(
            new_param: Optional[str] = None, old_param: Optional[str] = None
        ) -> str:
            return old_param or new_param or "default"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            my_func(old_param="value")

            message = str(w[0].message)
            assert "new_param" in message


class TestMadsciDeprecationWarning:
    """Tests for the MadsciDeprecationWarning class."""

    def test_is_deprecation_warning_subclass(self) -> None:
        """Test that MadsciDeprecationWarning is a DeprecationWarning subclass."""
        assert issubclass(MadsciDeprecationWarning, DeprecationWarning)

    def test_warning_not_filtered_by_default(self) -> None:
        """Test that MadsciDeprecationWarning is not filtered by default."""
        # This test verifies the warning filter is set up correctly
        with warnings.catch_warnings(record=True) as w:
            # Use "default" to match the filter we set
            warnings.filterwarnings("default", category=MadsciDeprecationWarning)
            warnings.warn("Test warning", MadsciDeprecationWarning, stacklevel=2)

            assert len(w) == 1
            assert issubclass(w[0].category, MadsciDeprecationWarning)

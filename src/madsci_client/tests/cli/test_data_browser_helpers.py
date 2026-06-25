"""Tests for data browser helper functions after DataPoint model migration.

These tests verify that the helper functions in the data_browser screen
correctly extract and format data from DataPoint model instances rather
than raw dictionaries.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from madsci.common.types.datapoint_types import (
    DataPointTypeEnum,
    FileDataPoint,
    ObjectStorageDataPoint,
    ValueDataPoint,
)


@pytest.fixture
def json_datapoint() -> ValueDataPoint:
    """Create a sample JSON/value datapoint."""
    return ValueDataPoint(
        datapoint_id="test-json-dp-001",
        label="temperature_reading",
        data_type=DataPointTypeEnum.JSON,
        data_timestamp=datetime(2026, 4, 9, 12, 0, 0),
        value={"temp": 25.5, "unit": "celsius"},
    )


@pytest.fixture
def file_datapoint() -> FileDataPoint:
    """Create a sample file datapoint."""
    return FileDataPoint(
        datapoint_id="test-file-dp-001",
        label="spectrum_data",
        data_type=DataPointTypeEnum.FILE,
        data_timestamp=datetime(2026, 4, 9, 13, 0, 0),
        path="/data/spectra/sample_001.csv",
    )


@pytest.fixture
def object_storage_datapoint() -> ObjectStorageDataPoint:
    """Create a sample object storage datapoint."""
    return ObjectStorageDataPoint(
        datapoint_id="test-obj-dp-001",
        label="image_capture",
        data_type=DataPointTypeEnum.OBJECT_STORAGE,
        data_timestamp=datetime(2026, 4, 9, 14, 0, 0),
        storage_endpoint="localhost:8333",
        bucket_name="madsci-data",
        object_name="experiments/img_001.png",
        content_type="image/png",
        size_bytes=1024000,
        url="http://localhost:9333/madsci-data/experiments/img_001.png",
        path=".scratch/img_001.png",
    )


@pytest.fixture
def unlabeled_datapoint() -> ValueDataPoint:
    """Create a datapoint with no label."""
    return ValueDataPoint(
        datapoint_id="test-nolabel-dp-001",
        label=None,
        data_type=DataPointTypeEnum.JSON,
        data_timestamp=datetime(2026, 4, 9, 15, 0, 0),
        value="simple string",
    )


class TestGetDataType:
    """Tests for _get_data_type helper."""

    def test_json_type(self, json_datapoint: ValueDataPoint) -> None:
        from madsci.client.cli.tui.screens.data_browser import _get_data_type

        assert _get_data_type(json_datapoint) == "json"

    def test_file_type(self, file_datapoint: FileDataPoint) -> None:
        from madsci.client.cli.tui.screens.data_browser import _get_data_type

        assert _get_data_type(file_datapoint) == "file"

    def test_object_storage_type(
        self, object_storage_datapoint: ObjectStorageDataPoint
    ) -> None:
        from madsci.client.cli.tui.screens.data_browser import _get_data_type

        assert _get_data_type(object_storage_datapoint) == "object_storage"


class TestGetPreview:
    """Tests for _get_preview helper."""

    def test_json_preview(self, json_datapoint: ValueDataPoint) -> None:
        from madsci.client.cli.tui.screens.data_browser import _get_preview

        preview = _get_preview(json_datapoint)
        assert preview != "-"
        assert "temp" in preview or "25.5" in preview

    def test_file_preview_returns_filename(self, file_datapoint: FileDataPoint) -> None:
        from madsci.client.cli.tui.screens.data_browser import _get_preview

        preview = _get_preview(file_datapoint)
        assert preview == "sample_001.csv"

    def test_object_storage_preview(
        self, object_storage_datapoint: ObjectStorageDataPoint
    ) -> None:
        from madsci.client.cli.tui.screens.data_browser import _get_preview

        preview = _get_preview(object_storage_datapoint)
        assert "img_001.png" in preview

    def test_json_none_value(self) -> None:
        from madsci.client.cli.tui.screens.data_browser import _get_preview

        dp = ValueDataPoint(
            datapoint_id="test-none-dp",
            data_type=DataPointTypeEnum.JSON,
            value=None,
        )
        assert _get_preview(dp) == "-"


class TestMatchesFilter:
    """Tests for _matches_filter helper."""

    def test_no_filters_matches(self, json_datapoint: ValueDataPoint) -> None:
        from madsci.client.cli.tui.screens.data_browser import _matches_filter

        assert _matches_filter(json_datapoint, "", {}) is True

    def test_type_filter_matches(self, json_datapoint: ValueDataPoint) -> None:
        from madsci.client.cli.tui.screens.data_browser import _matches_filter

        assert _matches_filter(json_datapoint, "", {"type": "json"}) is True

    def test_type_filter_no_match(self, json_datapoint: ValueDataPoint) -> None:
        from madsci.client.cli.tui.screens.data_browser import _matches_filter

        assert _matches_filter(json_datapoint, "", {"type": "file"}) is False

    def test_type_filter_all(self, json_datapoint: ValueDataPoint) -> None:
        from madsci.client.cli.tui.screens.data_browser import _matches_filter

        assert _matches_filter(json_datapoint, "", {"type": "all"}) is True

    def test_search_matches_label(self, json_datapoint: ValueDataPoint) -> None:
        from madsci.client.cli.tui.screens.data_browser import _matches_filter

        assert _matches_filter(json_datapoint, "temperature", {}) is True

    def test_search_case_insensitive(self, json_datapoint: ValueDataPoint) -> None:
        from madsci.client.cli.tui.screens.data_browser import _matches_filter

        assert _matches_filter(json_datapoint, "TEMPERATURE", {}) is True

    def test_search_no_match(self, json_datapoint: ValueDataPoint) -> None:
        from madsci.client.cli.tui.screens.data_browser import _matches_filter

        assert _matches_filter(json_datapoint, "nonexistent", {}) is False

    def test_unlabeled_datapoint_search(
        self, unlabeled_datapoint: ValueDataPoint
    ) -> None:
        from madsci.client.cli.tui.screens.data_browser import _matches_filter

        # Search on a datapoint with no label should not match
        assert _matches_filter(unlabeled_datapoint, "something", {}) is False

    def test_unlabeled_datapoint_no_search(
        self, unlabeled_datapoint: ValueDataPoint
    ) -> None:
        from madsci.client.cli.tui.screens.data_browser import _matches_filter

        # With no search term, should still pass
        assert _matches_filter(unlabeled_datapoint, "", {}) is True


class TestBuildGeneralSection:
    """Tests for _build_general_section helper."""

    def test_general_section_fields(self, json_datapoint: ValueDataPoint) -> None:
        from madsci.client.cli.tui.screens.data_browser import _build_general_section

        section = _build_general_section(json_datapoint)
        assert section.title == "General"
        assert section.fields["ID"] == "test-json-dp-001"
        assert section.fields["Label"] == "temperature_reading"
        assert section.fields["Type"] == "json"
        assert "Timestamp" in section.fields

    def test_general_section_no_label(
        self, unlabeled_datapoint: ValueDataPoint
    ) -> None:
        from madsci.client.cli.tui.screens.data_browser import _build_general_section

        section = _build_general_section(unlabeled_datapoint)
        assert section.fields["Label"] == "Unknown"


class TestBuildJsonSection:
    """Tests for _build_json_section (was _build_value_section)."""

    def test_json_section_dict_value(self, json_datapoint: ValueDataPoint) -> None:
        from madsci.client.cli.tui.screens.data_browser import _build_json_section

        section = _build_json_section(json_datapoint)
        assert section is not None
        assert section.title == "Value"
        assert "Data" in section.fields

    def test_json_section_none_value(self) -> None:
        from madsci.client.cli.tui.screens.data_browser import _build_json_section

        dp = ValueDataPoint(
            datapoint_id="test-none",
            data_type=DataPointTypeEnum.JSON,
            value=None,
        )
        assert _build_json_section(dp) is None

    def test_json_section_string_value(self) -> None:
        from madsci.client.cli.tui.screens.data_browser import _build_json_section

        dp = ValueDataPoint(
            datapoint_id="test-str",
            data_type=DataPointTypeEnum.JSON,
            value="hello world",
        )
        section = _build_json_section(dp)
        assert section is not None
        assert "hello world" in section.fields["Data"]


class TestBuildFileSection:
    """Tests for _build_file_section (was _build_storage_section)."""

    def test_file_section_has_path(self, file_datapoint: FileDataPoint) -> None:
        from madsci.client.cli.tui.screens.data_browser import _build_file_section

        section = _build_file_section(file_datapoint)
        assert section is not None
        assert section.title == "File"
        assert "Path" in section.fields
        assert "sample_001.csv" in section.fields["Path"]


class TestBuildObjectStorageSection:
    """Tests for _build_object_storage_section helper."""

    def test_object_storage_section_fields(
        self, object_storage_datapoint: ObjectStorageDataPoint
    ) -> None:
        from madsci.client.cli.tui.screens.data_browser import (
            _build_object_storage_section,
        )

        section = _build_object_storage_section(object_storage_datapoint)
        assert section is not None
        assert section.title == "Storage"
        assert "Endpoint" in section.fields
        assert section.fields["Endpoint"] == "localhost:8333"
        assert "Bucket" in section.fields
        assert section.fields["Bucket"] == "madsci-data"
        assert "Object Name" in section.fields
        assert "img_001.png" in section.fields["Object Name"]


class TestDatapointsDataType:
    """Tests that verify datapoints_data stores DataPoint models, not dicts."""

    def test_screen_datapoints_data_type_annotation(self) -> None:
        """Verify the type annotation is dict[str, DataPoint]."""
        from madsci.client.cli.tui.screens.data_browser import DataBrowserScreen

        screen = DataBrowserScreen()
        # The datapoints_data should be a dict, and when populated
        # it should hold DataPoint models, not raw dicts
        assert isinstance(screen.datapoints_data, dict)

    def test_screen_has_data_client_attribute(self) -> None:
        """Verify the screen has a _data_client attribute for lazy init."""
        from madsci.client.cli.tui.screens.data_browser import DataBrowserScreen

        screen = DataBrowserScreen()
        assert hasattr(screen, "_data_client")
        assert screen._data_client is None

    def test_screen_has_get_data_client_method(self) -> None:
        """Verify the screen has a _get_data_client method."""
        from madsci.client.cli.tui.screens.data_browser import DataBrowserScreen

        screen = DataBrowserScreen()
        assert hasattr(screen, "_get_data_client")
        assert callable(screen._get_data_client)

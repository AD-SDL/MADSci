"""Tests for the FOSS stack migration tool."""

from pathlib import Path
from unittest.mock import patch

import pytest
from madsci.common.foss_migration import (
    DEFAULT_DOCUMENT_DBS,
    FossMigrationReport,
    FossMigrationSettings,
    FossMigrationStepResult,
    FossMigrationTool,
)

# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


class TestFossMigrationStepResult:
    """Tests for FossMigrationStepResult model."""

    def test_success_result(self) -> None:
        result = FossMigrationStepResult(
            step="test_step",
            success=True,
            message="All good",
        )
        assert result.step == "test_step"
        assert result.success is True
        assert result.error is None
        assert result.duration_seconds == 0.0

    def test_failure_result(self) -> None:
        result = FossMigrationStepResult(
            step="test_step",
            success=False,
            message="Something broke",
            error="details here",
            duration_seconds=1.5,
        )
        assert result.success is False
        assert result.error == "details here"
        assert result.duration_seconds == 1.5

    def test_result_with_details(self) -> None:
        result = FossMigrationStepResult(
            step="test_step",
            success=True,
            message="OK",
            details={"copied": ["a", "b"]},
        )
        assert result.details == {"copied": ["a", "b"]}

    def test_serialization_roundtrip(self) -> None:
        result = FossMigrationStepResult(
            step="test",
            success=True,
            message="OK",
            duration_seconds=2.0,
        )
        data = result.model_dump(mode="json")
        restored = FossMigrationStepResult.model_validate(data)
        assert restored.step == result.step
        assert restored.success == result.success


class TestFossMigrationReport:
    """Tests for FossMigrationReport model."""

    def test_empty_report(self) -> None:
        report = FossMigrationReport()
        assert report.steps == []
        assert report.all_succeeded is False
        assert report.total_duration_seconds == 0.0

    def test_report_all_succeeded(self) -> None:
        report = FossMigrationReport(
            steps=[
                FossMigrationStepResult(
                    step="a", success=True, message="ok", duration_seconds=1.0
                ),
                FossMigrationStepResult(
                    step="b", success=True, message="ok", duration_seconds=2.0
                ),
            ]
        )
        assert report.all_succeeded is True
        assert report.total_duration_seconds == 3.0

    def test_report_with_failure(self) -> None:
        report = FossMigrationReport(
            steps=[
                FossMigrationStepResult(step="a", success=True, message="ok"),
                FossMigrationStepResult(step="b", success=False, message="fail"),
            ]
        )
        assert report.all_succeeded is False


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class TestFossMigrationSettings:
    """Tests for FossMigrationSettings."""

    def test_defaults(self) -> None:
        settings = FossMigrationSettings(enable_registry_resolution=False)
        assert "27018" in str(settings.old_document_db_url)
        assert "27017" in str(settings.new_document_db_url)
        assert "5433" in str(settings.old_postgres_url)
        assert "5434" in str(settings.new_postgres_url)
        assert settings.document_db_databases == DEFAULT_DOCUMENT_DBS
        # Path may be resolved to absolute by the settings system
        assert str(settings.backup_dir).endswith(".madsci/backups/foss_migration")

    def test_env_var_override(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "FOSS_MIGRATION_OLD_POSTGRES_URL": "postgresql://user:pass@host:9999/mydb"
            },
        ):
            settings = FossMigrationSettings(enable_registry_resolution=False)
        assert "9999" in settings.old_postgres_url

    def test_custom_databases(self) -> None:
        settings = FossMigrationSettings(
            document_db_databases=["custom_db"],
            enable_registry_resolution=False,
        )
        assert settings.document_db_databases == ["custom_db"]


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


class TestDetectOldData:
    """Tests for FossMigrationTool.detect_old_data."""

    def test_no_data(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".madsci").mkdir()
        tool = FossMigrationTool(
            settings=FossMigrationSettings(enable_registry_resolution=False)
        )
        detected = tool.detect_old_data()
        assert detected["mongodb"] is False
        assert detected["redis"] is False

    def test_with_mongodb_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".madsci" / "mongodb").mkdir(parents=True)
        tool = FossMigrationTool(
            settings=FossMigrationSettings(enable_registry_resolution=False)
        )
        detected = tool.detect_old_data()
        assert detected["mongodb"] is True
        assert detected["redis"] is False

    def test_with_redis_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".madsci" / "redis").mkdir(parents=True)
        tool = FossMigrationTool(
            settings=FossMigrationSettings(enable_registry_resolution=False)
        )
        detected = tool.detect_old_data()
        assert detected["redis"] is True


# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------


class TestCheckPrerequisites:
    """Tests for FossMigrationTool.check_prerequisites."""

    def test_all_tools_present(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/tool"):
            tool = FossMigrationTool(
                settings=FossMigrationSettings(enable_registry_resolution=False)
            )
            result = tool.check_prerequisites()
        assert result.success is True

    def test_missing_mongodump(self) -> None:
        def fake_which(name: str) -> str | None:
            if name == "mongodump":
                return None
            return "/usr/bin/" + name

        with patch("shutil.which", side_effect=fake_which):
            tool = FossMigrationTool(
                settings=FossMigrationSettings(enable_registry_resolution=False)
            )
            result = tool.check_prerequisites()
        assert result.success is False
        assert "mongodump" in result.error

    def test_all_tools_missing(self) -> None:
        with patch("shutil.which", return_value=None):
            tool = FossMigrationTool(
                settings=FossMigrationSettings(enable_registry_resolution=False)
            )
            result = tool.check_prerequisites()
        assert result.success is False
        assert "mongodump" in result.error
        assert "pg_dump" in result.error
        assert "psql" in result.error


# ---------------------------------------------------------------------------
# Command construction
# ---------------------------------------------------------------------------


class TestCommandBuilding:
    """Tests for mongodump/mongorestore/pg_dump/pg_restore command building."""

    def setup_method(self) -> None:
        self.tool = FossMigrationTool(
            settings=FossMigrationSettings(enable_registry_resolution=False)
        )

    def test_mongodump_command(self) -> None:
        cmd = self.tool.build_mongodump_command("madsci_events")
        assert cmd[0] == "mongodump"
        assert "--host" in cmd
        assert "--db" in cmd
        assert "madsci_events" in cmd
        # Old URL has no auth by default
        assert "--username" not in cmd

    def test_mongorestore_command(self) -> None:
        dump_path = ".scratch/dump/madsci_events"
        cmd = self.tool.build_mongorestore_command("madsci_events", dump_path)
        assert cmd[0] == "mongorestore"
        assert "--drop" in cmd
        assert "--db" in cmd
        assert "madsci_events" in cmd
        assert dump_path in cmd
        # New URL has auth
        assert "--username" in cmd

    def test_mongorestore_includes_credentials(self) -> None:
        cmd = self.tool.build_mongorestore_command("test_db", ".scratch/dump")
        # Default new URL is mongodb://madsci:madsci@localhost:27017/
        username_idx = cmd.index("--username")
        assert cmd[username_idx + 1] == "madsci"
        password_idx = cmd.index("--password")
        assert cmd[password_idx + 1] == "madsci"
        assert "--authenticationDatabase" in cmd
        auth_idx = cmd.index("--authenticationDatabase")
        assert cmd[auth_idx + 1] == "admin"

    def test_mongodump_no_auth_database_without_creds(self) -> None:
        cmd = self.tool.build_mongodump_command("test_db")
        # Default old URL has no auth
        assert "--authenticationDatabase" not in cmd

    def test_mongorestore_auth_database_with_creds(self) -> None:
        cmd = self.tool.build_mongorestore_command("test_db", ".scratch/dump")
        # Default new URL has auth (madsci:madsci)
        assert "--authenticationDatabase" in cmd

    def test_pg_dump_command(self) -> None:
        cmd = self.tool.build_pg_dump_command()
        assert cmd[0] == "pg_dump"
        assert "-h" in cmd
        assert "-p" in cmd
        # Old PG port is 5433
        port_idx = cmd.index("-p")
        assert cmd[port_idx + 1] == "5433"
        assert "--format=custom" in cmd

    def test_pg_restore_command(self) -> None:
        cmd = self.tool.build_pg_restore_command(".scratch/dump.dump")
        assert cmd[0] == "pg_restore"
        assert "--clean" in cmd
        assert "--if-exists" in cmd
        # New PG port is 5434 (dedicated resources container)
        port_idx = cmd.index("-p")
        assert cmd[port_idx + 1] == "5434"


# ---------------------------------------------------------------------------
# Redis -> Valkey  (skipped — ephemeral data)
# ---------------------------------------------------------------------------


class TestRedisToValkey:
    """Tests for Redis-to-Valkey skip behaviour."""

    def test_always_skips(self) -> None:
        tool = FossMigrationTool(
            settings=FossMigrationSettings(enable_registry_resolution=False)
        )
        result = tool.migrate_redis_to_valkey()
        assert result.success is True
        assert "skipped" in result.message.lower()
        assert "ephemeral" in result.message.lower()


# ---------------------------------------------------------------------------
# MinIO skip logic
# ---------------------------------------------------------------------------


class TestMinioSkip:
    """Tests for MinIO migration skip when no data exists."""

    def test_skip_when_no_minio_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".madsci").mkdir()
        tool = FossMigrationTool(
            settings=FossMigrationSettings(enable_registry_resolution=False)
        )
        result = tool.migrate_minio_to_seaweedfs()
        assert result.success is True
        assert "skipping" in result.message.lower()

    def test_skip_when_only_minio_sys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        minio_dir = tmp_path / ".madsci" / "minio"
        minio_dir.mkdir(parents=True)
        (minio_dir / ".minio.sys").mkdir()
        tool = FossMigrationTool(
            settings=FossMigrationSettings(enable_registry_resolution=False)
        )
        result = tool.migrate_minio_to_seaweedfs()
        assert result.success is True
        assert "skipping" in result.message.lower()
        assert "metadata" in result.message.lower()

    def test_has_user_data_false_for_empty(self, tmp_path: Path) -> None:
        minio_dir = tmp_path / "minio"
        assert FossMigrationTool._has_user_data_in_minio(minio_dir) is False

    def test_has_user_data_false_for_minio_sys_only(self, tmp_path: Path) -> None:
        minio_dir = tmp_path / "minio"
        minio_dir.mkdir()
        (minio_dir / ".minio.sys").mkdir()
        assert FossMigrationTool._has_user_data_in_minio(minio_dir) is False

    def test_has_user_data_true_for_bucket(self, tmp_path: Path) -> None:
        minio_dir = tmp_path / "minio"
        minio_dir.mkdir()
        (minio_dir / ".minio.sys").mkdir()
        (minio_dir / "my-bucket").mkdir()
        assert FossMigrationTool._has_user_data_in_minio(minio_dir) is True


# ---------------------------------------------------------------------------
# Pre-migration backup
# ---------------------------------------------------------------------------


class TestPreMigrationBackup:
    """Tests for pre-migration backup."""

    def test_backup_with_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        madsci_dir = tmp_path / ".madsci"
        # Create some mock data
        (madsci_dir / "mongodb").mkdir(parents=True)
        (madsci_dir / "mongodb" / "data.wt").write_bytes(b"data")
        (madsci_dir / "redis").mkdir(parents=True)
        (madsci_dir / "redis" / "dump.rdb").write_bytes(b"rdb")

        tool = FossMigrationTool(
            settings=FossMigrationSettings(enable_registry_resolution=False)
        )
        result = tool.create_pre_migration_backup()
        assert result.success is True
        assert "2" in result.message  # 2 dirs copied (mongodb + redis)

    def test_backup_no_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".madsci").mkdir()
        tool = FossMigrationTool(
            settings=FossMigrationSettings(enable_registry_resolution=False)
        )
        result = tool.create_pre_migration_backup()
        assert result.success is True
        assert "0" in result.message


# ---------------------------------------------------------------------------
# Docker lifecycle
# ---------------------------------------------------------------------------


class TestDockerLifecycle:
    """Tests for start/stop old containers."""

    def test_compose_cmd_construction(self) -> None:
        tool = FossMigrationTool(
            settings=FossMigrationSettings(
                compose_dir=Path("/my/lab"),
                enable_registry_resolution=False,
            )
        )
        cmd = tool._compose_cmd("up", "-d")
        assert cmd[0] == "docker"
        assert cmd[1] == "compose"
        assert "-f" in cmd
        assert str(Path("/my/lab") / "compose.infra.yaml") in cmd
        assert str(Path("/my/lab") / "compose.migration.yaml") in cmd
        assert "up" in cmd
        assert "-d" in cmd

    def test_compose_cmd_without_migration(self) -> None:
        tool = FossMigrationTool(
            settings=FossMigrationSettings(
                compose_dir=Path("/my/lab"),
                enable_registry_resolution=False,
            )
        )
        cmd = tool._compose_cmd("up", "-d", include_migration=False)
        assert str(Path("/my/lab") / "compose.infra.yaml") in cmd
        assert str(Path("/my/lab") / "compose.migration.yaml") not in cmd

    def test_compose_cmd_custom_files(self) -> None:
        tool = FossMigrationTool(
            settings=FossMigrationSettings(
                compose_dir=Path("/my/lab"),
                compose_files=["docker-compose.yml"],
                migration_compose_files=["docker-compose.migration.yml"],
                enable_registry_resolution=False,
            )
        )
        cmd = tool._compose_cmd("up", "-d")
        assert str(Path("/my/lab") / "docker-compose.yml") in cmd
        assert str(Path("/my/lab") / "docker-compose.migration.yml") in cmd
        assert "compose.infra.yaml" not in str(cmd)

    def test_start_failure(self) -> None:
        tool = FossMigrationTool(
            settings=FossMigrationSettings(enable_registry_resolution=False)
        )
        with patch("subprocess.run", side_effect=FileNotFoundError("docker not found")):
            result = tool.start_old_containers()
        assert result.success is False

    def test_stop_failure(self) -> None:
        tool = FossMigrationTool(
            settings=FossMigrationSettings(enable_registry_resolution=False)
        )
        with patch("subprocess.run", side_effect=FileNotFoundError("docker not found")):
            result = tool.stop_old_containers()
        assert result.success is False


# ---------------------------------------------------------------------------
# Full migration orchestration
# ---------------------------------------------------------------------------


class TestRunFullMigration:
    """Tests for the run_full_migration orchestrator."""

    def test_stops_on_prerequisite_failure(self) -> None:
        tool = FossMigrationTool(
            settings=FossMigrationSettings(enable_registry_resolution=False)
        )
        with patch.object(
            tool,
            "check_prerequisites",
            return_value=FossMigrationStepResult(
                step="check_prerequisites",
                success=False,
                message="Missing tools",
                error="mongodump not found",
            ),
        ):
            report = tool.run_full_migration(skip_backup=True, skip_docker=True)

        assert report.all_succeeded is False
        assert len(report.steps) == 1
        assert report.finished_at is not None

    def test_runs_selected_steps(self) -> None:
        tool = FossMigrationTool(
            settings=FossMigrationSettings(enable_registry_resolution=False)
        )
        ok = FossMigrationStepResult(step="ok", success=True, message="ok")

        with (
            patch.object(tool, "check_prerequisites", return_value=ok),
            patch.object(
                tool, "migrate_redis_to_valkey", return_value=ok
            ) as mock_redis,
            patch.object(tool, "verify_migration", return_value=ok),
        ):
            report = tool.run_full_migration(
                skip_backup=True, skip_docker=True, steps=["redis"]
            )

        mock_redis.assert_called_once()
        assert report.all_succeeded is True

    def test_unknown_step(self) -> None:
        tool = FossMigrationTool(
            settings=FossMigrationSettings(enable_registry_resolution=False)
        )
        ok = FossMigrationStepResult(step="ok", success=True, message="ok")

        with (
            patch.object(tool, "check_prerequisites", return_value=ok),
            patch.object(tool, "verify_migration", return_value=ok),
        ):
            report = tool.run_full_migration(
                skip_backup=True, skip_docker=True, steps=["nonexistent"]
            )

        # Should have a failure step for the unknown name
        unknown_steps = [s for s in report.steps if s.step == "nonexistent"]
        assert len(unknown_steps) == 1
        assert unknown_steps[0].success is False

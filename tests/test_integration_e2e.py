"""
Integration Tests: End-to-End Verification
============================================

Integration tests that verify all Phase 5 components work together.
These tests use real filesystem operations (via tmp_path) to verify
actual behavior, not just mocked interactions.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

# Import atoms
from src.director.utils import (
    resolve_absolute_path,
    validate_path_is_absolute,
    get_harness_root,
    format_command_for_logging,
    run_command,
)

# Import molecules
from src.director.cwd_guard import (
    WorkingDirectoryGuard,
    validate_cwd,
)

# Import organisms
from progress import (
    detect_rogue_beads_dirs,
    enforce_single_beads_database,
)
from beads_config import (
    BEADS_ROOT,
    SPECS_DIR,
    HARNESS_ROOT,
)


class TestCwdGuardWithRunCommandIntegration:
    """
    Integration test: WorkingDirectoryGuard + run_command molecule.

    Verifies that the CWD guard properly protects against directory drift
    even when executing commands that might change cwd.
    """

    def test_guard_restores_cwd_after_command_execution(self, tmp_path):
        """
        E2E: CWD guard restores working directory after command runs.

        Flow:
        1. Set cwd to a known directory
        2. Enter WorkingDirectoryGuard context
        3. Execute a command via run_command
        4. Simulate cwd drift within context
        5. Verify cwd is restored on exit
        """
        original_cwd = Path.cwd().resolve()
        test_dir = tmp_path / "guard_run_test"
        test_dir.mkdir()

        os.chdir(test_dir)

        try:
            with WorkingDirectoryGuard(test_dir):
                # Execute a real command (not affecting cwd)
                result = run_command(["echo", "test"], test_dir)
                assert result.returncode == 0

                # Simulate drift - something changes cwd
                other_dir = tmp_path / "other"
                other_dir.mkdir()
                os.chdir(other_dir)

            # Guard should have restored cwd
            assert Path.cwd().resolve() == test_dir.resolve()
        finally:
            os.chdir(original_cwd)

    def test_guard_validates_before_command_execution(self, tmp_path):
        """
        E2E: Guard validation happens before any commands can run.

        If cwd is wrong when entering the guard, no commands should execute.
        """
        original_cwd = Path.cwd().resolve()
        expected_dir = tmp_path / "expected"
        wrong_dir = tmp_path / "wrong"
        expected_dir.mkdir()
        wrong_dir.mkdir()

        # Set cwd to wrong_dir, but guard expects expected_dir
        os.chdir(wrong_dir)

        try:
            with pytest.raises(RuntimeError) as exc_info:
                with WorkingDirectoryGuard(expected_dir):
                    # This should never execute
                    run_command(["echo", "should not run"], expected_dir)
                    pytest.fail("Should not reach here")

            assert "mismatch" in str(exc_info.value).lower()
        finally:
            os.chdir(original_cwd)


class TestRunCommandForbidsCwd:
    """
    Integration test: run_command molecule enforces cwd prohibition.

    The run_command function must NEVER accept cwd as a parameter.
    This is a critical architectural constraint.
    """

    def test_run_command_raises_on_cwd_parameter(self, tmp_path):
        """
        E2E: run_command raises ValueError if cwd is passed.

        This enforcement ensures all path resolution uses absolute paths
        rather than relying on working directory changes.
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with pytest.raises(ValueError) as exc_info:
            run_command(
                ["echo", "test"],
                project_dir,
                cwd="/some/other/path"  # Forbidden!
            )

        error_msg = str(exc_info.value)
        assert "cwd" in error_msg.lower()
        assert "forbidden" in error_msg.lower()

    def test_run_command_uses_absolute_paths_instead(self, tmp_path):
        """
        E2E: run_command converts relative args to absolute paths.

        Instead of using cwd, run_command makes all paths absolute.
        """
        project_dir = tmp_path / "project"
        tests_dir = project_dir / "tests"
        project_dir.mkdir()
        tests_dir.mkdir()

        # Create a file to verify path resolution
        test_file = tests_dir / "test.txt"
        test_file.write_text("test content")

        # run_command should convert "tests/test.txt" to absolute path
        result = run_command(
            ["cat", "tests/test.txt"],
            project_dir,
            capture_output=True,
            text=True
        )

        # The command should succeed because path was made absolute
        assert result.returncode == 0
        assert "test content" in result.stdout


class TestPathUtilitiesWithRealFilesystem:
    """
    Integration test: Path utilities with actual filesystem operations.

    Verifies that resolve_absolute_path handles real paths correctly,
    including symlinks and relative paths.
    """

    def test_resolve_absolute_path_handles_symlinks(self, tmp_path):
        """
        E2E: resolve_absolute_path follows symlinks to real path.
        """
        real_dir = tmp_path / "real_dir"
        real_dir.mkdir()

        symlink_path = tmp_path / "symlink_dir"
        symlink_path.symlink_to(real_dir)

        resolved = resolve_absolute_path(symlink_path)

        # Resolved path should point to the real directory
        assert resolved.is_absolute()
        assert resolved == real_dir.resolve()

    def test_path_resolution_chain_consistency(self, tmp_path):
        """
        E2E: Multiple path operations maintain consistency.

        Path flow: relative -> absolute -> validated -> used in command
        """
        # Create nested structure
        project = tmp_path / "project"
        src = project / "src"
        src.mkdir(parents=True)

        # Create a test file
        test_file = src / "main.py"
        test_file.write_text("print('hello')")

        # Start with relative path from project root
        original_cwd = Path.cwd().resolve()
        os.chdir(project)

        try:
            relative_path = Path("src/main.py")

            # Step 1: Resolve to absolute
            absolute_path = resolve_absolute_path(relative_path)
            assert validate_path_is_absolute(absolute_path)

            # Step 2: Use in command
            result = run_command(
                ["python", str(absolute_path)],
                project,
                capture_output=True,
                text=True
            )

            assert result.returncode == 0
            assert "hello" in result.stdout
        finally:
            os.chdir(original_cwd)


class TestMigrationWorkflowIntegration:
    """
    Integration test: Full migration workflow components.

    Tests the migration script components with real filesystem,
    verifying detection -> validation -> cleanup flow.
    """

    def test_rogue_detection_to_enforcement_chain(self, tmp_path):
        """
        E2E: Detection feeds into enforcement correctly.

        1. Create rogue .beads/ directory
        2. Verify detect_rogue_beads_dirs finds it
        3. Verify enforce_single_beads_database raises
        4. Clean up and verify both pass
        """
        # We need to use the real SPECS_DIR for this test
        if not SPECS_DIR.exists():
            pytest.skip("SPECS_DIR does not exist")

        test_spec_dir = SPECS_DIR / "_integration_test_spec"
        rogue_beads = test_spec_dir / ".beads"

        try:
            # Create rogue directory
            test_spec_dir.mkdir(exist_ok=True)
            rogue_beads.mkdir(exist_ok=True)

            # Step 1: Detection should find it
            rogue_dirs = detect_rogue_beads_dirs()
            assert rogue_beads in rogue_dirs, "Detection should find rogue .beads/"

            # Step 2: Enforcement should fail
            with pytest.raises(RuntimeError) as exc_info:
                enforce_single_beads_database()

            assert "violation" in str(exc_info.value).lower()
            assert str(rogue_beads) in str(exc_info.value)

        finally:
            # Cleanup
            if rogue_beads.exists():
                rogue_beads.rmdir()
            if test_spec_dir.exists():
                test_spec_dir.rmdir()

        # Step 3: After cleanup, both should pass
        rogue_dirs = detect_rogue_beads_dirs()
        assert rogue_beads not in rogue_dirs

        # Should not raise now
        enforce_single_beads_database()

    def test_harness_root_consistency_across_modules(self):
        """
        E2E: HARNESS_ROOT matches get_harness_root() across modules.

        All modules must agree on where the harness root is.
        """
        harness_from_config = HARNESS_ROOT
        harness_from_utils = get_harness_root()
        beads_root_default = BEADS_ROOT  # When env var not set

        assert harness_from_config == harness_from_utils, (
            f"Config says {harness_from_config}, utils says {harness_from_utils}"
        )

        # BEADS_ROOT should default to HARNESS_ROOT
        if os.environ.get("BEADS_ROOT") is None:
            assert beads_root_default == harness_from_config


class TestValidationEnforcementChain:
    """
    Integration test: Full validation chain from atoms to organisms.

    Verifies that validation flows correctly from:
    atoms (path validation) -> molecules (cwd guard) -> organisms (enforcement)
    """

    def test_full_validation_stack(self, tmp_path):
        """
        E2E: Complete validation from path -> cwd -> architecture.

        This test exercises the full validation stack:
        1. Validate paths are absolute (atom)
        2. Validate cwd is correct (molecule)
        3. Validate architecture is correct (organism)
        """
        original_cwd = Path.cwd().resolve()
        test_dir = tmp_path / "validation_test"
        test_dir.mkdir()

        os.chdir(test_dir)

        try:
            # Layer 1: Atom - path validation
            assert validate_path_is_absolute(test_dir)
            resolved = resolve_absolute_path(test_dir)
            assert resolved.is_absolute()

            # Layer 2: Molecule - cwd validation
            validate_cwd(test_dir)  # Should not raise

            # Layer 3: Molecule - cwd guard
            with WorkingDirectoryGuard(test_dir):
                # Inside guard, we can safely operate
                pass

            # Layer 4: Organism - architecture validation
            # (only runs if no rogue dirs exist - which should be true)
            enforce_single_beads_database()

        finally:
            os.chdir(original_cwd)

    def test_validation_fails_fast_at_correct_layer(self, tmp_path):
        """
        E2E: Validation failures occur at the appropriate layer.

        Bad path -> atom fails
        Bad cwd -> molecule fails
        Bad architecture -> organism fails
        """
        original_cwd = Path.cwd().resolve()

        # Test 1: Atom layer - relative path detection
        relative_path = Path("relative/path")
        assert not validate_path_is_absolute(relative_path)

        # Test 2: Molecule layer - cwd mismatch
        wrong_dir = tmp_path / "wrong"
        wrong_dir.mkdir()

        with pytest.raises(RuntimeError):
            validate_cwd(wrong_dir)  # We're not in wrong_dir

        # Test 3: Organism layer - would fail if rogue dirs exist
        # (We don't create them here to avoid cleanup complexity,
        # but the test_rogue_detection_to_enforcement_chain covers this)


class TestMigrationScriptDryRun:
    """
    Integration test: Migration script dry-run safety.

    Verifies the migration script's dry-run mode is truly safe.
    """

    def test_dry_run_preserves_all_state(self, tmp_path):
        """
        E2E: Dry run makes zero filesystem changes.
        """
        if not SPECS_DIR.exists():
            pytest.skip("SPECS_DIR does not exist")

        test_spec_dir = SPECS_DIR / "_dry_run_integration_test"
        rogue_beads = test_spec_dir / ".beads"
        test_file = rogue_beads / "test_data.json"

        try:
            # Create rogue directory with content
            test_spec_dir.mkdir(exist_ok=True)
            rogue_beads.mkdir(exist_ok=True)
            test_file.write_text('{"test": "data"}')

            # Record state before
            state_before = {
                "spec_exists": test_spec_dir.exists(),
                "beads_exists": rogue_beads.exists(),
                "file_exists": test_file.exists(),
                "file_content": test_file.read_text() if test_file.exists() else None,
            }

            # Run migration in dry-run mode (import the function)
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
            from migrate_beads import migrate_beads

            exit_code = migrate_beads(dry_run=True)

            # Record state after
            state_after = {
                "spec_exists": test_spec_dir.exists(),
                "beads_exists": rogue_beads.exists(),
                "file_exists": test_file.exists(),
                "file_content": test_file.read_text() if test_file.exists() else None,
            }

            # State should be identical
            assert state_before == state_after, (
                f"Dry run modified state!\nBefore: {state_before}\nAfter: {state_after}"
            )

        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()
            if rogue_beads.exists():
                rogue_beads.rmdir()
            if test_spec_dir.exists():
                test_spec_dir.rmdir()

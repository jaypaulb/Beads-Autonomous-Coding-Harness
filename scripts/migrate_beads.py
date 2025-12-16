#!/usr/bin/env python3
"""
Beads Migration Script
======================

Migrates spec-level .beads/ directories to the root-level database.
This enforces the single-database architecture for Phase 5.

Usage:
    python scripts/migrate_beads.py [--dry-run]

Options:
    --dry-run   Show what would be migrated without making changes
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from beads_config import BEADS_ROOT, SPECS_DIR
from progress import detect_rogue_beads_dirs


def run_bd_command(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    """
    Run a beads CLI command and return (success, output).

    Args:
        cmd: Command arguments (e.g., ["bd", "export"])
        cwd: Working directory for the command

    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out after 60 seconds"
    except Exception as e:
        return False, f"Command failed: {e}"


def export_issues_from_dir(beads_dir: Path, dry_run: bool = False) -> tuple[bool, str]:
    """
    Export issues from a .beads/ directory.

    Args:
        beads_dir: Path to the .beads/ directory
        dry_run: If True, don't actually export

    Returns:
        Tuple of (success: bool, export_file_path or error message)
    """
    parent_dir = beads_dir.parent
    export_file = parent_dir / "beads_export.json"

    if dry_run:
        return True, f"Would export to {export_file}"

    # bd export outputs to stdout, we need to capture and save
    success, output = run_bd_command(["bd", "export"], cwd=parent_dir)

    if success:
        # Write the export to a file
        export_file.write_text(output)
        return True, str(export_file)
    else:
        return False, f"Export failed: {output}"


def import_issues_to_root(export_file: Path, dry_run: bool = False) -> tuple[bool, str]:
    """
    Import issues from an export file to the root database.

    Args:
        export_file: Path to the exported JSON file
        dry_run: If True, don't actually import

    Returns:
        Tuple of (success: bool, message)
    """
    if dry_run:
        return True, f"Would import from {export_file}"

    if not export_file.exists():
        return False, f"Export file not found: {export_file}"

    # bd import reads from file
    success, output = run_bd_command(
        ["bd", "import", str(export_file)], cwd=BEADS_ROOT
    )

    return success, output


def delete_beads_dir(beads_dir: Path, dry_run: bool = False) -> tuple[bool, str]:
    """
    Delete a .beads/ directory after successful migration.

    Args:
        beads_dir: Path to the .beads/ directory to delete
        dry_run: If True, don't actually delete

    Returns:
        Tuple of (success: bool, message)
    """
    if dry_run:
        return True, f"Would delete {beads_dir}"

    try:
        shutil.rmtree(beads_dir)
        return True, f"Deleted {beads_dir}"
    except Exception as e:
        return False, f"Failed to delete {beads_dir}: {e}"


def migrate_beads(dry_run: bool = False) -> int:
    """
    Main migration function.

    Args:
        dry_run: If True, show what would happen without making changes

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("=" * 60)
    print("Beads Migration Script")
    print("=" * 60)

    if dry_run:
        print("\n[DRY RUN MODE - No changes will be made]\n")

    # Detect rogue directories
    rogue_dirs = detect_rogue_beads_dirs()

    if not rogue_dirs:
        print("\nNo spec-level .beads/ directories found.")
        print("Architecture is already correct - nothing to migrate.")
        return 0

    print(f"\nFound {len(rogue_dirs)} spec-level .beads/ directories to migrate:\n")
    for d in rogue_dirs:
        print(f"  - {d}")

    # Verify root database exists
    root_beads = BEADS_ROOT / ".beads"
    if not root_beads.exists():
        print(f"\nError: Root .beads/ directory not found at {root_beads}")
        print("Please initialize beads at root level first: bd init")
        return 1

    print(f"\nMigrating to root database at: {root_beads}\n")

    # Process each rogue directory
    success_count = 0
    fail_count = 0

    for beads_dir in rogue_dirs:
        print(f"\nProcessing: {beads_dir}")
        print("-" * 40)

        # Step 1: Export
        print("  [1/3] Exporting issues...")
        success, result = export_issues_from_dir(beads_dir, dry_run)
        if not success:
            print(f"  ERROR: {result}")
            fail_count += 1
            continue
        print(f"  OK: {result}")
        export_file = Path(result) if not dry_run else None

        # Step 2: Import to root
        if not dry_run and export_file:
            print("  [2/3] Importing to root database...")
            success, result = import_issues_to_root(export_file, dry_run)
            if not success:
                print(f"  ERROR: {result}")
                fail_count += 1
                continue
            print(f"  OK: {result}")

            # Clean up export file
            export_file.unlink()
        else:
            print("  [2/3] Would import to root database...")

        # Step 3: Delete old directory
        print("  [3/3] Removing old .beads/ directory...")
        success, result = delete_beads_dir(beads_dir, dry_run)
        if not success:
            print(f"  ERROR: {result}")
            fail_count += 1
            continue
        print(f"  OK: {result}")

        success_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"  Successfully migrated: {success_count}")
    print(f"  Failed: {fail_count}")

    if dry_run:
        print("\n[DRY RUN - No actual changes were made]")
        print("Run without --dry-run to perform migration.")

    return 0 if fail_count == 0 else 1


def main():
    parser = argparse.ArgumentParser(
        description="Migrate spec-level .beads/ directories to root database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )
    args = parser.parse_args()

    sys.exit(migrate_beads(dry_run=args.dry_run))


if __name__ == "__main__":
    main()

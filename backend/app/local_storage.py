"""Stable, update-safe local storage paths for ProTreBot.

Windows releases are commonly extracted into a new folder for every update.
Runtime identity, encrypted credentials and Demo state therefore live under
the current Windows user's LocalAppData directory instead of the release
folder.  Non-Windows development keeps the historical project-local path so
tests remain isolated and portable.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path


PROJECT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
APP_DIRECTORY_NAME = "ProTreBotEliteX"


def resolve_data_dir(
    platform_name: str,
    environ: Mapping[str, str],
    home: Path,
    project_data_dir: Path = PROJECT_DATA_DIR,
) -> Path:
    """Return an explicit override, stable Windows path, or test-safe fallback."""
    override = str(environ.get("PROTREBOT_DATA_DIR") or "").strip()
    if override:
        return Path(override).expanduser()
    if platform_name == "nt":
        local_root = str(environ.get("LOCALAPPDATA") or "").strip()
        base = Path(local_root) if local_root else home / "AppData" / "Local"
        return base / APP_DIRECTORY_NAME / "data"
    return project_data_dir


DATA_DIR = resolve_data_dir(os.name, os.environ, Path.home())


def migrate_legacy_files(
    names: Sequence[str],
    *,
    source_dir: Path = PROJECT_DATA_DIR,
    destination_dir: Path = DATA_DIR,
) -> tuple[str, ...]:
    """Copy legacy runtime files once without ever replacing newer data."""
    if source_dir.resolve() == destination_dir.resolve():
        return ()
    migrated: list[str] = []
    for name in names:
        source = source_dir / name
        destination = destination_dir / name
        if destination.exists() or not source.is_file():
            continue
        try:
            destination_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            migrated.append(name)
        except OSError:
            # Startup must remain available; the old path is left untouched.
            continue
    return tuple(migrated)

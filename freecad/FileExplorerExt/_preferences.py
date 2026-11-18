# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Preferences.
"""

from __future__ import annotations

from pathlib import Path

import FreeCAD as App  # type: ignore


RECENT_FILES = "User parameter:BaseApp/Preferences/RecentFiles"


def _read_recent() -> list[str]:
    group = App.ParamGet(RECENT_FILES)
    return [file for name in group.GetStrings("MRU") if (file := group.GetString(name, ""))]


def _write_recent(files: list[str]) -> None:
    group = App.ParamGet(RECENT_FILES)
    for name in group.GetStrings("MRU"):
        group.RemString(name)
    for i, file in enumerate(files):
        group.SetString(f"MRU{i}", file)


def add_recent_file(path: str) -> None:
    mod_recent_file(path)


def remove_recent_file(path: str) -> None:
    mod_recent_file(path, remove=True)


def mod_recent_file(path: str, *, remove: bool = False) -> None:
    files = [f for f in _read_recent() if f != path]
    if not remove:
        files.insert(0, path)
    _write_recent(files)


def remove_recent_subtree(path: str) -> None:
    """Remove a path and everything below it (deleted/trashed directory)."""
    target = Path(path)
    _write_recent([f for f in _read_recent() if not _is_same_or_under(f, target)])


def rename_recent_path(old_path: str, new_path: str) -> None:
    """Follow a file or directory rename in the recent files list."""
    old = Path(old_path)
    new = Path(new_path)
    files: list[str] = []
    for file in _read_recent():
        if _is_same_or_under(file, old):
            with_relative = Path(file).relative_to(old)
            files.append(str(new / with_relative))
        else:
            files.append(file)
    _write_recent(files)


def _is_same_or_under(file: str, directory: Path) -> bool:
    candidate = Path(file)
    if candidate == directory:
        return True
    try:
        candidate.relative_to(directory)
    except ValueError:
        return False
    return True


def get_recent_files() -> list[str]:
    return _read_recent()


def get_recent_files_group():
    return App.ParamGet(RECENT_FILES)

# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: System trash support.
"""

from __future__ import annotations

from pathlib import Path

from ._qt import qtc


def trash_path(path: str | Path) -> tuple[bool, str | None]:
    """
    Move a path to the system trash.

    Returns (ok, location). `location` is the trash location when the binding
    reports it, otherwise None. Never deletes permanently.
    """
    move = getattr(qtc.QFile, "moveToTrash", None)
    if move is None:
        return False, None

    try:
        result = move(str(path))
    except Exception:
        return False, None

    if isinstance(result, tuple):
        ok, location = result
        return bool(ok), location or None
    return bool(result), None

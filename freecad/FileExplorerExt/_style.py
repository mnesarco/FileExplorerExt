# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Application style.
"""

from ._qt import qtg, qtw
from pathlib import Path

class Icons:
    standardIcon = qtw.QApplication.style().standardIcon
    fromTheme = qtg.QIcon.fromTheme
    pixmaps = qtw.QStyle.StandardPixmap

    @staticmethod
    def customIcon(name: str) -> qtg.QIcon:
        return qtg.QIcon(str(Path(__file__).parent / "resources" / "icons" / f"{name}.svg"))

    RootDir = customIcon("root")
    HomeDir = customIcon("home")
    FavoriteDir = customIcon("fav")
    DefaultDir = customIcon("default")
    SysOpen = customIcon("open")
    Import = customIcon("import")
    Copy = customIcon("copy")
    Duplicate = customIcon("duplicate")
    Macros = customIcon("macros")
    NavUp = customIcon("up")
    NavBack = customIcon("back")
    NavForward = customIcon("forward")
    Trash = customIcon("trash")
    Rename = customIcon("rename")

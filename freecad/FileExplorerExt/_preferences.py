# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Preferences.
"""

import FreeCAD as App  # type: ignore


RECENT_FILES = "User parameter:BaseApp/Preferences/RecentFiles"


def add_recent_file(path: str) -> None:
    group = App.ParamGet(RECENT_FILES)
    count = group.GetInt("RecentFiles", 0)
    files = [path]

    for i in range(count):
        if (file := group.GetString(f"MRU{i}", "")) and file != path:
            files.append(file)

    for i, name in enumerate(files):
        group.SetString(f"MRU{i}", name)

    group.SetInt("RecentFiles", len(files))

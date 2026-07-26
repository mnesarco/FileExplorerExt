# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Preferences.
"""

import FreeCAD as App  # type: ignore


RECENT_FILES = "User parameter:BaseApp/Preferences/RecentFiles"


def add_recent_file(path: str) -> None:
    mod_recent_file(path)


def remove_recent_file(path: str) -> None:
    mod_recent_file(path, remove=True)


def mod_recent_file(path: str, *, remove: bool = False) -> None:
    group = App.ParamGet(RECENT_FILES)
    names: list[str] = group.GetStrings("MRU")
    files = [] if remove else [path]
    for name in names:
        if (file := group.GetString(name, "")) and file != path:
            files.append(file)

    for i, name in enumerate(files):
        group.SetString(f"MRU{i}", name)

    for name in names[i+1:]:
        group.RemString(name)


def get_recent_files() -> list[str]:
    group = App.ParamGet(RECENT_FILES)
    return [group.GetString(n, "") for n in group.GetStrings("MRU")]


def get_recent_files_group():
    return App.ParamGet(RECENT_FILES)

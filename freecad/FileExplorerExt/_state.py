# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Persistent state.
"""

import json
from pathlib import Path

import FreeCAD as App

from ._files import duplicate_file, import_file, open_file
from ._history import History
from ._qt import qtc, qtg
from ._intl import tr


class State(qtc.QObject):
    """
    Main State Controller.
    """

    path_changed: qtc.Signal = qtc.Signal(str)
    favorite_selected: qtc.Signal = qtc.Signal(str)
    tree_root_changed: qtc.Signal = qtc.Signal(str)
    passive_tree_root_changed: qtc.Signal = qtc.Signal(str)

    _current_path: str
    _history: History

    def __init__(self, parent: qtc.QObject | None = None):
        super().__init__(parent)
        self._current_path = ""
        self._history = History()
        self.passive_tree_root_changed.connect(self.on_passive_tree_root_changed)

    def get_last_path(self) -> str:
        return self._current_path or str(Path.home())

    def open_with_sys_app(self, path: str) -> None:
        url = qtc.QUrl.fromLocalFile(path)
        qtg.QDesktopServices.openUrl(url)

    def import_file(self, path: str) -> None:
        try:
            import_file(path)
        except Exception:
            msg = tr("FileExplorerExt", "File {} could not be imported").format(path)
            App.Console.PrintUserWarning(f"{msg}\n")

    def open_file(self, path: str) -> None:
        try:
            open_file(path)
        except Exception:
            msg = tr("FileExplorerExt", "File {} could not be opened").format(path)
            App.Console.PrintUserWarning(f"{msg}\n")

    def duplicate_file(self, path: str) -> None:
        duplicate_file(path)

    def on_passive_tree_root_changed(self, path: str) -> None:
        self._history.add(path)

    def navigate_back(self) -> None:
        if back := self._history.go_back():
            self.favorite_selected.emit(back)

    def navigate_forward(self) -> None:
        if forward := self._history.go_forward():
            self.favorite_selected.emit(forward)

    def get_favorites(self) -> list[tuple[str, str]]:
        path = Path(App.getUserConfigDir()) / "file_explorer.json"
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}
        favorites = data.get("favorites", {})
        return list(favorites.items())

    def save_favorites(self, data: list[tuple[str, str]]) -> None:
        path = Path(App.getUserConfigDir()) / "file_explorer.json"
        if path.exists():
            s_data = json.loads(path.read_text())
        else:
            s_data = {}
        s_data["favorites"] = dict(data)
        path.write_text(json.dumps(s_data))

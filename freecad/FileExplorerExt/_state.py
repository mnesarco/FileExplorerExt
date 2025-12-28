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
    request_root_change: qtc.Signal = qtc.Signal(str)
    tree_root_changed: qtc.Signal = qtc.Signal(str)
    passive_tree_root_changed: qtc.Signal = qtc.Signal(str)

    _current_path: str
    _history: History
    _navigating: bool

    def __init__(self, parent: qtc.QObject | None = None):
        super().__init__(parent)
        config = self._get_config()
        self._current_path = config.get("default_path", str(Path.home()))
        self._history = History()
        self._navigating = False
        self.passive_tree_root_changed.connect(
            self.on_passive_tree_root_changed
        )

    def get_last_path(self) -> str:
        return self._current_path or str(Path.home())

    def open_with_sys_app(self, path: str) -> None:
        url = qtc.QUrl.fromLocalFile(path)
        qtg.QDesktopServices.openUrl(url)

    def set_default_dir(self, path: str) -> None:
        config = self._get_config()
        config["default_path"] = path
        self._save_config(config)

    def import_file(self, path: str) -> None:
        try:
            import_file(path)
        except Exception:
            msg = tr("FileExplorerExt", "File {} could not be imported").format(
                path
            )
            App.Console.PrintUserWarning(f"{msg}\n")

    def open_file(self, path: str) -> None:
        try:
            open_file(path)
        except Exception:
            msg = tr("FileExplorerExt", "File {} could not be opened").format(
                path
            )
            App.Console.PrintUserWarning(f"{msg}\n")

    def duplicate_file(self, path: str) -> None:
        duplicate_file(path)

    def on_passive_tree_root_changed(self, path: str) -> None:
        if not self._navigating:
            self._history.add(path)

    def _navigate(self, path: str) -> None:
        self._navigating = True
        self.request_root_change.emit(path)
        self._navigating = False

    def navigate_back(self) -> None:
        if back := self._history.go_back():
            self._navigate(back)

    def navigate_forward(self) -> None:
        if forward := self._history.go_forward():
            self._navigate(forward)

    def _get_config(self) -> dict[str, object]:
        path = Path(App.getUserConfigDir()) / "file_explorer.json"
        if path.exists():
            return json.loads(path.read_text())
        else:
            return {}

    def _save_config(self, data: dict[str, object]) -> None:
        path = Path(App.getUserConfigDir()) / "file_explorer.json"
        path.write_text(json.dumps(data))

    def get_favorites(self) -> list[tuple[str, str]]:
        data = self._get_config()
        favorites = data.get("favorites", {})
        return list(favorites.items())

    def save_favorites(self, data: list[tuple[str, str]]) -> None:
        s_data = self._get_config()
        s_data["favorites"] = dict(data)
        self._save_config(s_data)

    def get_dock_area(self) -> qtc.Qt.DockWidgetArea:
        config = self._get_config()
        area = config.get("dockArea", "LeftDockWidgetArea")
        return getattr(
            qtc.Qt.DockWidgetArea,
            area,
            qtc.Qt.DockWidgetArea.LeftDockWidgetArea,
        )

    def save_dock_area(self, area: qtc.Qt.DockWidgetArea) -> None:
        s_data = self._get_config()
        s_data["dockArea"] = area.name if area else "LeftDockWidgetArea"
        self._save_config(s_data)


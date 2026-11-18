# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Persistent state.
"""

from __future__ import annotations

import json
import os
from contextlib import suppress
from pathlib import Path

import FreeCAD as App  # type: ignore

from ._files import delete_path, import_file, open_file
from ._history import History
from ._intl import tr
from ._preferences import remove_recent_subtree
from ._qt import qtc, qtg, QtCompat
from ._trash import trash_path as _trash_path

CONFIG_FILE = "file_explorer.json"


def config_path() -> Path:
    return Path(App.getUserConfigDir()) / CONFIG_FILE


def get_config() -> dict[str, object]:
    """Read the config, returning an empty dict if it is missing or corrupt."""
    path = config_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        App.Console.PrintWarning(f"File Explorer: could not read config {path}, using defaults.\n")
        # Keep the unreadable file for the user instead of overwriting it later.
        with suppress(OSError):
            path.replace(path.with_name(f"{path.name}.bad"))
        return {}
    return data if isinstance(data, dict) else {}


def save_config(data: dict[str, object]) -> None:
    """Write the config atomically so a crash or a second instance cannot corrupt it."""
    path = config_path()
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as e:
        App.Console.PrintWarning(f"File Explorer: could not save config: {e}\n")
        with suppress(OSError):
            tmp.unlink()


def _valid_dir(value: object) -> str | None:
    if isinstance(value, str) and value and Path(value).is_dir():
        return value
    return None


class State(qtc.QObject):
    """
    Main State Controller.
    """

    path_changed: qtc.Signal = qtc.Signal(str)
    request_root_change: qtc.Signal = qtc.Signal(str)
    tree_root_changed: qtc.Signal = qtc.Signal(str)
    passive_tree_root_changed: qtc.Signal = qtc.Signal(str)
    preview_enabled_changed: qtc.Signal = qtc.Signal(bool)
    request_recent_files: qtc.Signal = qtc.Signal()
    recent_files_changed: qtc.Signal = qtc.Signal()
    request_show_tree: qtc.Signal = qtc.Signal()

    _current_path: str
    _history: History
    _navigating: bool

    def __init__(self, parent: qtc.QObject | None = None):
        super().__init__(parent)
        self._current_path = self._resolve_start_path()
        self._history = History()
        self._navigating = False
        self.passive_tree_root_changed.connect(self.on_passive_tree_root_changed)

    def _resolve_start_path(self) -> str:
        """last_path → default_path → home, always an existing directory."""
        config = get_config()
        for key in ("last_path", "default_path"):
            if path := _valid_dir(config.get(key)):
                return path
        return str(Path.home())

    def get_last_path(self) -> str:
        return self._current_path or str(Path.home())

    def open_with_sys_app(self, path: str) -> None:
        url = qtc.QUrl.fromLocalFile(path)
        qtg.QDesktopServices.openUrl(url)

    def set_default_dir(self, path: str) -> None:
        config = get_config()
        config["default_path"] = path
        save_config(config)

    def import_file(self, path: str) -> bool:
        try:
            import_file(path)
            if path.lower().endswith(".fcstd"):
                self.recent_files_changed.emit()
            return True
        except Exception as e:
            msg = tr("FileExplorerExt", "File {} could not be imported").format(path)
            App.Console.PrintUserWarning(f"{msg}: {e}\n")
            return False

    def open_file(self, path: str) -> bool:
        try:
            open_file(path)
            self.recent_files_changed.emit()
            return True
        except Exception as e:
            msg = tr("FileExplorerExt", "File {} could not be opened").format(path)
            App.Console.PrintUserWarning(f"{msg}: {e}\n")
            return False

    def delete_path(self, path: str) -> bool:
        try:
            delete_path(path)
        except OSError as e:
            msg = tr("FileExplorerExt", "Could not delete {}").format(path)
            App.Console.PrintUserWarning(f"{msg}: {e}\n")
            return False
        remove_recent_subtree(path)
        self.recent_files_changed.emit()
        return True

    def trash_path(self, path: str) -> bool:
        ok, location = _trash_path(path)
        if not ok:
            msg = tr("FileExplorerExt", "Could not move {} to Trash").format(path)
            App.Console.PrintUserWarning(f"{msg}\n")
            return False
        App.Console.PrintLog(f"Moved to Trash: {path} -> {location or '?'}\n")
        remove_recent_subtree(path)
        self.recent_files_changed.emit()
        return True

    def on_passive_tree_root_changed(self, path: str) -> None:
        self._current_path = path
        config = get_config()
        config["last_path"] = path
        save_config(config)
        if not self._navigating:
            self._history.add(path)
        with suppress(OSError):
            os.chdir(path)

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

    def get_favorites(self) -> list[tuple[str, str]]:
        data = get_config().get("favorites")
        result: list[tuple[str, str]] = []
        if isinstance(data, list):
            # Ordered list of {path, name}; duplicates are kept.
            for item in data:
                if isinstance(item, dict):
                    path = item.get("path")
                    name = item.get("name")
                    if isinstance(path, str) and path:
                        result.append(
                            (path, name if isinstance(name, str) and name else Path(path).name)
                        )
        elif isinstance(data, dict):
            # Legacy format: {path: name}
            for path, name in data.items():
                if isinstance(path, str) and path:
                    result.append(
                        (path, name if isinstance(name, str) and name else Path(path).name)
                    )
        return result

    def save_favorites(self, data: list[tuple[str, str | None]]) -> None:
        config = get_config()
        config["favorites"] = [
            {"path": path, "name": name or Path(path).name} for path, name in data if path
        ]
        save_config(config)

    def get_dock_area(self) -> QtCompat.DockWidgetArea:
        config = get_config()
        area = config.get("dockArea")
        if not isinstance(area, str):
            area = "LeftDockWidgetArea"
        return getattr(
            QtCompat.DockWidgetArea,
            area,
            QtCompat.DockWidgetArea.LeftDockWidgetArea,
        )

    def save_dock_area(self, area: QtCompat.DockWidgetArea) -> None:
        config = get_config()
        config["dockArea"] = QtCompat.dock_area_name(area)
        save_config(config)

    def get_dock_visible(self) -> bool:
        return bool(get_config().get("dock_visible", True))

    def save_dock_visible(self, visible: bool) -> None:
        config = get_config()
        config["dock_visible"] = visible
        save_config(config)

    def get_dock_width(self) -> int:
        width = get_config().get("dock_width")
        return width if isinstance(width, int) and width > 100 else 0

    def save_dock_width(self, width: int) -> None:
        config = get_config()
        config["dock_width"] = width
        save_config(config)

    def get_preview_enabled(self) -> bool:
        return bool(get_config().get("preview_enabled", True))

    def save_preview_enabled(self, enabled: bool) -> None:
        config = get_config()
        config["preview_enabled"] = enabled
        save_config(config)

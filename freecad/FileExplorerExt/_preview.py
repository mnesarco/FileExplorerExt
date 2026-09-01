# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Preview Widget
"""

from __future__ import annotations

import contextlib
import hashlib
import zipfile
from pathlib import Path

import FreeCAD as App

from ._files import is_fcstd_file, is_image_file, open_file, is_fclist_file
from ._intl import tr
from ._preferences import remove_recent_file
from ._qt import QtCompat, qtc, qtg, qtw
from ._state import State
from ._style import Icons


class PreviewPanel(qtw.QLabel):
    """
    Preview Widget.
    """

    _state: State
    _enabled: bool = True
    _last_path: str = ""

    def __init__(self, state: State, parent: qtw.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FileExplorerExt_Preview")
        self._state = state
        self._enabled = state.get_preview_enabled()
        self.init_ui()
        state.path_changed.connect(self.on_state_path_changed)
        state.passive_tree_root_changed.connect(self._on_root_changed)
        state.preview_enabled_changed.connect(self.set_enabled)

    def _on_root_changed(self, _path: str) -> None:
        self._last_path = ""
        self.setVisible(False)

    def on_state_path_changed(self, path: str) -> None:
        self._last_path = path
        self.update_preview(path)

    def init_ui(self) -> None:
        self.setAlignment(QtCompat.AlignmentFlag.AlignCenter)
        self.setVisible(False)
        self.setStyleSheet("QLabel { background-color: white; }")

    def update_preview(self, file_path: str) -> None:
        self.setVisible(False)
        if not self._enabled:
            return

        info = qtc.QFileInfo(file_path)
        if not info.exists() or info.isDir():  # type: ignore
            return

        size = max(self.width() - 24, 150)

        if is_image_file(info.absoluteFilePath()):
            pixmap = qtg.QPixmap(info.absoluteFilePath())
            if not pixmap.isNull():
                self.show_image_preview(scaled_pixmap(pixmap, size, size))
                return

        if is_fcstd_file(info.absoluteFilePath()):
            size = max(self.width() - 24, 150)
            pixmap = get_fcstd_preview(
                info.absoluteFilePath(), width=size, height=size
            )
            if pixmap and not pixmap.isNull():
                self.show_image_preview(pixmap)
                return

    def show_image_preview(self, pixmap: qtg.QPixmap) -> None:
        """Display image preview."""
        self.setPixmap(pixmap)
        self.setVisible(True)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if enabled:
            self.update_preview(self._last_path)
        else:
            self.setVisible(False)


class FilePreviewCard(qtw.QToolButton):
    """
    File card with thumbnail.
    """

    path: Path

    def __init__(
        self,
        path: str = "",
        width: int = 150,
        height: int = 210,
        parent: qtw.QWidget | None = None,
    ):
        super().__init__(parent)

        self.setToolButtonStyle(
            QtCompat.ToolButtonStyle.ToolButtonTextUnderIcon
        )
        self.path = Path(path)
        self.setText(self.path.stem)
        self.setToolTip(path)

        if is_fcstd_file(path):
            pixmap = get_fcstd_preview(path)
            if pixmap and not pixmap.isNull():
                self.setIcon(qtg.QIcon(pixmap))
        elif is_fclist_file(path):
            self.setIcon(Icons.FCList)

        icon_size = int(width * 0.95)
        self.setIconSize(qtc.QSize(icon_size, icon_size))
        self.setFixedSize(width, height)

        self.setStyleSheet("""
            QToolButton {
                padding: 10px 6px;
                border: 0px;
            }
        """)

        self.clicked.connect(self.on_item_click)
        self.customContextMenuRequested.connect(self.on_context_menu)
        self.setContextMenuPolicy(QtCompat.ContextMenuPolicy.CustomContextMenu)

    def on_context_menu(self, position: qtc.QPoint) -> None:
        menu = qtw.QMenu(self)
        QtCompat.addAction(
            menu,
            Icons.Trash,
            tr("FileExplorerExt", "Remove from list"),
            lambda: remove_recent_file(str(self.path)),
        )
        QtCompat.exec_menu(menu, self.mapToGlobal(position))

    def on_item_click(self) -> None:
        if self.path.exists():
            open_file(str(self.path))


def get_cache_directory() -> Path:
    if hasattr(App, "getUserCachePath"):
        return Path(App.getUserCachePath())

    # Fallback
    user_dir = Path(App.getUserAppDataDir())
    cache_dir = user_dir / "Cache"

    if not cache_dir.exists():
        cache_dir.mkdir(parents=True)

    return cache_dir


def scaled_pixmap(pixmap: qtg.QPixmap, width: int, height: int) -> qtg.QPixmap:
    return pixmap.scaled(
        qtc.QSize(width, height),
        QtCompat.AspectRatioMode.KeepAspectRatio,
        QtCompat.TransformationMode.SmoothTransformation,
    )


def get_fcstd_preview(
    file_path: str | Path,
    width: int = 256,
    height: int = 256,
) -> qtg.QPixmap | None:
    """Load Thumbnail.png from a FreeCAD .FCStd file or cache if available."""
    if isinstance(file_path, str):
        if not file_path.strip():
            return None
        file_path = Path(file_path)

    if not file_path.exists() or not file_path.is_file():
        return None

    path_hash = hashlib.sha256(
        str(file_path.resolve()).encode("utf-8")
    ).hexdigest()
    cache = get_cache_directory() / f".{path_hash}.png"
    if cache.exists() and cache.stat().st_ctime > file_path.stat().st_ctime:
        return qtg.QPixmap(str(cache))

    try:
        with zipfile.ZipFile(str(file_path), "r") as zf:
            thumb_name = "thumbnails/Thumbnail.png"
            if thumb_name not in zf.namelist():
                return None
            data = zf.read(thumb_name)
            pixmap = qtg.QPixmap()
            if pixmap.loadFromData(data):
                pixmap = scaled_pixmap(pixmap, width, height)
                with contextlib.suppress(OSError, IOError):
                    pixmap.save(str(cache), "png")
                return pixmap
    except (zipfile.BadZipFile, OSError, IOError, KeyError):
        return None
    return None

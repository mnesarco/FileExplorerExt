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
from collections.abc import Callable
from pathlib import Path

import FreeCAD as App

from ._files import (
    is_fcstd_file,
    is_image_file,
    is_fclist_file,
    show_in_folder,
)
from ._intl import tr
from ._preferences import remove_recent_file
from ._qt import QtCompat, qtc, qtg, qtw
from ._state import State
from ._style import Icons

_CACHE_PRUNED = False


class PreviewPanel(qtw.QWidget):
    """
    Preview Widget.
    """

    _state: State
    _enabled: bool = True
    _last_path: str = ""
    _current_pixmap: qtg.QPixmap | None = None
    _lines: list[str]

    def __init__(self, state: State, parent: qtw.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FileExplorerExt_Preview")
        self._state = state
        self._enabled = state.get_preview_enabled()
        self._lines = []
        self.init_ui()
        state.path_changed.connect(self.on_state_path_changed)
        state.passive_tree_root_changed.connect(self._on_root_changed)
        state.preview_enabled_changed.connect(self.set_enabled)

    def _on_root_changed(self, _path: str) -> None:
        self._last_path = ""
        self.setVisible(False)

    def on_state_path_changed(self, path: str) -> None:
        self.update_preview(path)

    def init_ui(self) -> None:
        self.setMinimumHeight(120)
        self.setMaximumHeight(256)
        self.setSizePolicy(QtCompat.SizePolicy.Expanding, QtCompat.SizePolicy.Expanding)
        self.setVisible(False)

    def update_preview(self, file_path: str) -> None:
        self._last_path = file_path or ""
        self._current_pixmap = None
        self._lines = []
        self.setVisible(False)
        if not self._enabled or not file_path:
            return

        info = qtc.QFileInfo(file_path)
        if not info.exists() or info.isDir():  # type: ignore
            return

        size = qtc.QLocale().formattedDataSize(info.size())
        modified = info.lastModified().toString("yyyy-MM-dd HH:mm")
        self._lines = [info.fileName(), f"{size}  ·  {modified}"]
        self.setVisible(True)

        absolute_path = info.absoluteFilePath()
        if is_image_file(absolute_path):
            if pixmap := load_scaled_image(absolute_path):
                self._current_pixmap = pixmap
        elif is_fcstd_file(absolute_path):
            if pixmap := get_fcstd_preview(absolute_path):
                self._current_pixmap = pixmap
        self.update()

    def paintEvent(self, event: qtg.QPaintEvent) -> None:  # type: ignore[override]
        palette = self.palette()
        background = palette.color(QtCompat.PaletteColorRole.Base)
        foreground = palette.color(QtCompat.PaletteColorRole.Text)
        border = palette.color(QtCompat.PaletteColorRole.Mid)

        painter = qtg.QPainter(self)
        painter.fillRect(self.rect(), background)

        text_height = 38 if self._lines else 0
        image_area = self.rect().adjusted(0, 0, 0, -text_height)
        if self._current_pixmap is not None:
            scaled = self._current_pixmap.scaled(
                image_area.size(),
                QtCompat.AspectRatioMode.KeepAspectRatio,
                QtCompat.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(
                image_area.x() + (image_area.width() - scaled.width()) // 2,
                image_area.y() + (image_area.height() - scaled.height()) // 2,
                scaled,
            )

        if self._lines:
            painter.setPen(foreground)
            rect = self.rect().adjusted(4, self.height() - text_height + 2, -4, -2)
            metrics = painter.fontMetrics()
            line_height = metrics.height()
            for row, line in enumerate(self._lines[:2]):
                elided = metrics.elidedText(line, QtCompat.TextElideMode.ElideMiddle, rect.width())
                painter.drawText(
                    rect.x(),
                    rect.y() + row * line_height + metrics.ascent(),
                    elided,
                )

        painter.setPen(qtg.QPen(border))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.end()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if enabled:
            self.update_preview(self._last_path)
        else:
            self._current_pixmap = None
            self._lines = []
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
        on_remove: Callable[[], None] | None = None,
        on_open: Callable[[str], None] | None = None,
    ):
        super().__init__(parent)

        self.setToolButtonStyle(QtCompat.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.path = Path(path)
        self._on_remove = on_remove
        self._on_open = on_open
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
        if self.path.exists():
            QtCompat.addAction(
                menu,
                Icons.SysOpen,
                tr("FileExplorerExt", "Open"),
                self.on_item_click,
            )
            QtCompat.addAction(
                menu,
                Icons.SysOpen,
                tr("FileExplorerExt", "Show containing folder"),
                lambda: show_in_folder(str(self.path)),
            )
            menu.addSeparator()
        QtCompat.addAction(
            menu,
            Icons.Trash,
            tr("FileExplorerExt", "Remove from list"),
            self.remove_from_list,
        )
        QtCompat.exec_menu(menu, self.mapToGlobal(position))

    def remove_from_list(self) -> None:
        remove_recent_file(str(self.path))
        if self._on_remove:
            self._on_remove()

    def mark_missing(self) -> None:
        missing = tr("FileExplorerExt", "missing")
        self.setText(f"{self.path.stem} ({missing})")
        self.setToolTip(tr("FileExplorerExt", "Missing: {}").format(str(self.path)))

    def on_item_click(self) -> None:
        if self.path.exists() and self._on_open is not None:
            self._on_open(str(self.path))


def get_cache_directory() -> Path:
    if hasattr(App, "getUserCachePath"):
        cache = Path(App.getUserCachePath())
    else:
        cache = Path(App.getUserAppDataDir()) / "Cache"
    with contextlib.suppress(OSError):
        cache.mkdir(parents=True, exist_ok=True)

    global _CACHE_PRUNED
    if not _CACHE_PRUNED:
        _CACHE_PRUNED = True
        _prune_cache(cache)
    return cache


def _prune_cache(cache: Path, limit: int = 500) -> None:
    """Keep only the newest thumbnails: the cache would otherwise grow forever."""
    try:
        files = sorted(cache.glob(".*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return
    for stale in files[limit:]:
        with contextlib.suppress(OSError):
            stale.unlink()


def scaled_pixmap(pixmap: qtg.QPixmap, width: int, height: int) -> qtg.QPixmap:
    return pixmap.scaled(
        qtc.QSize(width, height),
        QtCompat.AspectRatioMode.KeepAspectRatio,
        QtCompat.TransformationMode.SmoothTransformation,
    )


def load_scaled_image(file_path: str, max_side: int = 512) -> qtg.QPixmap | None:
    """Read an image, downscaling large files while decoding."""
    reader = qtg.QImageReader(file_path)
    if not reader.canRead():
        return None
    size = reader.size()
    if size.isValid() and (size.width() > max_side or size.height() > max_side):
        reader.setScaledSize(
            size.scaled(max_side, max_side, QtCompat.AspectRatioMode.KeepAspectRatio)
        )
    image = reader.read()
    if image.isNull():
        return None
    return qtg.QPixmap.fromImage(image)


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

    path_hash = hashlib.sha256(str(file_path.resolve()).encode("utf-8")).hexdigest()
    cache = get_cache_directory() / f".{path_hash}.png"
    if cache.exists() and cache.stat().st_mtime > file_path.stat().st_mtime:
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

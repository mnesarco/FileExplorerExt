# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Preview Widget
"""

import zipfile

from ._files import is_fcstd_file, is_image_file
from ._qt import qtc, qtg, qtw
from ._state import State


class PreviewPanel(qtw.QLabel):
    """
    Preview Widget.
    """

    _state: State

    def __init__(self, state: State, parent: qtw.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FileExplorerExt_Preview")
        self._state = state
        self.init_ui()
        state.path_changed.connect(self.on_state_path_changed)
        state.passive_tree_root_changed.connect(lambda: self.setVisible(False))

    def on_state_path_changed(self, path: str) -> None:
        self.update_preview(path)

    def init_ui(self) -> None:
        self.setAlignment(qtc.Qt.AlignCenter)
        self.setVisible(False)
        self.setStyleSheet("QLabel { background-color: white; }")

    def update_preview(self, file_path: str) -> None:
        self.setVisible(False)

        info = qtc.QFileInfo(file_path)
        if not info.exists() or info.isDir():
            return

        if is_image_file(info.absoluteFilePath()):
            pixmap = qtg.QPixmap(info.absoluteFilePath())
            if not pixmap.isNull():
                self.show_image_preview(pixmap)
                return

        if is_fcstd_file(info.absoluteFilePath()):
            pixmap = self.get_fcstd_preview(info.absoluteFilePath())
            if pixmap and not pixmap.isNull():
                self.show_image_preview(pixmap)
                return

    def show_image_preview(self, pixmap: qtg.QPixmap) -> None:
        """Display image preview scaled to available width."""
        target_width = max(self.width() - 24, 150)
        scaled = pixmap.scaled(
            qtc.QSize(target_width, target_width),
            qtc.Qt.KeepAspectRatio,
            qtc.Qt.SmoothTransformation,
        )
        self.setPixmap(scaled)
        self.setVisible(True)

    def get_fcstd_preview(self, file_path: str) -> qtg.QPixmap | None:
        """Load Thumbnail.png from a FreeCAD .FCStd file if available."""
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                thumb_name = "thumbnails/Thumbnail.png"
                if thumb_name not in zf.namelist():
                    return None
                data = zf.read(thumb_name)
                pixmap = qtg.QPixmap()
                if pixmap.loadFromData(data):
                    return pixmap
        except (zipfile.BadZipFile, OSError, KeyError):
            return None
        return None

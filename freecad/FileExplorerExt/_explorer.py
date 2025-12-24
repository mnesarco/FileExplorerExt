# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz

"""
FileExplorerExt: Main Widget.
"""

from __future__ import annotations

from pathlib import Path

import FreeCADGui as Gui

from ._favorites import FavoritesWidget
from ._intl import tr
from ._preview import PreviewPanel
from ._qt import qtc, qtw
from ._state import State
from ._tree import FileTree
from ._style import Icons


class FileExplorerWidget(qtw.QWidget):
    """
    Advanced File Explorer Widget.
    """

    _state: State
    tree: FileTree
    preview: PreviewPanel
    favorites: FavoritesWidget
    status: qtw.QStatusBar

    def __init__(self, parent: qtw.QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = State()
        self.init_ui()

        self._state.passive_tree_root_changed.connect(
            lambda path: self.status.showMessage(self.tree.root())
        )

        # Restore last location if available
        last_location = self._state.get_last_path()
        if last_location and Path(last_location).is_dir():
            self._state.favorite_selected.emit(last_location)

    def build_sidebar(self) -> qtw.QWidget:
        container = qtw.QWidget()
        layout = qtw.QVBoxLayout(container)
        layout.addWidget(self.favorites)
        layout.addWidget(self.preview)
        layout.setContentsMargins(0, 0, 0, 0)
        return container

    def build_top_toolbar(self) -> qtw.QToolBar:
        toolbar = qtw.QToolBar(self)
        toolbar.setObjectName("FileExplorerExt_ToolBar")

        toolbar.addAction(
            Icons.NavBack,
            tr("FileExplorerExt", "Back"),
            self._state.navigate_back,
        )
        toolbar.addAction(
            Icons.NavForward,
            tr("FileExplorerExt", "Forward"),
            self._state.navigate_forward,
        )
        toolbar.addAction(
            Icons.NavUp,
            tr("FileExplorerExt", "Up"),
            self.tree.go_up,
        )

        filter_input = qtw.QLineEdit(self)
        filter_input.setPlaceholderText(tr("FileExplorerExt", "Filter..."))
        filter_input.textChanged.connect(self.on_filter_changed)
        toolbar.addSeparator()
        toolbar.addWidget(filter_input)
        return toolbar

    def init_ui(self) -> None:
        self.tree = FileTree(self._state, self)
        self.preview = PreviewPanel(self._state, self)
        self.favorites = FavoritesWidget(self._state, self)
        left_sidebar = self.build_sidebar()
        top_toolbar = self.build_top_toolbar()
        self.status = qtw.QStatusBar(self)

        splitter = qtw.QSplitter(qtc.Qt.Horizontal)
        splitter.addWidget(left_sidebar)
        splitter.addWidget(self.tree)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 8)

        layout = qtw.QVBoxLayout(self)
        layout.addWidget(top_toolbar, stretch=0)
        layout.addWidget(splitter, stretch=1)
        layout.addWidget(self.status, stretch=0)
        self.setLayout(layout)

    def on_filter_changed(self, text: str):
        self.tree.setNameFilter(text)


class FileExplorerDockWidget(qtw.QDockWidget):
    """
    Dockable container for File Explorer.
    """

    file_explorer: FileExplorerWidget

    def __init__(self, parent: qtw.QWidget | None = None) -> None:
        super().__init__(tr("FileExplorerExt", "File Explorer"), parent)
        self.file_explorer = FileExplorerWidget(self)
        self.setWidget(self.file_explorer)
        self.setObjectName("FileExplorerExt_Dock")


def show() -> None:
    window = Gui.getMainWindow()
    dock = FileExplorerDockWidget(window)
    window.__FileExplorerExt__ = dock
    window.addDockWidget(qtc.Qt.LeftDockWidgetArea, dock)

# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Main Widget.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import FreeCADGui as Gui  # type: ignore

from ._favorites import FavoritesWidget
from ._intl import tr
from ._preview import PreviewPanel
from ._qt import qtc, qtg, qtw, QtCompat
from ._state import State
from ._style import Icons
from ._tree import FileTree


class FileExplorerWidget(qtw.QWidget):
    """
    Advanced File Explorer Widget.
    """

    _state: State
    tree: FileTree
    preview: PreviewPanel
    favorites: FavoritesWidget
    status: qtw.QStatusBar
    read_only_toggle: qtw.QToolButton

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
            self._state.request_root_change.emit(last_location)

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

        QtCompat.addAction(
            toolbar,
            Icons.NavBack,
            tr("FileExplorerExt", "Back"),
            self._state.navigate_back,
        )
        QtCompat.addAction(
            toolbar,
            Icons.NavForward,
            tr("FileExplorerExt", "Forward"),
            self._state.navigate_forward,
        )
        QtCompat.addAction(
            toolbar,
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

    def build_statusbar(self) -> qtw.QStatusBar:
        status = qtw.QStatusBar(self)
        status.setSizeGripEnabled(False)
        read_only_toggle = qtw.QToolButton()
        read_only_toggle.setCheckable(True)
        read_only_toggle.setToolButtonStyle(
            QtCompat.ToolButtonStyle.ToolButtonTextOnly
        )
        read_only_toggle.setToolTip(tr("FileExplorerExt", "Read only"))
        read_only_toggle.toggled.connect(self.on_toggle_readonly)
        read_only_toggle.setFocusPolicy(QtCompat.FocusPolicy.NoFocus)
        status.addPermanentWidget(read_only_toggle)
        self.read_only_toggle = read_only_toggle
        read_only_toggle.toggle()
        return status

    def on_toggle_readonly(self, ro: bool) -> None:
        toggle = self.read_only_toggle
        toggle.setText(
            tr("FileExplorerExt", "ro") if ro else tr("FileExplorerExt", "rw")
        )
        toggle.setToolTip(
            tr("FileExplorerExt", "Read only")
            if ro
            else tr("FileExplorerExt", "Read/Write")
        )
        self.tree.setReadOnly(ro)

    def init_ui(self) -> None:
        self.tree = FileTree(self._state, self)
        self.preview = PreviewPanel(self._state, self)
        self.favorites = FavoritesWidget(self._state, self)
        left_sidebar = self.build_sidebar()
        top_toolbar = self.build_top_toolbar()
        self.status = self.build_statusbar()

        splitter = qtw.QSplitter(QtCompat.Orientation.Horizontal)
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

    def closeEvent(self, event: qtg.QCloseEvent) -> None:
        setattr(Gui, "__FileExplorerExt__", None)
        return super().closeEvent(event)

    def on_area_changed(self, area: QtCompat.DockWidgetArea) -> None:
        self.file_explorer._state.save_dock_area(area)

    def start(self) -> None:
        window = cast(qtw.QMainWindow, self.parent())
        setattr(Gui, "__FileExplorerExt__", self)
        area = self.file_explorer._state.get_dock_area()
        window.addDockWidget(area, self)
        self.setVisible(True)
        self.raise_()
        qtc.QTimer.singleShot(
            100, lambda: self.dockLocationChanged.connect(self.on_area_changed)
        )


def _instance() -> FileExplorerDockWidget | None:
    return getattr(Gui, "__FileExplorerExt__", None)


def show() -> None:
    if instance := _instance():
        instance.setVisible(True)
        instance.raise_()
    else:
        instance = FileExplorerDockWidget(Gui.getMainWindow())
        instance.start()


def hide() -> None:
    if instance := _instance():
        instance.setVisible(False)


def toggle() -> None:
    if (instance := _instance()) and instance.isVisible():
        hide()
    else:
        show()

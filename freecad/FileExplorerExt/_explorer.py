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
from ._recent import RecentFilesWidget


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
    content: qtw.QStackedWidget
    recent: RecentFilesWidget

    def __init__(self, parent: qtw.QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = State()
        self.init_ui()

        self._state.passive_tree_root_changed.connect(
            lambda _: self.show_tree(self.tree.root())
        )
        self._state.request_show_tree.connect(
            lambda: self.show_tree(self.tree.root())
        )
        self._state.request_recent_files.connect(self.show_recent)

        # Restore last location if available
        last_location = self._state.get_last_path()
        if last_location and Path(last_location).is_dir():
            self._state.request_root_change.emit(last_location)

    def show_tree(self, msg: str) -> None:
        self.status.showMessage(self.tree.root())
        self.content.setCurrentIndex(0)

    def show_recent(self) -> None:
        self.content.setCurrentIndex(1)

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
        size = int(toolbar.iconSize().width() * 0.7)
        toolbar.setIconSize(qtc.QSize(size, size))

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
        QtCompat.addAction(
            toolbar,
            Icons.Save,
            tr("FileExplorerExt", "Save here"),
            self.tree.save_here,
        )
        QtCompat.addAction(
            toolbar,
            Icons.NewFolder,
            tr("FileExplorerExt", "Create Folder"),
            self._create_folder,
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
        preview_toggle = qtw.QToolButton()
        preview_toggle.setCheckable(True)
        preview_toggle.setToolButtonStyle(
            QtCompat.ToolButtonStyle.ToolButtonIconOnly
        )
        preview_toggle.setFocusPolicy(QtCompat.FocusPolicy.NoFocus)
        preview_toggle.setIconSize(qtc.QSize(16, 16))
        preview_toggle.toggled.connect(self.on_toggle_preview)
        status.addPermanentWidget(preview_toggle)
        self.preview_toggle = preview_toggle
        preview_toggle.setChecked(self._state.get_preview_enabled())
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

    def on_toggle_preview(self, enabled: bool) -> None:
        toggle = self.preview_toggle
        toggle.setIcon(Icons.Preview if enabled else Icons.PreviewOff)
        toggle.setToolTip(
            tr("FileExplorerExt", "Preview enabled")
            if enabled
            else tr("FileExplorerExt", "Preview disabled")
        )
        self._state.save_preview_enabled(enabled)
        self._state.preview_enabled_changed.emit(enabled)

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
        self.content = qtw.QStackedWidget()
        self.recent = RecentFilesWidget(self._state, self)
        left_sidebar = self.build_sidebar()
        top_toolbar = self.build_top_toolbar()
        self.status = self.build_statusbar()

        self.content.addWidget(self.tree)
        self.content.addWidget(self.recent)
        self.content.setCurrentIndex(0)

        splitter = qtw.QSplitter(QtCompat.Orientation.Horizontal)
        splitter.addWidget(left_sidebar)
        splitter.addWidget(self.content)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 8)

        layout = qtw.QVBoxLayout(self)
        layout.addWidget(top_toolbar, stretch=0)
        layout.addWidget(splitter, stretch=1)
        layout.addWidget(self.status, stretch=0)
        self.setLayout(layout)

    def on_filter_changed(self, text: str):
        self.tree.setNameFilter(text)

    def _create_folder(self) -> None:
        parent = self.tree.root()
        name, ok = QtCompat.get_text(
            self,
            tr("FileExplorerExt", "Create Folder"),
            tr("FileExplorerExt", "Folder name in:") + f"\n{parent}",
        )
        name = name.strip()
        if not ok or not name:
            return
        if Path(name).name != name or "/" in name or "\\" in name or name in (".", ".."):
            QtCompat.message_box(
                self,
                tr("FileExplorerExt", "Create Folder"),
                tr("FileExplorerExt", "Enter a single folder name without path separators."),
            )
            return
        path = Path(parent) / name
        try:
            path.mkdir(exist_ok=False)
        except FileExistsError:
            QtCompat.message_box(
                self,
                tr("FileExplorerExt", "Create Folder"),
                tr("FileExplorerExt", "A file or folder with that name already exists."),
            )
        except OSError as e:
            QtCompat.message_box(
                self,
                tr("FileExplorerExt", "Create Folder"),
                str(e),
            )


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
        if area and area != QtCompat.DockWidgetArea.NoDockWidgetArea:
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

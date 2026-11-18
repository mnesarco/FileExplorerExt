# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Main Widget.
"""

from __future__ import annotations

from typing import cast

import FreeCAD as App  # type: ignore
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
    drag_lock_toggle: qtw.QToolButton
    preview_toggle: qtw.QToolButton
    filter_input: qtw.QLineEdit
    save_action: qtg.QAction
    content: qtw.QStackedWidget
    recent: RecentFilesWidget

    def __init__(self, parent: qtw.QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = State()
        self.init_ui()

        self._state.passive_tree_root_changed.connect(lambda _: self.show_tree())
        self._state.request_show_tree.connect(self.show_tree)
        self._state.request_recent_files.connect(self.show_recent)
        self._state.path_changed.connect(lambda _: self._update_save_tooltip())
        self.show_tree()

    def _update_save_tooltip(self) -> None:
        doc = App.ActiveDocument
        self.save_action.setToolTip(
            tr("FileExplorerExt", "Save '{}' in the current folder").format(doc.Name)
            if doc
            else tr("FileExplorerExt", "Save the active document in the current folder")
        )

    def show_tree(self) -> None:
        self.status.showMessage(self.tree.root())
        self.content.setCurrentIndex(0)

    def show_recent(self) -> None:
        self.content.setCurrentIndex(1)

    def build_sidebar(self) -> qtw.QWidget:
        container = qtw.QWidget()
        layout = qtw.QVBoxLayout(container)
        layout.addWidget(self.favorites, stretch=1)
        layout.addWidget(self.preview, stretch=0, alignment=QtCompat.AlignmentFlag.AlignBottom)
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
        save_action = QtCompat.addAction(
            toolbar,
            Icons.Save,
            tr("FileExplorerExt", "Save document here"),
            self.tree.save_here,
        )
        self.save_action = save_action
        self._update_save_tooltip()
        QtCompat.addAction(
            toolbar,
            Icons.SaveList,
            tr("FileExplorerExt", "Save all here"),
            self.tree.save_all_here,
        )
        QtCompat.addAction(
            toolbar,
            Icons.NewFolder,
            tr("FileExplorerExt", "Create Folder"),
            self.tree.create_folder,
        )

        filter_input = qtw.QLineEdit(self)
        filter_input.setPlaceholderText(tr("FileExplorerExt", "Filter..."))
        filter_input.setClearButtonEnabled(True)
        filter_input.textChanged.connect(self.on_filter_changed)
        self.filter_input = filter_input
        # Debounce: every text change re-walks all rows of the current folder.
        self._filter_timer = qtc.QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(120)
        self._filter_timer.timeout.connect(self._apply_filter)
        self.tree.set_filter_widget(filter_input)
        toolbar.addSeparator()
        toolbar.addWidget(filter_input)
        return toolbar

    def build_statusbar(self) -> qtw.QStatusBar:
        status = qtw.QStatusBar(self)
        status.setSizeGripEnabled(False)
        preview_toggle = qtw.QToolButton()
        preview_toggle.setCheckable(True)
        preview_toggle.setToolButtonStyle(QtCompat.ToolButtonStyle.ToolButtonIconOnly)
        preview_toggle.setFocusPolicy(QtCompat.FocusPolicy.NoFocus)
        preview_toggle.setIconSize(qtc.QSize(16, 16))
        preview_toggle.toggled.connect(self.on_toggle_preview)
        status.addPermanentWidget(preview_toggle)
        self.preview_toggle = preview_toggle
        preview_toggle.setChecked(self._state.get_preview_enabled())
        # setChecked() does not emit when the saved value is already True.
        self.on_toggle_preview(preview_toggle.isChecked())

        drag_lock_toggle = qtw.QToolButton()
        drag_lock_toggle.setCheckable(True)
        drag_lock_toggle.setToolButtonStyle(QtCompat.ToolButtonStyle.ToolButtonIconOnly)
        drag_lock_toggle.toggled.connect(self.on_toggle_drag_lock)
        drag_lock_toggle.setFocusPolicy(QtCompat.FocusPolicy.NoFocus)
        drag_lock_toggle.setIconSize(qtc.QSize(16, 16))
        status.addPermanentWidget(drag_lock_toggle)
        self.drag_lock_toggle = drag_lock_toggle
        drag_lock_toggle.setChecked(True)
        self.on_toggle_drag_lock(True)
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

    def on_toggle_drag_lock(self, locked: bool) -> None:
        toggle = self.drag_lock_toggle
        toggle.setIcon(Icons.Lock if locked else Icons.Unlock)
        toggle.setToolTip(
            tr(
                "FileExplorerExt",
                "Lock drag & drop — prevents moving files or folders by dropping "
                "them onto folders.",
            )
            if locked
            else tr("FileExplorerExt", "Drops move files.")
        )
        self.tree.setDragLocked(locked)

    def init_ui(self) -> None:
        self.tree = FileTree(self._state, self)
        self.preview = PreviewPanel(self._state, self)
        self.favorites = FavoritesWidget(self._state, self)
        self.tree.favorites = self.favorites
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

    def on_filter_changed(self, text: str) -> None:
        self._filter_timer.start()

    def _apply_filter(self) -> None:
        self.tree.setNameFilter(self.filter_input.text())


class FileExplorerDockWidget(qtw.QDockWidget):
    """
    Dockable container for File Explorer.
    """

    file_explorer: FileExplorerWidget

    def __init__(self, parent: qtw.QWidget | None = None) -> None:
        super().__init__(tr("FileExplorerExt", "File Explorer"), parent)
        # Created before the content widget: resizeEvent can fire while it is set.
        self._width_timer = qtc.QTimer(self)
        self._width_timer.setSingleShot(True)
        self._width_timer.timeout.connect(self._save_width)
        self.file_explorer = FileExplorerWidget(self)
        self.setWidget(self.file_explorer)
        self.setObjectName("FileExplorerExt_Dock")
        self.setAttribute(QtCompat.WidgetAttribute.WA_DeleteOnClose, False)

    def _save_width(self) -> None:
        if hasattr(self, "file_explorer"):
            self.file_explorer._state.save_dock_width(self.width())

    def _can_persist(self) -> bool:
        """Ignore visibility changes caused by FreeCAD shutting down or hiding."""
        window = self.parentWidget()
        return not qtc.QCoreApplication.closingDown() and window is not None and window.isVisible()

    def closeEvent(self, event: qtg.QCloseEvent) -> None:
        self._save_width()
        if self._can_persist():
            self.file_explorer._state.save_dock_visible(False)
        return super().closeEvent(event)

    def resizeEvent(self, event: qtg.QResizeEvent) -> None:
        if hasattr(self, "file_explorer"):
            self._width_timer.start(500)
        return super().resizeEvent(event)

    def on_area_changed(self, area: QtCompat.DockWidgetArea) -> None:
        self.file_explorer._state.save_dock_area(area)

    def on_visibility_changed(self, visible: bool) -> None:
        if self._can_persist():
            self.file_explorer._state.save_dock_visible(visible)

    def start(self) -> None:
        window = cast(qtw.QMainWindow, self.parent())
        setattr(Gui, "__FileExplorerExt__", self)

        area = self.file_explorer._state.get_dock_area()
        if area == QtCompat.DockWidgetArea.NoDockWidgetArea:
            area = QtCompat.DockWidgetArea.LeftDockWidgetArea
        window.addDockWidget(area, self)
        if width := self.file_explorer._state.get_dock_width():
            self.resize(width, self.height())
        # Connect after the initial layout settles so restoring the dock does
        # not overwrite the persisted visibility.
        qtc.QTimer.singleShot(100, self._connect_dock_signals)

    def _connect_dock_signals(self) -> None:
        self.dockLocationChanged.connect(self.on_area_changed)
        self.visibilityChanged.connect(self.on_visibility_changed)


def _instance() -> FileExplorerDockWidget | None:
    return getattr(Gui, "__FileExplorerExt__", None)


def _create() -> FileExplorerDockWidget:
    instance = FileExplorerDockWidget(Gui.getMainWindow())
    instance.start()
    return instance


def show_on_startup() -> None:
    """Show the dock only if it was visible when FreeCAD closed."""
    if _instance():
        return
    instance = _create()
    if instance.file_explorer._state.get_dock_visible():
        instance.setVisible(True)
        instance.raise_()
    else:
        instance.setVisible(False)


def show() -> None:
    if instance := _instance():
        instance.setVisible(True)
        instance.raise_()
        instance.file_explorer._state.save_dock_visible(True)
    else:
        instance = _create()
        instance.setVisible(True)
        instance.raise_()


def hide() -> None:
    if instance := _instance():
        instance.setVisible(False)
        instance.file_explorer._state.save_dock_visible(False)


def toggle() -> None:
    if (instance := _instance()) and instance.isVisible():
        hide()
    else:
        show()

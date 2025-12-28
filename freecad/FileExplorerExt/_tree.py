# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: File Tree.
"""

from pathlib import Path

import FreeCAD as App  # type: ignore

from ._files import get_import_module, is_fcstd_file
from ._intl import tr
from ._qt import qtc, qtg, qtw
from ._state import State
from ._style import Icons

Filter = qtc.QDir.Filter
QDir = qtc.QDir


class FileTree(qtw.QTreeView):
    """
    File Tree Widget.
    """

    def __init__(self, state: State, parent: qtw.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FileExplorerExt_Tree")

        model = qtw.QFileSystemModel(self)

        self._state = state
        self._model = model

        model.rootPathChanged.connect(state.passive_tree_root_changed)
        model.setFilter(Filter.AllDirs | Filter.NoDotAndDotDot | Filter.Files)
        model.setRootPath(state.get_last_path())
        model.setNameFilterDisables(False)

        self.setModel(model)
        self.setRootIndex(model.index(model.rootPath()))
        self.setDragEnabled(True)
        self.setDragDropMode(qtw.QAbstractItemView.DragDropMode.DragOnly)
        self.hideColumn(1)
        self.hideColumn(2)
        self.setColumnWidth(0, 300)
        self.setUniformRowHeights(True)
        self.setContextMenuPolicy(qtc.Qt.ContextMenuPolicy.CustomContextMenu)
        self.activated.connect(self.on_activated)
        self.clicked.connect(self.on_activated)
        self.doubleClicked.connect(self.on_double_click)
        self.customContextMenuRequested.connect(self.on_context_menu)
        self._state.request_root_change.connect(self.on_root_change_requested)

    def on_root_change_requested(self, path: str) -> None:
        rootIndex = self._model.setRootPath(path)
        self.setRootIndex(rootIndex)
        self._state.tree_root_changed.emit(path)

    def on_double_click(self, index: qtc.QModelIndex) -> None:
        if index.isValid():
            str_path = self._model.filePath(index)
            path = Path(str_path)
            if path.is_dir():
                rootIndex = self._model.setRootPath(str_path)
                self.setRootIndex(rootIndex)
                self._state.tree_root_changed.emit(str_path)
            elif is_fcstd_file(str_path) or get_import_module(str_path):
                self._state.open_file(str_path)
            else:
                self._state.open_with_sys_app(str_path)

    def on_activated(self, index: qtc.QModelIndex) -> None:
        if index.isValid():
            path = self._model.filePath(index)
            self._state.path_changed.emit(path)
        else:
            self._state.path_changed.emit(None)

    def on_context_menu(self, position: qtc.QPoint) -> None:
        index = self.indexAt(position)
        if not index.isValid():
            return

        file_path = self._model.filePath(index)
        is_fcstd = is_fcstd_file(file_path)
        is_dir = Path(file_path).is_dir()
        is_importable = not is_dir and get_import_module(file_path)
        doc = App.ActiveDocument

        menu = qtw.QMenu(self)

        if is_fcstd or is_importable:
            menu.addAction(
                Icons.SysOpen,
                tr("FileExplorerExt", "Open"),
                lambda: self._state.open_file(file_path),
            )

        if doc and is_importable and not is_fcstd:
            menu.addAction(
                Icons.Import,
                tr("FileExplorerExt", "Import into current document"),
                lambda: self._state.import_file(file_path),
            )

        if not is_dir and not is_fcstd:
            menu.addAction(
                Icons.SysOpen,
                tr("FileExplorerExt", "Open with Default App"),
                lambda: self._state.open_with_sys_app(file_path),
            )

        menu.addAction(
            Icons.Copy,
            tr("FileExplorerExt", "Copy Path"),
            lambda: self.copy_path_to_clipboard(file_path),
        )

        if is_dir:
            menu.addAction(
                Icons.SysOpen,
                tr("FileExplorerExt", "Browse"),
                lambda: self._state.open_with_sys_app(file_path),
            )
            menu.addAction(
                Icons.DefaultDir,
                tr("FileExplorerExt", "Set as default dir"),
                lambda: self._state.set_default_dir(file_path),
            )
        else:
            menu.addAction(
                Icons.Copy,
                tr("FileExplorerExt", "Duplicate"),
                lambda: self._state.duplicate_file(file_path),
            )

        menu.exec(self.mapToGlobal(position))  # type: ignore -> False positive

    def copy_path_to_clipboard(self, path: str) -> None:
        clipboard = qtg.QGuiApplication.clipboard()
        clipboard.setText(path)

    def go_up(self) -> None:
        path = Path(self._model.rootPath())
        if path.parent:
            rootIndex = self._model.setRootPath(str(path.parent))
            self.setRootIndex(rootIndex)
            self._state.tree_root_changed.emit(str(path.parent))

    def root(self) -> str:
        return self._model.rootPath()

    def setNameFilter(self, text: str) -> None:
        if text:
            if "*" in text:
                self._model.setNameFilters([text])
            else:
                self._model.setNameFilters([f"*{text}*"])
        else:
            self._model.setNameFilters([])

    def setReadOnly(self, ro: bool) -> None:
        self._model.setReadOnly(ro)
        self.setDragDropMode(
            qtw.QAbstractItemView.DragDropMode.DragOnly
            if ro
            else qtw.QAbstractItemView.DragDropMode.DragDrop
        )
        self.setDragEnabled(True)
        self.setDefaultDropAction(qtc.Qt.DropAction.MoveAction)
        self.setAcceptDrops(not ro)
        self.setDropIndicatorShown(not ro)

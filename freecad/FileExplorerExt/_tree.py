# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: File Tree.
"""

from __future__ import annotations

from pathlib import Path

import FreeCAD as App  # type: ignore

from ._files import get_import_module, is_fcstd_file
from ._intl import tr
from ._qt import qtc, qtg, qtw, QtCompat
from ._state import State
from ._style import Icons
from ._api import API
from ._preferences import add_recent_file


Filter = qtc.QDir.Filter
QDir = qtc.QDir


class ExcludingFilterProxy(qtc.QSortFilterProxyModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDynamicSortFilter(False)
        self.exclude_regex = qtc.QRegularExpression(r"^(?!.*\.fcbak$)", QtCompat.PatternOption.CaseInsensitiveOption)
        self.setFilterRegularExpression(self.exclude_regex)


class FileTree(qtw.QTreeView):
    """
    File Tree Widget.
    """

    def __init__(self, state: State, parent: qtw.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FileExplorerExt_Tree")

        model = qtw.QFileSystemModel(self)
        model.setFilter(Filter.AllDirs | Filter.NoDotAndDotDot | Filter.Files)
        model.setNameFilterDisables(False)
        QtCompat.set_file_system_options(model)

        proxy = ExcludingFilterProxy(self)
        proxy.setSourceModel(model)
        proxy.setFilterKeyColumn(0)

        self._state = state
        self._model = model
        self._proxy = proxy

        model.rootPathChanged.connect(state.passive_tree_root_changed)
        self.set_root_path(state.get_last_path())

        self.setModel(proxy)
        self.setRootIndex(self.root_index())
        self.setDragEnabled(True)
        self.setDragDropMode(QtCompat.DragDropMode.DragOnly)
        self.hideColumn(1)
        self.hideColumn(2)
        self.setColumnWidth(0, 300)
        self.setUniformRowHeights(True)
        self.setContextMenuPolicy(QtCompat.ContextMenuPolicy.CustomContextMenu)
        self.setSortingEnabled(True)
        self.activated.connect(self.on_activated)
        self.clicked.connect(self.on_activated)
        self.doubleClicked.connect(self.on_double_click)
        self.customContextMenuRequested.connect(self.on_context_menu)
        self._state.request_root_change.connect(self.on_root_change_requested)

    def set_root_path(self, path: str) -> qtc.QModelIndex:
        return self._proxy.mapFromSource(self._model.setRootPath(path))

    def root_index(self) -> qtc.QModelIndex:
        return self._proxy.mapFromSource(self._model.index(self._model.rootPath()))

    def file_path(self, index: qtc.QModelIndex) -> str:
        return self._model.filePath(self._proxy.mapToSource(index))

    def on_root_change_requested(self, path: str) -> None:
        rootIndex = self.set_root_path(path)
        self.setRootIndex(rootIndex)
        self._state.tree_root_changed.emit(path)

    def on_double_click(self, index: qtc.QModelIndex) -> None:
        if index.isValid():
            str_path = self.file_path(index)
            path = Path(str_path)
            if path.is_dir():
                rootIndex = self.set_root_path(str_path)
                self.setRootIndex(rootIndex)
                self._state.tree_root_changed.emit(str_path)
            elif is_fcstd_file(str_path) or get_import_module(str_path):
                self._state.open_file(str_path)
            else:
                self._state.open_with_sys_app(str_path)

    def on_activated(self, index: qtc.QModelIndex) -> None:
        if index.isValid():
            path = self.file_path(index)
            self._state.path_changed.emit(path)
        else:
            self._state.path_changed.emit(None)

    def on_context_menu(self, position: qtc.QPoint) -> None:
        index = self.indexAt(position)
        if not index.isValid():
            return

        file_path = self.file_path(index)
        is_fcstd = is_fcstd_file(file_path)
        is_dir = Path(file_path).is_dir()
        is_importable = not is_dir and get_import_module(file_path)
        doc = App.ActiveDocument

        menu = qtw.QMenu(self)

        if is_fcstd or is_importable:
            QtCompat.addAction(
                menu,
                Icons.SysOpen,
                tr("FileExplorerExt", "Open"),
                lambda: self._state.open_file(file_path),
            )

        if doc and is_importable and not is_fcstd:
            QtCompat.addAction(
                menu,
                Icons.Import,
                tr("FileExplorerExt", "Import into current document"),
                lambda: self._state.import_file(file_path),
            )

        if not is_dir and not is_fcstd:
            QtCompat.addAction(
                menu,
                Icons.SysOpen,
                tr("FileExplorerExt", "Open with Default App"),
                lambda: self._state.open_with_sys_app(file_path),
            )

        QtCompat.addAction(
            menu,
            Icons.Copy,
            tr("FileExplorerExt", "Copy Path"),
            lambda: self.copy_path_to_clipboard(file_path),
        )

        if is_dir:
            QtCompat.addAction(
                menu,
                Icons.SysOpen,
                tr("FileExplorerExt", "Browse"),
                lambda: self._state.open_with_sys_app(file_path),
            )
            QtCompat.addAction(
                menu,
                Icons.DefaultDir,
                tr("FileExplorerExt", "Set as default dir"),
                lambda: self._state.set_default_dir(file_path),
            )
        else:
            QtCompat.addAction(
                menu,
                Icons.Duplicate,
                tr("FileExplorerExt", "Duplicate"),
                lambda: self._state.duplicate_file(file_path),
            )

        paths = [Path(file_path)]
        custom_actions = API.get_custom_actions(paths)
        if custom_actions:
            for action in custom_actions:
                QtCompat.addAction(
                    menu,
                    action.icon if isinstance(action.icon, qtg.QIcon) else qtg.QIcon(action.icon), # type: ignore
                    action.text,
                    lambda act=action: act.activated(paths),
                )

        QtCompat.exec_menu(menu, self.mapToGlobal(position))

    def copy_path_to_clipboard(self, path: str) -> None:
        clipboard = qtg.QGuiApplication.clipboard()
        clipboard.setText(path)

    def go_up(self) -> None:
        path = Path(self._model.rootPath())
        if path.parent:
            rootIndex = self.set_root_path(str(path.parent))
            self.setRootIndex(rootIndex)
            self._state.tree_root_changed.emit(str(path.parent))

    def save_here(self) -> None:
        if doc := App.ActiveDocument:
            path = Path(self._model.rootPath())
            if not path.exists() or not path.is_dir():
                App.Console.PrintError("Invalid directory\n")
                return

            if file := doc.FileName:
                file = Path(file)
                if file.exists():
                    if path.samefile(file.parent):
                        doc.save()
                    else:
                        doc.saveAs(str(path / file.name))
                        App.Console.PrintNotification(f"Saved to {doc.FileName}. Old version left at {file!s}\n")
                    add_recent_file(str(path / file.name))
            else:
                new_name, ok = qtw.QInputDialog.getText(
                    self,
                    tr("FileExplorerExt", "Save as..."),
                    tr("FileExplorerExt", "Enter file name:"),
                    QtCompat.EchoMode.Normal,
                    f"{doc.Name}.FCStd",
                )
                if new_name and ok:
                    if not new_name.lower().endswith(".fcstd"):
                        new_name = f"{new_name}.FCStd"
                    dst = path / new_name
                    title = tr("FileExplorerExt", "Override confirmation:")
                    prompt = tr("FileExplorerExt", "File {} already exists. Override?").format(str(dst))
                    if dst.exists() and qtw.QMessageBox.question(self, title, prompt) != QtCompat.StandardButton.Yes:
                        return
                    doc.saveAs(str(path / new_name))
                    add_recent_file(str(path / new_name))


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
            QtCompat.DragDropMode.DragOnly
            if ro
            else QtCompat.DragDropMode.DragDrop
        )
        self.setDragEnabled(True)
        self.setDefaultDropAction(QtCompat.DropAction.MoveAction)
        self.setAcceptDrops(not ro)
        self.setDropIndicatorShown(not ro)

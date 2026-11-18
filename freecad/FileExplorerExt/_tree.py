# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: File Tree.
"""

from __future__ import annotations

import fnmatch
import shutil
from pathlib import Path
from typing import Callable, cast

import FreeCAD as App  # type: ignore

from ._api import API
from ._files import (
    duplicate_file,
    get_import_module,
    is_fcstd_file,
    open_terminal,
    path_touches_open_document,
    show_in_folder,
)
from ._intl import tr
from ._preferences import add_recent_file, rename_recent_path
from ._qt import qtc, qtg, qtw, QtCompat
from ._state import State
from ._style import Icons


Filter = qtc.QDir.Filter
QDir = qtc.QDir


class FileSystemModel(qtw.QFileSystemModel):
    """
    Writable file system model with rename validation.
    """

    rename_blocked: qtc.Signal = qtc.Signal(str)

    def setData(
        self, index: qtc.QModelIndex, value: object, role: int = QtCompat.ItemDataRole.EditRole
    ) -> bool:
        if role == QtCompat.ItemDataRole.EditRole:
            source = Path(self.filePath(index))
            new_name = str(value).strip()
            error = self._rename_error(source, new_name)
            if error:
                self.rename_blocked.emit(error)
                return False
            value = new_name
        return super().setData(index, value, role)

    def _rename_error(self, source: Path, new_name: str) -> str | None:
        if not new_name:
            return tr("FileExplorerExt", "The name cannot be empty.")
        if new_name in (".", "..") or "/" in new_name or "\\" in new_name:
            return tr("FileExplorerExt", "The name cannot contain path separators.")
        if path_touches_open_document(source):
            return tr(
                "FileExplorerExt",
                "'{}' belongs to an open document and cannot be renamed. Close it first.",
            ).format(source.name)
        target = source.with_name(new_name)
        if target.exists() and not _same_file(source, target):
            return tr(
                "FileExplorerExt",
                "A file or folder named '{}' already exists.",
            ).format(new_name)
        return None


def _same_file(left: Path, right: Path) -> bool:
    try:
        return left.samefile(right)
    except OSError:
        return False


def _is_inside(path: Path, folder: Path) -> bool:
    """True when path is folder or below it, following symlinks."""
    try:
        return path.resolve().is_relative_to(folder.resolve())
    except OSError:
        return False


class ExcludingFilterProxy(qtc.QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDynamicSortFilter(False)
        self.exclude_regex = qtc.QRegularExpression(
            r"^(?!.*\.(fcbak|fcstd1)$)",
            QtCompat.PatternOption.CaseInsensitiveOption,
        )
        self.setFilterRegularExpression(self.exclude_regex)
        self._name_filter = ""

    def set_name_filter(self, text: str) -> None:
        text = text.strip().lower()
        if text != self._name_filter:
            self._name_filter = text
            self.invalidateFilter()

    def filterAcceptsRow(self, row: int, parent: qtc.QModelIndex) -> bool:
        if not super().filterAcceptsRow(row, parent):
            return False
        if not self._name_filter:
            return True
        # Directories stay visible so filtered files can still be navigated.
        model = cast(qtw.QFileSystemModel, self.sourceModel())
        index = model.index(row, 0, parent)
        if model.isDir(index):
            return True
        name = str(index.data() or "").lower()
        if "*" in self._name_filter:
            return fnmatch.fnmatch(name, self._name_filter)
        return self._name_filter in name

    def lessThan(self, left_index, right_index):
        model = cast(qtw.QFileSystemModel, self.sourceModel())
        left_is_dir = model.isDir(left_index)
        right_is_dir = model.isDir(right_index)

        if left_is_dir != right_is_dir:
            return (
                left_is_dir
                if self.sortOrder() == QtCompat.SortOrder.AscendingOrder
                else right_is_dir
            )

        return super().lessThan(left_index, right_index)


class FileTree(qtw.QTreeView):
    """
    File Tree Widget.
    """

    favorites: object = None
    _clipboard: tuple[str, list[str]] | None = None

    def __init__(self, state: State, parent: qtw.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FileExplorerExt_Tree")

        model = FileSystemModel(self)
        model.setFilter(Filter.AllDirs | Filter.NoDotAndDotDot | Filter.Files)
        model.setNameFilterDisables(False)
        # The model is always writable; F2 is the only edit trigger.
        model.setReadOnly(False)
        QtCompat.set_file_system_options(model)
        model.rename_blocked.connect(self.on_rename_blocked)
        model.fileRenamed.connect(self.on_file_renamed)

        proxy = ExcludingFilterProxy(self)
        proxy.setSourceModel(model)
        proxy.setFilterKeyColumn(0)

        self._state = state
        self._model = model
        self._proxy = proxy
        self._filter_input: qtw.QLineEdit | None = None

        model.rootPathChanged.connect(state.passive_tree_root_changed)
        self.set_root_path(state.get_last_path())

        self.setModel(proxy)
        self.setRootIndex(self.root_index())
        self.setSelectionMode(QtCompat.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QtCompat.EditTrigger.EditKeyPressed)
        self.hideColumn(1)
        self.hideColumn(2)
        self.setColumnWidth(0, 300)
        self.setUniformRowHeights(True)
        self.setContextMenuPolicy(QtCompat.ContextMenuPolicy.CustomContextMenu)
        self.setSortingEnabled(True)
        self.sortByColumn(0, QtCompat.SortOrder.AscendingOrder)
        self.activated.connect(self.on_activated)
        self.doubleClicked.connect(self.open_index)
        self.customContextMenuRequested.connect(self.on_context_menu)
        self._state.request_root_change.connect(self.on_root_change_requested)
        self.selectionModel().currentChanged.connect(self.on_current_changed)
        self._install_shortcuts()
        # Locked by default; the lock is intentionally not persisted.
        self.setDragLocked(True)

    # --- Setup -------------------------------------------------------------

    def _install_shortcuts(self) -> None:
        self._shortcut("Return", self.open_current)
        self._shortcut("Enter", self.open_current)
        self._shortcut("Delete", self.trash_selection)
        self._shortcut("Backspace", self.go_up)
        self._shortcut("Ctrl+F", self.focus_filter)
        self._shortcut("Escape", self.clear_filter)
        self._shortcut("F5", self.refresh)
        self._shortcut("F2", self.rename_current)
        self._shortcut("Ctrl+C", self.copy_selection)
        self._shortcut("Ctrl+X", self.cut_selection)
        self._shortcut("Ctrl+V", self.paste)

    def _shortcut(self, key: str, call: Callable) -> qtg.QAction:
        action = qtg.QAction(self)
        action.setShortcut(qtg.QKeySequence(key))
        action.setShortcutContext(QtCompat.ShortcutContext.WidgetShortcut)
        action.triggered.connect(call)
        self.addAction(action)
        return action

    def set_filter_widget(self, widget: qtw.QLineEdit) -> None:
        self._filter_input = widget

    def setDragLocked(self, locked: bool) -> None:
        # Drag-out is independent of the drop lock: never disable dragging.
        self.setDragEnabled(True)
        self.setDragDropMode(
            QtCompat.DragDropMode.DragOnly if locked else QtCompat.DragDropMode.DragDrop
        )
        self.setAcceptDrops(not locked)
        self.setDropIndicatorShown(not locked)
        self.setDefaultDropAction(QtCompat.DropAction.MoveAction)

    # --- Navigation and selection -----------------------------------------

    def set_root_path(self, path: str) -> qtc.QModelIndex:
        return self._proxy.mapFromSource(self._model.setRootPath(path))

    def root_index(self) -> qtc.QModelIndex:
        return self._proxy.mapFromSource(self._model.index(self._model.rootPath()))

    def root(self) -> str:
        return self._model.rootPath()

    def file_path(self, index: qtc.QModelIndex) -> str:
        return self._model.filePath(self._proxy.mapToSource(index))

    def selected_paths(self) -> list[str]:
        rows = self.selectionModel().selectedRows(0)
        return list(dict.fromkeys(self.file_path(i) for i in rows if i.isValid()))

    def navigate_to(self, path: str) -> None:
        index = self.set_root_path(path)
        if not index.isValid():
            return
        self.setRootIndex(index)
        self._state.tree_root_changed.emit(path)

    def on_root_change_requested(self, path: str) -> None:
        self.navigate_to(path)

    def on_current_changed(self, current: qtc.QModelIndex, _previous: qtc.QModelIndex) -> None:
        path = self.file_path(current) if current.isValid() else None
        API.set_selected_path(path)
        self._state.path_changed.emit(path or "")

    def on_activated(self, index: qtc.QModelIndex) -> None:
        self._state.path_changed.emit(self.file_path(index) if index.isValid() else "")

    def open_current(self) -> None:
        self.open_index(self.currentIndex())

    def open_index(self, index: qtc.QModelIndex) -> None:
        if index.isValid():
            self.open_path(self.file_path(index))

    def open_path(self, str_path: str) -> None:
        path = Path(str_path)
        if path.is_dir():
            self.navigate_to(str_path)
        elif is_fcstd_file(str_path) or get_import_module(str_path):
            self._state.open_file(str_path)
        else:
            self._state.open_with_sys_app(str_path)

    def go_up(self) -> None:
        path = Path(self._model.rootPath())
        if path.parent and path.parent != path:
            self.navigate_to(str(path.parent))

    def refresh(self) -> None:
        self._proxy.invalidate()
        self.viewport().update()

    # --- Filter ------------------------------------------------------------

    def setNameFilter(self, text: str) -> None:
        self._proxy.set_name_filter(text)

    def focus_filter(self) -> None:
        if self._filter_input is not None:
            self._filter_input.setFocus()
            self._filter_input.selectAll()

    def clear_filter(self) -> None:
        if self._filter_input is not None:
            self._filter_input.clear()

    def set_show_hidden(self, hidden: bool) -> None:
        current = self._model.filter()
        if hidden:
            current |= Filter.Hidden
        else:
            current &= ~Filter.Hidden
        self._model.setFilter(current)
        self.refresh()

    # --- Context menu ------------------------------------------------------

    def on_context_menu(self, position: qtc.QPoint) -> None:
        index = self.indexAt(position)
        if not index.isValid():
            self.selectionModel().clearSelection()
            self._show_blank_menu(position)
            return

        if not self.selectionModel().isSelected(index):
            self.selectionModel().select(
                index,
                QtCompat.SelectionFlag.ClearAndSelect | QtCompat.SelectionFlag.Rows,
            )
        if index != self.currentIndex():
            self.selectionModel().setCurrentIndex(index, QtCompat.SelectionFlag.NoUpdate)

        self._show_item_menu(position, self.selected_paths())

    def _show_item_menu(self, position: qtc.QPoint, paths: list[str]) -> None:
        if not paths:
            return

        single = len(paths) == 1
        path = paths[0] if single else ""
        is_dir = single and Path(path).is_dir()
        is_fcstd = single and is_fcstd_file(path)
        is_importable = single and not is_dir and get_import_module(path)
        files = [p for p in paths if Path(p).is_file()]
        dirs = [p for p in paths if Path(p).is_dir()]
        insertable = [p for p in files if get_import_module(p) and not is_fcstd_file(p)]
        doc = App.ActiveDocument
        menu = qtw.QMenu(self)

        def add(icon, text, call, enabled=True, checkable=False) -> qtg.QAction:
            action = QtCompat.addAction(menu, icon, text, call)
            action.setEnabled(enabled)
            if checkable:
                action.setCheckable(True)
            return action

        # Open / FreeCAD group
        if single and not is_dir and (is_fcstd or is_importable):
            add(Icons.SysOpen, tr("FileExplorerExt", "Open"), self.open_current)
        if insertable:
            add(
                Icons.Import,
                tr("FileExplorerExt", "Import into current document"),
                lambda: self.insert_files(insertable),
                enabled=doc is not None,
            )
        if single and not is_dir and not is_fcstd:
            add(
                Icons.SysOpen,
                tr("FileExplorerExt", "Open with Default App"),
                lambda: self._state.open_with_sys_app(path),
            )
        if single:
            add(
                Icons.SysOpen,
                tr("FileExplorerExt", "Show containing folder"),
                lambda: self.show_containing(path),
            )
        if is_dir:
            add(
                Icons.SysOpen,
                tr("FileExplorerExt", "Browse"),
                lambda: self._state.open_with_sys_app(path),
            )
            if self.favorites is not None:
                add(
                    Icons.FavoriteDir,
                    tr("FileExplorerExt", "Add to Favorites"),
                    lambda: self.favorites.add_path(path),  # type: ignore[attr-defined]
                )
        add(
            Icons.Copy,
            tr("FileExplorerExt", "Copy Path"),
            lambda: self.copy_path_to_clipboard(paths),
        )
        add(
            Icons.Duplicate,
            tr("FileExplorerExt", "Duplicate"),
            lambda: self.duplicate_files(files),
            enabled=bool(files) and not dirs,
        )

        menu.addSeparator()

        add(
            Icons.Rename,
            tr("FileExplorerExt", "Rename (F2)"),
            self.rename_current,
            enabled=single,
        )
        if single and is_dir:
            add(
                Icons.DefaultDir,
                tr("FileExplorerExt", "Set as startup folder"),
                lambda: self._state.set_default_dir(path),
            )
            add(
                Icons.NavForward,
                tr("FileExplorerExt", "Open Terminal Here"),
                lambda: self.open_terminal_here(path),
            )

        custom_actions = API.get_custom_actions([Path(p) for p in paths])
        if custom_actions:
            menu.addSeparator()
            for action in custom_actions:
                icon = (
                    action.icon if isinstance(action.icon, qtg.QIcon) else qtg.QIcon(action.icon)  # type: ignore[arg-type]
                )
                paths_obj = [Path(p) for p in paths]
                add(
                    icon,
                    action.text,
                    lambda act=action, p=paths_obj: act.activated(p),
                )

        menu.addSeparator()

        add(
            Icons.Trash,
            tr("FileExplorerExt", "Move to Trash"),
            lambda: self.confirm_trash(paths),
        )
        add(
            Icons.Delete,
            tr("FileExplorerExt", "Delete Permanently"),
            lambda: self.confirm_delete(paths),
        )

        QtCompat.exec_menu(menu, self.mapToGlobal(position))

    def _show_blank_menu(self, position: qtc.QPoint) -> None:
        menu = qtw.QMenu(self)

        def add(icon, text, call, enabled=True, checkable=False) -> qtg.QAction:
            action = QtCompat.addAction(menu, icon, text, call)
            action.setEnabled(enabled)
            if checkable:
                action.setCheckable(True)
            return action

        add(
            Icons.NewFolder,
            tr("FileExplorerExt", "New Folder"),
            self.create_folder,
        )
        add(Icons.Refresh, tr("FileExplorerExt", "Refresh"), self.refresh)
        add(
            Icons.Copy,
            tr("FileExplorerExt", "Paste"),
            self.paste,
            enabled=self._clipboard is not None,
        )
        add(
            Icons.SysOpen,
            tr("FileExplorerExt", "Open Terminal Here"),
            lambda: self.open_terminal_here(self.root()),
        )
        if self.favorites is not None:
            add(
                Icons.FavoriteDir,
                tr("FileExplorerExt", "Add Current Folder to Favorites"),
                lambda: self.favorites.add_path(self.root()),  # type: ignore[attr-defined]
            )
        hidden = add(
            Icons.PreviewOff,
            tr("FileExplorerExt", "Show hidden files"),
            lambda: self.set_show_hidden(hidden.isChecked()),
            checkable=True,
        )
        hidden.setChecked(bool(self._model.filter() & Filter.Hidden))

        QtCompat.exec_menu(menu, self.mapToGlobal(position))

    # --- Actions -----------------------------------------------------------

    def copy_path_to_clipboard(self, paths: list[str] | str) -> None:
        text = paths if isinstance(paths, str) else "\n".join(paths)
        qtg.QGuiApplication.clipboard().setText(text)

    def rename_current(self) -> None:
        index = self.currentIndex()
        if index.isValid() and len(self.selected_paths()) <= 1:
            self.edit(index)

    def on_rename_blocked(self, message: str) -> None:
        qtw.QMessageBox.warning(self, tr("FileExplorerExt", "Rename"), message)

    def on_file_renamed(self, directory: str, old_name: str, new_name: str) -> None:
        rename_recent_path(str(Path(directory) / old_name), str(Path(directory) / new_name))
        self._state.recent_files_changed.emit()

    def create_folder(self) -> None:
        parent = self.root()
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
        try:
            (Path(parent) / name).mkdir(exist_ok=False)
        except FileExistsError:
            QtCompat.message_box(
                self,
                tr("FileExplorerExt", "Create Folder"),
                tr("FileExplorerExt", "A file or folder with that name already exists."),
            )
        except OSError as e:
            QtCompat.message_box(self, tr("FileExplorerExt", "Create Folder"), str(e))
        self.refresh()

    def _blocked_by_open_documents(self, paths: list[str]) -> set[str]:
        """Paths belonging to (or containing) an open document, with one warning."""
        blocked = {path for path in paths if path_touches_open_document(path)}
        if blocked:
            qtw.QMessageBox.warning(
                self,
                tr("FileExplorerExt", "Protected"),
                tr(
                    "FileExplorerExt",
                    "These items belong to open documents. Close the documents first:\n\n{}",
                ).format("\n".join(Path(path).name for path in sorted(blocked))),
            )
        return blocked

    def trash_selection(self) -> None:
        if paths := self.selected_paths():
            self.confirm_trash(paths)

    def confirm_trash(self, paths: list[str]) -> None:
        blocked = self._blocked_by_open_documents(paths)
        paths = [p for p in paths if p not in blocked]
        if not paths:
            return

        if len(paths) > 1:
            prompt = tr("FileExplorerExt", "Move {} items to Trash?").format(len(paths))
        elif Path(paths[0]).is_dir():
            prompt = tr(
                "FileExplorerExt",
                "Move directory '{}' and all its contents to Trash?",
            ).format(Path(paths[0]).name)
        else:
            prompt = tr("FileExplorerExt", "Move '{}' to Trash?").format(Path(paths[0]).name)

        if (
            qtw.QMessageBox.warning(
                self,
                tr("FileExplorerExt", "Move to Trash"),
                prompt,
                QtCompat.StandardButton.Yes | QtCompat.StandardButton.No,
                QtCompat.StandardButton.No,
            )
            != QtCompat.StandardButton.Yes
        ):
            return

        failures = [p for p in paths if not self._state.trash_path(p)]
        self.refresh()
        if failures:
            self._offer_permanent_delete(failures)

    def _offer_permanent_delete(self, paths: list[str]) -> None:
        listing = "\n".join(paths[:10])
        prompt = tr(
            "FileExplorerExt",
            "Could not move to Trash:\n\n{}\n\nDelete permanently instead? This cannot be undone.",
        ).format(listing)
        if (
            qtw.QMessageBox.warning(
                self,
                tr("FileExplorerExt", "Delete Permanently"),
                prompt,
                QtCompat.StandardButton.Yes | QtCompat.StandardButton.No,
                QtCompat.StandardButton.No,
            )
            == QtCompat.StandardButton.Yes
        ):
            self.confirm_delete(paths)

    def confirm_delete(self, paths: list[str]) -> None:
        blocked = self._blocked_by_open_documents(paths)
        paths = [p for p in paths if p not in blocked]
        if not paths:
            return

        if len(paths) > 1:
            prompt = tr(
                "FileExplorerExt",
                "PERMANENTLY DELETE {} items and ALL their contents?\n\nThis cannot be undone!",
            ).format(len(paths))
        elif Path(paths[0]).is_dir():
            prompt = tr(
                "FileExplorerExt",
                "PERMANENTLY DELETE directory '{}' and ALL its contents?\n\nThis cannot be undone!",
            ).format(Path(paths[0]).name)
        else:
            prompt = tr(
                "FileExplorerExt",
                "PERMANENTLY DELETE file '{}'?\n\nThis cannot be undone!",
            ).format(Path(paths[0]).name)

        if (
            qtw.QMessageBox.warning(
                self,
                tr("FileExplorerExt", "Confirm Delete"),
                prompt,
                QtCompat.StandardButton.Yes | QtCompat.StandardButton.No,
                QtCompat.StandardButton.No,
            )
            != QtCompat.StandardButton.Yes
        ):
            return

        failures = [p for p in paths if not self._state.delete_path(p)]
        self.refresh()
        if failures:
            qtw.QMessageBox.warning(
                self,
                tr("FileExplorerExt", "Delete Permanently"),
                tr("FileExplorerExt", "Some items could not be deleted:\n\n{}").format(
                    "\n".join(failures[:10])
                ),
            )

    def duplicate_files(self, files: list[str]) -> None:
        for file in files:
            try:
                duplicate_file(file)
            except OSError as e:
                App.Console.PrintUserWarning(f"Could not duplicate {file}: {e}\n")
        self.refresh()

    def insert_files(self, paths: list[str]) -> None:
        if not App.ActiveDocument:
            QtCompat.message_box(
                self,
                tr("FileExplorerExt", "Insert"),
                tr("FileExplorerExt", "There is no active document."),
            )
            return
        failures = [p for p in paths if not self._state.import_file(p)]
        self.refresh()
        if failures:
            qtw.QMessageBox.warning(
                self,
                tr("FileExplorerExt", "Insert"),
                tr("FileExplorerExt", "Some files could not be inserted:\n\n{}").format(
                    "\n".join(failures[:10])
                ),
            )

    def show_containing(self, path: str) -> None:
        try:
            show_in_folder(path)
        except OSError as e:
            QtCompat.message_box(self, tr("FileExplorerExt", "Show containing folder"), str(e))

    def open_terminal_here(self, path: str) -> None:
        try:
            open_terminal(path)
        except OSError as e:
            QtCompat.message_box(self, tr("FileExplorerExt", "Open Terminal Here"), str(e))

    # --- Clipboard ---------------------------------------------------------

    def copy_selection(self) -> None:
        if paths := self.selected_paths():
            self._clipboard = ("copy", paths)

    def cut_selection(self) -> None:
        if paths := self.selected_paths():
            self._clipboard = ("cut", paths)

    def paste(self) -> None:
        if not self._clipboard:
            return
        operation, sources = self._clipboard
        root = Path(self.root())
        errors: list[str] = []
        not_found = tr("FileExplorerExt", "not found")

        for source in map(Path, sources):
            destination = root / source.name
            if not source.exists() and not source.is_symlink():
                errors.append(f"{source.name}: {not_found}")
                continue
            if source.is_dir() and not source.is_symlink() and _is_inside(root, source):
                errors.append(
                    f"{source.name}: " + tr("FileExplorerExt", "Cannot paste a folder into itself")
                )
                continue
            if destination.exists() or destination.is_symlink():
                if _same_file(source, destination):
                    continue
                if not self._confirm_overwrite(destination):
                    continue
                # Prefer the trash, like every other destructive action here.
                if not self._state.trash_path(str(destination)) and not self._state.delete_path(
                    str(destination)
                ):
                    continue
            try:
                if operation == "cut":
                    shutil.move(str(source), str(destination))
                    rename_recent_path(str(source), str(destination))
                elif source.is_dir() and not source.is_symlink():
                    shutil.copytree(str(source), str(destination))
                else:
                    shutil.copy2(str(source), str(destination))
            except OSError as e:
                errors.append(f"{source.name}: {e}")

        if operation == "cut":
            self._clipboard = None
        self.refresh()
        self._state.recent_files_changed.emit()
        if errors:
            qtw.QMessageBox.warning(
                self,
                tr("FileExplorerExt", "Paste"),
                tr("FileExplorerExt", "Some items could not be pasted:\n\n{}").format(
                    "\n".join(errors[:10])
                ),
            )

    def _confirm_overwrite(self, path: Path) -> bool:
        return (
            qtw.QMessageBox.question(
                self,
                tr("FileExplorerExt", "Override confirmation"),
                tr("FileExplorerExt", "File {} already exists. Override?").format(str(path)),
                QtCompat.StandardButton.Yes | QtCompat.StandardButton.No,
                QtCompat.StandardButton.No,
            )
            == QtCompat.StandardButton.Yes
        )

    # --- Save --------------------------------------------------------------

    def save_here(self) -> None:
        doc = App.ActiveDocument
        if not doc:
            QtCompat.message_box(
                self,
                tr("FileExplorerExt", "Save document here"),
                tr("FileExplorerExt", "There is no active document to save."),
            )
            return

        root = Path(self.root())
        if not root.exists() or not root.is_dir():
            QtCompat.message_box(
                self,
                tr("FileExplorerExt", "Save document here"),
                tr("FileExplorerExt", "Invalid directory."),
            )
            return

        try:
            if filename := doc.FileName:
                source = Path(filename)
                target = root / source.name
                same_folder = source.parent.resolve() == root.resolve()
                if target.exists() and not same_folder and not self._confirm_overwrite(target):
                    return
                if same_folder:
                    doc.save()
                else:
                    doc.saveAs(str(target))
                    App.Console.PrintNotification(
                        f"Saved to {doc.FileName}. Old version left at {source!s}\n"
                    )
                add_recent_file(str(target))
            else:
                new_name, ok = qtw.QInputDialog.getText(
                    self,
                    tr("FileExplorerExt", "Save as..."),
                    tr("FileExplorerExt", "Enter file name:"),
                    QtCompat.EchoMode.Normal,
                    f"{doc.Name}.FCStd",
                )
                new_name = new_name.strip() if ok else ""
                if not new_name:
                    return
                if not new_name.lower().endswith(".fcstd"):
                    new_name = f"{new_name}.FCStd"
                target = root / new_name
                if target.exists() and not self._confirm_overwrite(target):
                    return
                doc.saveAs(str(target))
                add_recent_file(str(target))
        except Exception as e:
            QtCompat.message_box(self, tr("FileExplorerExt", "Save document here"), str(e))

        self.refresh()
        self._state.recent_files_changed.emit()

    def save_all_here(self) -> None:
        documents = App.listDocuments()
        if not documents:
            QtCompat.message_box(
                self,
                tr("FileExplorerExt", "Save all here"),
                tr("FileExplorerExt", "There is no open document to save."),
            )
            return

        root = Path(self.root())
        if not root.exists() or not root.is_dir():
            QtCompat.message_box(
                self,
                tr("FileExplorerExt", "Save all here"),
                tr("FileExplorerExt", "Invalid directory."),
            )
            return

        saved = 0
        skipped = 0
        errors: list[str] = []
        for doc in documents.values():
            try:
                filename = doc.FileName
                name = Path(filename).name if filename else f"{doc.Name}.FCStd"
                target = root / name
                if filename and Path(filename).resolve() == target.resolve():
                    doc.save()
                else:
                    if target.exists() and not self._confirm_overwrite(target):
                        skipped += 1
                        continue
                    doc.saveAs(str(target))
                add_recent_file(str(target))
                saved += 1
            except Exception as e:
                errors.append(f"{doc.Name}: {e}")

        self.refresh()
        self._state.recent_files_changed.emit()
        message = tr("FileExplorerExt", "Saved {} document(s).").format(saved)
        if skipped:
            message += "\n" + tr("FileExplorerExt", "Skipped {} conflict(s).").format(skipped)
        if errors:
            message += "\n\n" + "\n".join(errors[:10])
        qtw.QMessageBox.information(self, tr("FileExplorerExt", "Save all here"), message)

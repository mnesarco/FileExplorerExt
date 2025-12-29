# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Favorites.
"""

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence

import FreeCAD as App  # type: ignore

from ._intl import tr
from ._qt import qtc, qtg, qtw
from ._state import State
from ._style import Icons

Role = qtc.Qt.ItemDataRole


@dataclass
class Favorite:
    path: str
    name: str = ""
    kind: str = "user"
    order: int = 2

    def __post_init__(self) -> None:
        if not self.name:
            self.name = Path(self.path).stem


RootDir = Favorite(
    path="",
    name=tr("FileExplorerExt", "This PC"),
    kind="root",
    order=0,
)

HomeDir = Favorite(
    path=qtc.QDir.homePath(),
    name=tr("FileExplorerExt", "Home"),
    kind="home",
    order=1,
)

MacrosDir = Favorite(
    path=App.getUserMacroDir(True),
    name=tr("FileExplorerExt", "Macros"),
    kind="macro",
    order=1,
)


class DuplicatedFavoriteError(Exception):
    pass


class FavoritesModel(qtc.QAbstractListModel):
    """
    Favorites Model.
    """

    def __init__(
        self,
        user: list[Favorite],
        parent: qtc.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._items: list[Favorite] = [RootDir, HomeDir, MacrosDir] + user
        self.icons = {
            "root": Icons.RootDir,
            "home": Icons.HomeDir,
            "macro": Icons.Macros,
            "user": Icons.FavoriteDir,
        }

    def rowCount(
        self,
        parent: qtc.QModelIndex | qtc.QPersistentModelIndex = qtc.QModelIndex(),
    ) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(
        self,
        index: qtc.QModelIndex | qtc.QPersistentModelIndex,
        role: int = Role.DisplayRole,
    ) -> object:
        if not index.isValid() or index.row() >= len(self._items):
            return None

        item = self._items[index.row()]
        match role:
            case Role.DisplayRole:
                return item.name
            case Role.DecorationRole:
                return self.icons.get(item.kind, None)
            case Role.UserRole:
                return item
            case Role.ToolTipRole:
                return item.path
            case _:
                return None

    def flags(self, index: qtc.QModelIndex | qtc.QPersistentModelIndex) -> qtc.Qt.ItemFlag:
        default_flags = super().flags(index)
        if index.isValid():
            item = self._items[index.row()]
            # Only user favorites can be dragged and dropped
            if item.kind == "user":
                return default_flags | qtc.Qt.ItemFlag.ItemIsDragEnabled | qtc.Qt.ItemFlag.ItemIsDropEnabled
        return default_flags | qtc.Qt.ItemFlag.ItemIsDropEnabled

    def supportedDropActions(self) -> qtc.Qt.DropAction:
        return qtc.Qt.DropAction.MoveAction

    def mimeTypes(self) -> list[str]:
        return ["application/x-qabstractitemmodeldatalist", "text/uri-list", "text/plain"]

    def mimeData(self, indexes: Sequence[qtc.QModelIndex]) -> qtc.QMimeData:
        mime_data = super().mimeData(indexes)
        if indexes:
            # Store the row being dragged
            item = self._items[indexes[0].row()]
            mime_data.setText(item.path)
        return mime_data

    def addItem(self, fav: Favorite) -> None:
        for it in self._items:
            if it.path == fav.path:
                raise DuplicatedFavoriteError

        row = len(self._items)
        self.beginInsertRows(qtc.QModelIndex(), row, row)
        self._items.append(fav)
        self.endInsertRows()

    def removeItem(self, row: int) -> None:
        if 0 <= row < len(self._items):
            self.beginRemoveRows(qtc.QModelIndex(), row, row)
            del self._items[row]
            self.endRemoveRows()

    def clear(self) -> None:
        if self._items:
            self.beginResetModel()
            self._items.clear()
            self.endResetModel()

    def setItems(self, items: list[Favorite]) -> None:
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()

    def getItem(self, row: int) -> Favorite | None:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def contains_name(self, name: str) -> bool:
        for fav in self._items:
            if name == fav.name:
                return True
        return False

    def findIndex(self, path: str) -> qtc.QModelIndex | None:
        for row, fav in enumerate(self._items):
            if path == fav.path:
                return self.index(row, 0)
        return None

    def moveItem(self, from_row: int, to_row: int) -> bool:
        """Move an item from one position to another. Only user favorites can be moved."""
        if not (0 <= from_row < len(self._items) and 0 <= to_row < len(self._items)):
            return False

        # Don't allow moving system favorites (root, home, macro)
        if self._items[from_row].kind != "user":
            return False

        # Don't allow moving into system favorites positions
        system_count = sum(1 for f in self._items if f.kind != "user")
        if to_row < system_count:
            return False

        if from_row == to_row:
            return False

        self.beginMoveRows(qtc.QModelIndex(), from_row, from_row, qtc.QModelIndex(),
                          to_row + 1 if to_row > from_row else to_row)
        item = self._items.pop(from_row)
        self._items.insert(to_row, item)
        self.endMoveRows()
        return True

    def get_state(self) -> list[tuple[str, str | None]]:
        return [(f.path, f.name) for f in self._items if f.kind == "user"]


class FavoritesWidget(qtw.QListView):
    """
    Favorites View.
    """

    _model: FavoritesModel
    _state: State

    def __init__(
        self,
        state: State,
        parent: qtw.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("FileExplorerExt_Favorites")
        user_data = [
            Favorite(path, name) for path, name in state.get_favorites()
        ]
        self._model = FavoritesModel(user_data, self)
        self._state = state
        self.setModel(self._model)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(qtw.QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(qtc.Qt.DropAction.MoveAction)
        self.setSelectionMode(
            qtw.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.setContextMenuPolicy(qtc.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)
        self.setIconSize(qtc.QSize(16, 16))
        self.setSpacing(2)

        self.activated.connect(self.on_activated)
        self.clicked.connect(self.on_activated)

        state.tree_root_changed.connect(self.on_tree_root_changed)

        # TODO: Shortcut conflict with tree
        # rename_action = self.addAction(
        #     tr("FileExplorerExt", "Rename favorite"),
        #     lambda: self.rename_favorite(self.currentIndex()),
        # )
        # rename_action.setPriority(qtg.QAction.Priority.LowPriority)
        # rename_action.setShortcutContext(qtc.Qt.ShortcutContext.WidgetShortcut)

    def on_tree_root_changed(self, path: str) -> None:
        index = self._model.findIndex(path)
        if index and index.isValid():
            self.selectionModel().select(
                index, qtc.QItemSelectionModel.SelectionFlag.ClearAndSelect
            )
        else:
            self.selectionModel().clear()

    def on_activated(self, index: qtc.QModelIndex) -> None:
        if index.isValid():
            path = self._model.getItem(index.row())
            if path:
                self._state.request_root_change.emit(path.path)

    def dragEnterEvent(self, event: qtg.QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: qtg.QDragMoveEvent) -> None:
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: qtg.QDropEvent) -> None:
        mime_data = event.mimeData()

        # Check if this is an internal move (reordering)
        if event.source() == self and event.proposedAction() == qtc.Qt.DropAction.MoveAction:
            drop_index = self.indexAt(event.position().toPoint())
            current_index = self.currentIndex()

            if current_index.isValid():
                from_row = current_index.row()
                # If dropping between items, use the index; if on an item, insert before it
                to_row = drop_index.row() if drop_index.isValid() else len(self._model._items) - 1

                if self._model.moveItem(from_row, to_row):
                    self._state.save_favorites(self._model.get_state())
                    event.acceptProposedAction()
            return

        # Handle URLs (from file system)
        if mime_data.hasUrls():
            for url in mime_data.urls():
                if (path := url.toLocalFile()) and self.add_path(path):
                    event.acceptProposedAction()

        # Handle text (file path from tree view)
        elif mime_data.hasText():
            path = mime_data.text()
            if path and self.add_path(path):
                event.acceptProposedAction()

    def add_path(self, path: str) -> bool:
        if not Path(path).is_dir():
            return False
        try:
            self._model.addItem(Favorite(path))
            self._state.save_favorites(self._model.get_state())
            return True
        except DuplicatedFavoriteError:
            qtw.QMessageBox.warning(
                self,
                tr("FileExplorerExt", "Duplicated"),
                tr("FileExplorerExt", "Duplicated favorite"),
            )
        return False

    def on_context_menu(self, position: qtc.QPoint) -> None:
        index = self.indexAt(position)
        if not index.isValid():
            return

        fav = self._model.getItem(index.row())
        if not fav or fav.kind != "user":
            return

        menu = qtw.QMenu(self)

        menu.addAction(
            tr("FileExplorerExt", "Rename"),
            lambda: self.rename_favorite(index),
        )

        menu.addAction(
            tr("FileExplorerExt", "Remove from Favorites"),
            lambda: self.remove_favorite(index),
        )

        menu.addAction(
            Icons.DefaultDir,
            tr("FileExplorerExt", "Set as default dir"),
            lambda: self._state.set_default_dir(fav.path),
        )

        menu.exec(self.mapToGlobal(position))  # type: ignore -> False positive

    def remove_favorite(self, index: qtc.QModelIndex) -> None:
        if not index.isValid():
            return
        fav = self._model.getItem(index.row())
        if fav and fav.kind == "user":
            self._model.removeItem(index.row())
            self._state.save_favorites(self._model.get_state())

    def rename_favorite(self, index: qtc.QModelIndex) -> None:
        if not index.isValid():
            return

        row = index.row()
        fav = self._model.getItem(row)
        if not fav:
            return

        new_name, ok = qtw.QInputDialog.getText(
            self,
            tr("FileExplorerExt", "Rename Favorite"),
            tr("FileExplorerExt", "Enter new name:"),
            qtw.QLineEdit.EchoMode.Normal,
            fav.name,
        )

        if ok and (new_name := new_name.strip()) and new_name != fav.name:
            suffix = 1
            base_name = new_name
            while self._model.contains_name(new_name):
                new_name = f"{base_name}{suffix:03}"
                suffix += 1
            fav.name = new_name
            self._state.save_favorites(self._model.get_state())
            self._model.dataChanged.emit(index, index)

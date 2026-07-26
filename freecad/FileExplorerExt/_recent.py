# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Recent Files Grid.
"""

from __future__ import annotations

from ._preferences import (
    get_recent_files,
    get_recent_files_group,
)
from ._preview import FilePreviewCard
from ._qt import QtCompat, qtc, qtw
from ._state import State

_CARD_WIDTH = 150
_CARD_HEIGHT = 210


class RecentFilesWidget(qtw.QListWidget):
    """
    Grid widget displaying file preview cards.
    """

    _state: State

    def __init__(
        self,
        state: State,
        parent: qtw.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("FileExplorerExt_Recent")
        self._state = state
        self._init_ui()
        state.request_recent_files.connect(self._load_recent_files)

        self.pref_group = get_recent_files_group()
        self.pref_group.AttachManager(self)

    def _init_ui(self) -> None:
        self.setViewMode(QtCompat.ListView_ViewMode.IconMode)
        self.setFlow(QtCompat.ListView_Flow.LeftToRight)
        self.setResizeMode(QtCompat.ListView_ResizeMode.Adjust)
        self.setMovement(QtCompat.ListView_Movement.Static)
        self.setWrapping(True)
        self.setSpacing(10)
        self.setUniformItemSizes(True)
        self.setGridSize(qtc.QSize(_CARD_WIDTH, _CARD_HEIGHT))

    def add_tile(self, path: str) -> FilePreviewCard:
        card = FilePreviewCard(path, _CARD_WIDTH, _CARD_HEIGHT)
        item = qtw.QListWidgetItem(self)
        item.setSizeHint(qtc.QSize(_CARD_WIDTH, _CARD_HEIGHT))
        item.setData(QtCompat.ItemDataRole.UserRole, path)
        self.addItem(item)
        self.setItemWidget(item, card)
        return card

    def remove_tile(self, path: str) -> bool:
        for i in range(self.count()):
            item = self.item(i)
            if item and item.data(QtCompat.ItemDataRole.UserRole) == path:
                self.takeItem(i)
                return True
        return False

    def clear_tiles(self) -> None:
        self.clear()

    def _load_recent_files(self) -> None:
        self.clear_tiles()
        for path in get_recent_files():
            self.add_tile(path)

    def load_recent_files(self) -> None:
        qtc.QTimer.singleShot(0, self._load_recent_files)

    def slotParamChanged(self, _grp, _typ, _entry, _value) -> None:
        self.load_recent_files()

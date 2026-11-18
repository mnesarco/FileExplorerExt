# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Recent Files Grid.
"""

from __future__ import annotations

from pathlib import Path

from ._preferences import (
    get_recent_files,
    get_recent_files_group,
)
from ._preview import FilePreviewCard
from ._qt import QtCompat, qtc, qtg, qtw
from ._state import State

_CARD_WIDTH = 150
_CARD_HEIGHT = 210
_CARD_SPACING = 10


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
        self._dirty = True
        self._init_ui()
        state.request_recent_files.connect(self._load_recent_files)
        state.recent_files_changed.connect(self._mark_dirty)

        self.pref_group = get_recent_files_group()
        self.pref_group.AttachManager(self)

    def _init_ui(self) -> None:
        self.setViewMode(QtCompat.ListView_ViewMode.IconMode)
        self.setFlow(QtCompat.ListView_Flow.LeftToRight)
        self.setResizeMode(QtCompat.ListView_ResizeMode.Adjust)
        self.setMovement(QtCompat.ListView_Movement.Static)
        self.setWrapping(True)
        self.setSpacing(_CARD_SPACING)
        self.setUniformItemSizes(True)
        self.setGridSize(qtc.QSize(_CARD_WIDTH + _CARD_SPACING, _CARD_HEIGHT + _CARD_SPACING))

    def add_tile(self, path: str) -> FilePreviewCard:
        card = FilePreviewCard(
            path,
            _CARD_WIDTH,
            _CARD_HEIGHT,
            on_remove=self._load_recent_files,
            on_open=self._state.open_file,
        )
        item = qtw.QListWidgetItem(self)
        item.setSizeHint(qtc.QSize(_CARD_WIDTH, _CARD_HEIGHT))
        item.setData(QtCompat.ItemDataRole.UserRole, path)
        self.addItem(item)
        self.setItemWidget(item, card)
        return card

    def clear_tiles(self) -> None:
        # clear() orphans item widgets: free them or they pile up with their thumbnails.
        for row in range(self.count()):
            if widget := self.itemWidget(self.item(row)):
                widget.deleteLater()
        self.clear()

    def _mark_dirty(self) -> None:
        """Rebuild lazily: a batch of file operations must not reload every thumbnail."""
        self._dirty = True
        if self.isVisible():
            self._load_recent_files()

    def _load_recent_files(self) -> None:
        self._dirty = False
        self.clear_tiles()
        for path in get_recent_files():
            if not path:
                continue
            card = self.add_tile(path)
            if not Path(path).exists():
                card.mark_missing()

    def showEvent(self, event: qtg.QShowEvent) -> None:
        if self._dirty:
            self._load_recent_files()
        super().showEvent(event)

    def slotParamChanged(self, _grp, _typ, _entry, _value) -> None:
        self._mark_dirty()

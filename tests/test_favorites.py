# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""Tests for the favorites list keyboard behaviour."""

from __future__ import annotations

from pathlib import Path

import PySide6.QtCore as qtc
import PySide6.QtGui as qtg

from freecad.FileExplorerExt._favorites import FavoritesWidget
from freecad.FileExplorerExt._state import State


def _enter(widget: FavoritesWidget) -> None:
    event = qtg.QKeyEvent(
        qtc.QEvent.Type.KeyPress,
        qtc.Qt.Key.Key_Return,
        qtc.Qt.KeyboardModifier.NoModifier,
    )
    widget.keyPressEvent(event)


def test_enter_opens_the_highlighted_favorite(tmp_path: Path) -> None:
    state = State()
    widget = FavoritesWidget(state)
    (tmp_path / "fav").mkdir()
    assert widget.add_path(str(tmp_path / "fav"))

    widget.setCurrentIndex(widget._model.findIndex(str(tmp_path / "fav")))
    opened: list[str] = []
    state.request_root_change.connect(opened.append)

    _enter(widget)

    assert opened == [str(tmp_path / "fav")]


def test_double_click_does_not_open_twice(tmp_path: Path) -> None:
    state = State()
    widget = FavoritesWidget(state)
    (tmp_path / "fav").mkdir()
    assert widget.add_path(str(tmp_path / "fav"))

    index = widget._model.findIndex(str(tmp_path / "fav"))
    opened: list[str] = []
    state.request_root_change.connect(opened.append)

    widget.clicked.emit(index)
    widget.activated.emit(index)  # what a double click would add on top of clicked

    assert opened == [str(tmp_path / "fav")]

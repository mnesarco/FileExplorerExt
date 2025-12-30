# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Qt
"""

from typing import TYPE_CHECKING

if not TYPE_CHECKING:
    import PySide.QtCore as qtc
    import PySide.QtGui as qtg
    import PySide.QtWidgets as qtw

    try:
        IS_QT6_SUPPORTED = qtc.qVersion().startswith("6.")
    except Exception:
        IS_QT6_SUPPORTED = False

if TYPE_CHECKING:
    import PySide6.QtCore as qtc
    import PySide6.QtGui as qtg
    import PySide6.QtWidgets as qtw

    IS_QT6_SUPPORTED = True


if not IS_QT6_SUPPORTED:

    class QtCompat:
        """Compatibility layer for Qt5 enum differences."""

        ItemFlag = qtc.Qt
        DropAction = qtc.Qt
        DragDropMode = qtw.QAbstractItemView
        SelectionMode = qtw.QAbstractItemView
        ContextMenuPolicy = qtc.Qt
        SelectionFlag = qtc.QItemSelectionModel
        EchoMode = qtw.QLineEdit
        AlignmentFlag = qtc.Qt
        AspectRatioMode = qtc.Qt
        TransformationMode = qtc.Qt
        Orientation = qtc.Qt.Orientation
        ToolButtonStyle = qtc.Qt
        FocusPolicy = qtc.Qt
        DockWidgetArea = qtc.Qt

        @staticmethod
        def get_event_pos(event):
            return event.pos()

        @staticmethod
        def exec_menu(menu, pos):
            return menu.exec_(pos)

        @staticmethod
        def set_file_system_options(model):
            pass


if IS_QT6_SUPPORTED:

    class QtCompat:
        """Compatibility layer for Qt6 enum differences."""

        ItemFlag = qtc.Qt.ItemFlag
        DropAction = qtc.Qt.DropAction
        DragDropMode = qtw.QAbstractItemView.DragDropMode
        SelectionMode = qtw.QAbstractItemView.SelectionMode
        ContextMenuPolicy = qtc.Qt.ContextMenuPolicy
        SelectionFlag = qtc.QItemSelectionModel.SelectionFlag
        EchoMode = qtw.QLineEdit.EchoMode
        AlignmentFlag = qtc.Qt.AlignmentFlag
        AspectRatioMode = qtc.Qt.AspectRatioMode
        TransformationMode = qtc.Qt.TransformationMode
        Orientation = qtc.Qt.Orientation
        ToolButtonStyle = qtc.Qt.ToolButtonStyle
        FocusPolicy = qtc.Qt.FocusPolicy
        DockWidgetArea = qtc.Qt.DockWidgetArea

        @staticmethod
        def get_event_pos(event: qtg.QMouseEvent | qtg.QDropEvent):
            """Get position from mouse event."""
            return event.position().toPoint()

        @staticmethod
        def exec_menu(menu: qtw.QMenu, pos: qtc.QPoint):
            """Execute menu."""
            return menu.exec(pos)  # type: ignore

        @staticmethod
        def set_file_system_options(model: qtw.QFileSystemModel):
            """Set QFileSystemModel options."""
            model.setOptions(
                qtw.QFileSystemModel.Option.DontUseCustomDirectoryIcons
            )

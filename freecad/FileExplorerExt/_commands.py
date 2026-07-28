# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Commands.
"""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import ClassVar

import FreeCAD as App
import FreeCADGui as Gui

from ._explorer import toggle
from ._intl import tr
from ._qt import QtCompat, qtw
from ._api import ApiState

class FEE_ToggleExplorer:
    """
    Toggle File Explorer View.
    """

    DefaultAccel = "F3"

    def GetResources(self) -> dict[str, str]:
        return {
            "Pixmap": str(Path(__file__).parent / "resources" / "icon.svg"),
            "MenuText": tr("FileExplorerExt", "Toggle File Explorer"),
            "ToolTip": tr("FileExplorerExt", "Toggle File Explorer Panel"),
            "Accel": self.Shortcut,
        }

    def Activated(self, index: int = 0) -> None:
        toggle()

    def IsActive(self) -> bool:
        return True

    @classmethod
    def Name(cls) -> str:
        return cls.__name__

    @property
    def Shortcut(self) -> str:
        return App.ParamGet(
            "User parameter:BaseApp/Preferences/Shortcut"
        ).GetString(
            self.Name(),
            self.DefaultAccel,
        )

    @classmethod
    def Install(cls) -> None:
        self = cls()
        Gui.addCommand(self.Name(), self)
        window = Gui.getMainWindow()
        action = QtCompat.addAction(
            window,
            None,
            tr("FileExplorerExt", "Toggle File Explorer View"),
            lambda: Gui.runCommand(self.Name(), 0),
        )
        action.setShortcut(self.Shortcut)


class FEE_SaveSession:
    """
    Save open file list.
    """

    DefaultAccel = "Ctrl+F3"

    def GetResources(self) -> dict[str, str]:
        return {
            "Pixmap": str(
                Path(__file__).parent / "resources" / "icons" / "save-list.svg"
            ),
            "MenuText": tr("FileExplorerExt", "Save open file list (session)"),
            "ToolTip": tr("FileExplorerExt", "Save open file list (session)"),
            "Accel": self.Shortcut,
        }

    def Activated(self, index: int = 0) -> None:
        filter = "FreeCAD File List (*.fclist)"
        file, _ = qtw.QFileDialog.getSaveFileName(
            App.Gui.getMainWindow(),
            tr("FileExplorerExt", "Save open file paths as a list (session)"),
            str(ApiState.selected_path or ""),
            filter,
            filter,
        )
        if file:
            from ._fclist import FCListImportHandler
            FCListImportHandler.save(file)


    def IsActive(self) -> bool:
        return bool(App.listDocuments())

    @classmethod
    def Name(cls) -> str:
        return cls.__name__

    @property
    def Shortcut(self) -> str:
        return App.ParamGet(
            "User parameter:BaseApp/Preferences/Shortcut"
        ).GetString(
            self.Name(),
            self.DefaultAccel,
        )

    @classmethod
    def Install(cls) -> None:
        Gui.addCommand(cls.Name(), cls())


class WorkbenchManipulator:
    """Adds/Remove Commands to Gui"""

    _instance: ClassVar[WorkbenchManipulator | None] = None

    def modifyMenuBar(self) -> list[dict[str, str]]:
        """Add commands to menus."""
        return [
            {
                "insert": FEE_SaveSession.Name(),
                "after": "",
                "menuItem": "Std_SaveAll",
            }
        ]

    def modifyContextMenu(self, recipient: str) -> list[dict[str, str]]:
        """Add commands to the context menu."""
        return []

    def modifyToolBars(self) -> list[dict[str, str]]:
        """Add commands to toolbars."""
        return []

    @classmethod
    def install(cls) -> None:
        """Apply the workbench manipulator to the live session"""
        if App.GuiUp and cls._instance is None:
            cls._instance = WorkbenchManipulator()
            App.Gui.addWorkbenchManipulator(cls._instance)
            with suppress(Exception):
                App.Gui.activeWorkbench().reloadActive()

    @classmethod
    def uninstall(cls) -> None:
        """Remove the workbench manipulator to the live session"""
        if App.GuiUp and cls._instance is not None:
            App.Gui.removeWorkbenchManipulator(cls._instance)
            cls._instance = None
            with suppress(Exception):
                App.Gui.activeWorkbench().reloadActive()

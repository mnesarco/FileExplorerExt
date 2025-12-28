# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Commands.
"""

from pathlib import Path

import FreeCAD as App  # type: ignore
import FreeCADGui as Gui  # type: ignore

from ._explorer import toggle
from ._intl import tr


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
            "Accel": self.DefaultAccel,
        }

    def Activated(self, index: int = 0) -> None:
        toggle()

    def IsActive(self) -> bool:
        return True

    @property
    def Name(self) -> str:
        return self.__class__.__name__

    @property
    def Shortcut(self) -> str:
        return App.ParamGet(
            "User parameter:BaseApp/Preferences/Shortcut"
        ).GetString(
            self.Name,
            self.DefaultAccel,
        )

    def Install(self) -> None:
        Gui.addCommand(self.Name, self)
        window = Gui.getMainWindow()
        action = window.addAction(
            tr("FileExplorerExt", "Toggle File Explorer View"),
            lambda: Gui.runCommand(self.Name, 0),
        )
        action.setShortcut(self.Shortcut)

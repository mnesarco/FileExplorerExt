# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

from ._qt import IS_QT6_SUPPORTED
import FreeCAD as App  # type: ignore

if not IS_QT6_SUPPORTED:
    App.Console.PrintWarning(
        "FileExplorer requires Qt6, Qt5 may work but it is not officially supported."
    )

from ._intl import install_translations

install_translations()

from ._explorer import show
from ._commands import FEE_ToggleExplorer

cmd = FEE_ToggleExplorer()
cmd.Install()
show()

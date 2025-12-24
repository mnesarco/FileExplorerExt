# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz
# SPDX-FileNotice: Part of the File Explorer addon.

from ._qt import IS_QT6_SUPPORTED

if not IS_QT6_SUPPORTED:
    import FreeCAD as App
    App.Console.PrintWarning("FileExplorer requires Qt6")
else:
    from . import _explorer
    _explorer.show()

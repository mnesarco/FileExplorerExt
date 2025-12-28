# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Translation.
"""

import FreeCAD as App

tr = App.Qt.translate

def install_translations() -> None:
    import FreeCADGui as Gui
    from pathlib import Path
    Gui.addLanguagePath(str(Path(__file__).parent / "resources" / "translations"))

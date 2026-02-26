# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Translation.
"""

import FreeCAD as App  # type: ignore
from pathlib import Path

tr = App.Qt.translate


def install_translations() -> None:
    if not App.GuiUp:
        msg = "Translations must be loaded only after GUI is up."
        raise RuntimeError(msg)

    App.Gui.addLanguagePath(
        str(Path(__file__).parent / "resources" / "translations")
    )


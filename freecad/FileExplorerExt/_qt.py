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

if TYPE_CHECKING:
    import PySide6.QtCore as qtc
    import PySide6.QtGui as qtg
    import PySide6.QtWidgets as qtw

try:
    IS_QT6_SUPPORTED = qtc.qVersion().startswith("6.")
except Exception:
    IS_QT6_SUPPORTED = False

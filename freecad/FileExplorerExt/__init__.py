# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
Advanced File Explorer FreeCAD Addon.
"""

from ._api import API as API, _CustomFileAction as CustomFileAction
from ._fclist import FCListImportHandler

FCListImportHandler.install()

__all__ = ("API", "CustomFileAction")

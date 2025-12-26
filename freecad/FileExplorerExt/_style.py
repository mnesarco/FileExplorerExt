# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Application style.
"""

from ._qt import qtg, qtw


class Icons:
    standardIcon = qtw.QApplication.style().standardIcon
    fromTheme = qtg.QIcon.fromTheme
    pixmaps = qtw.QStyle.StandardPixmap

    RootDir = standardIcon(pixmaps.SP_ComputerIcon)
    HomeDir = fromTheme("user-home", standardIcon(pixmaps.SP_DirHomeIcon))
    FavoriteDir = fromTheme("folder", standardIcon(pixmaps.SP_DirIcon))

    SysOpen = fromTheme("document-open", standardIcon(pixmaps.SP_DirOpenIcon))
    Import = standardIcon(pixmaps.SP_ArrowForward)

    Copy = fromTheme("edit-copy", standardIcon(pixmaps.SP_CommandLink))

    Macros = standardIcon(pixmaps.SP_FileIcon)

    NavUp = fromTheme("go-up", standardIcon(pixmaps.SP_ArrowUp))
    NavBack = fromTheme("go-previous", standardIcon(pixmaps.SP_ArrowBack))
    NavForward = fromTheme("go-next", standardIcon(pixmaps.SP_ArrowForward))

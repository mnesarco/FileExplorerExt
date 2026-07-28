# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: File utils.
"""

import re
import shutil
from pathlib import Path
from typing import cast

import FreeCAD as App

from ._preferences import add_recent_file
from ._qt import qtg

SUPPORTED_IMAGE_FORMATS = set([
    f".{str(f, 'utf-8')}".lower()  # ty:ignore[invalid-argument-type]
    for f in qtg.QImageReader.supportedImageFormats()
])


def is_image_file(file_path: str) -> bool:
    """Return True if Qt can read the image format."""
    path = Path(file_path)
    return (
        (path.suffix or "").lower() in SUPPORTED_IMAGE_FORMATS
    ) and path.exists()


def is_fcstd_file(file_path: str) -> bool:
    """Return True if file_path is a FCStd file."""
    return file_path.lower().endswith(".fcstd") and Path(file_path).exists()


def is_fclist_file(file_path: str) -> bool:
    """Return True if file_path is a FCList file."""
    return file_path.lower().endswith(".fclist") and Path(file_path).exists()


def get_import_module(path: str) -> str | None:
    """Return the module to import path if any."""
    ext = (path.split(".")[-1] or "").lower()
    modules = cast("list[str]", App.getImportType(ext))
    if modules:
        return modules[0]
    return None


def open_file(file_path: str) -> None:
    ext = (file_path.split(".")[-1] or "").lower()
    if ext == "fcstd":
        App.openDocument(file_path)
        add_recent_file(file_path)
    else:
        module = get_import_module(file_path)
        if module:
            try:
                from freecad import module_io  # type: ignore
            except ImportError:
                App.Gui.insert(file_path)
            else:
                module_io.OpenInsertObject(module, file_path, "open")
        else:
            App.Console.PrintWarning(f"File type not supported: {file_path}\n")


def import_file(file_path: str) -> None:
    ext = (file_path.split(".")[-1] or "").lower()

    doc_name = App.ActiveDocument.Name if App.ActiveDocument else None
    if ext == "fcstd":
        App.Gui.insert(file_path, doc_name)  # ty:ignore[invalid-argument-type] Bad FreeCAD stuff signature typings
        add_recent_file(file_path)
        return

    module = get_import_module(file_path)
    if module:
        try:
            from freecad import module_io  # type: ignore
        except ImportError:
            App.Gui.insert(file_path, doc_name)  # ty:ignore[invalid-argument-type] Bad FreeCAD stuff signature typings
        else:
            module_io.OpenInsertObject(
                module,
                file_path,
                "insert",
                doc_name,
            )
    else:
        App.Console.PrintWarning(f"File type not supported: {file_path}\n")


def duplicate_file(file: str) -> None:
    path = Path(file)
    if not path.exists() or not path.is_file():
        return
    base = path.stem
    ext = path.suffix
    m = re.match(r"(.*?)(\d+)$", base)
    num = 1
    if m:
        base, num = m.groups()
        num = int(num) + 1
    else:
        base += "."

    copy = path.parent / f"{base}{num}{ext}"
    while copy.exists():
        num += 1
        copy = path.parent / f"{base}{num}{ext}"
    shutil.copy2(str(path), str(copy))

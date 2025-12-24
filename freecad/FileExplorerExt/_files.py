# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: File utils.
"""

import re
import shutil
import types
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui

from ._qt import qtg

SUPPORTED_IMAGE_FORMATS = set([
    f".{str(f, 'utf-8')}".lower()
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


def get_import_module(path: str) -> types.ModuleType | None:
    """Return the module to import path if any."""
    ext = (path.split(".")[-1] or "").lower()
    modules = App.getImportType(ext)
    if modules:
        return modules[0]
    return None


def open_file(file_path: str) -> None:
    ext = (file_path.split(".")[-1] or "").lower()
    if ext == "fcstd":
        App.openDocument(file_path)
    else:
        module = get_import_module(file_path)
        if module:
            try:
                from freecad import module_io
            except ImportError:
                Gui.insert(file_path)
            else:
                module_io.OpenInsertObject(module, file_path, "open")
        else:
            App.Console.PrintWarning(f"File type not supported: {file_path}\n")


def import_file(file_path: str) -> None:
    ext = (file_path.split(".")[-1] or "").lower()

    doc_name = App.ActiveDocument.Name if App.ActiveDocument else None
    if ext == "fcstd":
        Gui.insert(file_path, doc_name)

    module = get_import_module(file_path)
    if module:
        try:
            from freecad import module_io
        except ImportError:
            Gui.insert(file_path, doc_name)
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

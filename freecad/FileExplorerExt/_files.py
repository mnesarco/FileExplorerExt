# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: File utils.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import cast

import FreeCAD as App

from ._preferences import add_recent_file
from ._qt import qtc, qtg

SUPPORTED_IMAGE_FORMATS = set(
    [
        f".{str(f, 'utf-8')}".lower()  # ty:ignore[invalid-argument-type]
        for f in qtg.QImageReader.supportedImageFormats()
    ]
)


def is_image_file(file_path: str) -> bool:
    """Return True if Qt can read the image format."""
    path = Path(file_path)
    return ((path.suffix or "").lower() in SUPPORTED_IMAGE_FORMATS) and path.exists()


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


def open_document_paths() -> list[Path]:
    """Files of all currently open documents (unsaved documents have none)."""
    paths: list[Path] = []
    for doc in App.listDocuments().values():
        filename = getattr(doc, "FileName", "")
        if filename:
            paths.append(Path(filename))
    return paths


def path_touches_open_document(path: str | Path) -> bool:
    """True if path is an open document's file or a directory containing one."""
    target = Path(path)
    for doc_path in open_document_paths():
        if doc_path == target:
            return True
        try:
            doc_path.relative_to(target)
        except ValueError:
            continue
        return True
    return False


def show_in_folder(path: str) -> None:
    """Reveal a file in the platform file manager when it is supported."""
    target = Path(path)
    if sys.platform == "win32":
        subprocess.Popen(["explorer", f"/select,{target}"])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(target)])
    else:
        folder = target if target.is_dir() else target.parent
        qtg.QDesktopServices.openUrl(qtc.QUrl.fromLocalFile(str(folder)))


def open_terminal(path: str) -> None:
    """Open a terminal in path. Raises OSError when no terminal is available."""
    target = str(Path(path))
    if sys.platform == "win32":
        subprocess.Popen(["cmd", "/K", f'cd /d "{target}"'])
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-a", "Terminal", target])
        return

    for name in (
        "x-terminal-emulator",
        "gnome-terminal",
        "konsole",
        "xfce4-terminal",
        "xterm",
    ):
        if exe := shutil.which(name):
            subprocess.Popen([exe], cwd=target)
            return
    msg = "No terminal emulator found"
    raise OSError(msg)


def delete_path(file_path: str) -> None:
    path = Path(file_path)
    if path.is_symlink():
        # Never rmtree() through a symlink: it would delete the target's contents.
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    elif os.path.lexists(path):
        path.unlink()
    else:
        msg = f"{file_path} does not exist"
        raise FileNotFoundError(msg)

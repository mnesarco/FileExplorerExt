# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: *.FCList File type handler.
"""

from __future__ import annotations

from pathlib import Path

import FreeCAD as App

from ._files import open_file
from datetime import datetime


class FCListImportHandler:
    """
    File Handler: *.FCList
    """

    @staticmethod
    def _collect(filename: str, files: set[Path], visited: set[str]) -> None:
        """
        Process *.FCList recursively.
        """
        container = Path(filename).resolve()
        parent = container.parent
        visited.add(str(container))

        for line, text in enumerate(container.read_text("utf-8").splitlines()):
            item = text.strip()

            if not item or item.startswith("#"):
                continue

            path = Path(item)
            if not path.is_absolute():
                path = parent / path

            if not path.exists():
                App.Console.PrintWarning(
                    f"File does not exists {container!s}:{line}: {path!s}\n"
                )
                continue

            try:
                path = path.resolve()
            except Exception:
                App.Console.PrintWarning(
                    f"File does not exists {container!s}:{line}: {path!s}\n"
                )
                continue

            if path.suffix.lower() == ".fclist":
                str_path = str(path)
                if str_path not in visited:
                    FCListImportHandler._collect(str_path, files, visited)
                continue

            files.add(path)

    @staticmethod
    def open(filename: str) -> None:
        """
        Open File Handler for *.FCList files.
        """
        files: set[Path] = set()
        FCListImportHandler._collect(filename, files, set())
        for file in files:
            try:
                App.Console.PrintLog(f"Opening listed file: {file!s}")
                open_file(str(file))
            except Exception:
                App.Console.PrintError(f"Failed to load file {file!s}\n")

    @staticmethod
    def save(filename: str) -> None:
        container = Path(filename)
        parent = container.parent
        lines = [f"# Date: {datetime.now().isoformat()}"]
        for name, doc in App.listDocuments().items():
            if not (doc_filename := doc.FileName):  # ty:ignore[unresolved-attribute]
                continue
            path = Path(doc_filename)
            lines.append(f"# Document: {name}")
            if path.is_relative_to(parent):
                lines.append(str(path.relative_to(parent)))
            else:
                lines.append(str(path))
        container.with_suffix(".fclist").write_text("\n".join(lines))

    @staticmethod
    def install():
        App.addImportType("File list (*.FCList)", __class__.__module__)


# FreeCAD API Protocol
open = FCListImportHandler.open

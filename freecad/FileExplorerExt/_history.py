# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Navigation history.
"""


class History:
    back: list[str]
    forward: list[str]

    def __init__(self):
        self.back = []
        self.forward = []

    def add(self, path: str) -> None:
        if not self.back or self.back[-1] != path:
            self.back.append(path)

    def go_back(self) -> str | None:
        if self.back:
            self.forward.append(self.back.pop())
        return self.back[-1] if self.back else None

    def go_forward(self) -> str | None:
        if self.forward:
            return self.forward.pop()
        return None

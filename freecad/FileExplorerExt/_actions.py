# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Builtin Actions

Context menu actions.
"""

import sys
from pathlib import Path

from ._api import API
from ._intl import tr


def action_run_macro(paths: list[Path]) -> None:
    path = paths[0]
    parent = str(path.parent.resolve())
    temp = False
    try:
        if parent not in sys.path:
            temp = True
            sys.path.insert(0, parent)

        import __main__ as mod_main

        env = dict(mod_main.__dict__)
        code = compile(path.read_text("utf-8"), str(path), "exec")
        exec(code, env, env)
    finally:
        if temp:
            sys.path.remove(parent)


def builtin_actions(paths: list[Path]):

    actions = []

    # Run Python/Macro
    if len(paths) == 1 and paths[0].suffix.lower() in (".py", ".fcmacro"):
        actions.append(
            API.CustomFileAction(
                text=tr("FileExplorerExt", "Run Macro/Script"),
                icon=str(
                    Path(__file__).parent
                    / "resources"
                    / "icons"
                    / "play-macro.svg"
                ),
                activated=action_run_macro,
            )
        )

    return actions


API.add_action_provider(builtin_actions, key="FileExplorerExt-Builtin-Actions")

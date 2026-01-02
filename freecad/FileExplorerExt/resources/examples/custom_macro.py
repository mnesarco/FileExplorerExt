# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Example of API usage.

This Macro adds custom actions to the File context menu.
"""

from freecad.FileExplorerExt import API
from freecad.FileExplorerExt import CustomFileAction
from pathlib import Path


def my_actions(paths: list[Path]):
    """
    This function returns set of custom actions based on paths.

    Custom actions are presented as context menu items.
    """

    # This action will apply to any file
    actions = [
        CustomFileAction(
            text="Example action",
            icon=":/icons/edit_OK.svg",
            activated=lambda p: print(f"File: {p!s}"),
        )
    ]

    # This action will apply to svg files
    if paths[0].suffix == ".svg":
        actions.append(
            CustomFileAction(
                text="Example action (Only SVG)",
                icon=":/icons/edit_OK.svg",
                activated=lambda p: print(f"SVG: {p!s}"),
            )
        )

    return actions


# Register the actions provider function in the API
# with unique key to avoid possible repetitions.
API.add_action_provider(my_actions, key="my-custom-actions")

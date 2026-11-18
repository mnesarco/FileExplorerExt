# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""
FileExplorerExt: Builtin Actions

Context menu actions.
"""

import shutil
import sys
import traceback
from pathlib import Path

import FreeCAD as App  # type: ignore

from ._api import API
from ._intl import tr
from ._qt import qtw, QtCompat
from ._state import get_config, save_config


def _parent():
    return getattr(getattr(App, "Gui", None), "getMainWindow", lambda: None)()


def _icon(name: str) -> str:
    return str(Path(__file__).parent / "resources" / "icons" / name)


def _confirm_run(path: Path) -> bool:
    config = get_config()
    if not config.get("macro_confirm", True):
        return True

    box = qtw.QMessageBox(_parent())
    box.setWindowTitle(tr("FileExplorerExt", "Run Macro/Script"))
    box.setText(tr("FileExplorerExt", "Run '{}'?").format(str(path)))
    box.setIcon(QtCompat.MessageBoxIcon.Warning)
    box.setStandardButtons(QtCompat.StandardButton.Yes | QtCompat.StandardButton.No)
    box.setDefaultButton(QtCompat.StandardButton.No)
    checkbox = qtw.QCheckBox(tr("FileExplorerExt", "Don't ask again"))
    box.setCheckBox(checkbox)
    confirmed = box.exec() == QtCompat.StandardButton.Yes
    # Only persist the opt-out when the user actually runs the script.
    if confirmed and checkbox.isChecked():
        config["macro_confirm"] = False
        save_config(config)
    return confirmed


def action_run_macro(paths: list[Path]) -> None:
    path = paths[0]
    if not _confirm_run(path):
        return

    parent = str(path.parent.resolve())
    temp = False
    try:
        if parent not in sys.path:
            temp = True
            sys.path.insert(0, parent)

        import __main__ as mod_main

        env = dict(mod_main.__dict__)
        env["__file__"] = str(path)
        env["__name__"] = "__main__"
        code = compile(path.read_text("utf-8"), str(path), "exec")

        # This may be reported as a security issue, but the purpose of this
        # code is to allow the user to run arbitrary code on its behalf.
        exec(code, env, env)  # nosec

    except Exception:
        qtw.QMessageBox.critical(
            _parent(),
            tr("FileExplorerExt", "Run Macro/Script"),
            traceback.format_exc(),
        )
    finally:
        if temp:
            sys.path.remove(parent)


def action_install_macro(paths: list[Path]) -> None:
    source = paths[0]
    target = Path(App.getUserMacroDir(True)) / source.name
    if target.exists():
        answer = qtw.QMessageBox.question(
            _parent(),
            tr("FileExplorerExt", "Install to macro folder"),
            tr("FileExplorerExt", "'{}' already exists. Overwrite?").format(str(target)),
            QtCompat.StandardButton.Yes | QtCompat.StandardButton.No,
            QtCompat.StandardButton.No,
        )
        if answer != QtCompat.StandardButton.Yes:
            return
    try:
        shutil.copy2(str(source), str(target))
    except OSError as e:
        qtw.QMessageBox.warning(
            _parent(),
            tr("FileExplorerExt", "Install to macro folder"),
            str(e),
        )
        return
    qtw.QMessageBox.information(
        _parent(),
        tr("FileExplorerExt", "Install to macro folder"),
        tr("FileExplorerExt", "Installed to {}").format(str(target)),
    )


def builtin_actions(paths: list[Path]):
    actions = []

    # Run Python/Macro
    if len(paths) == 1 and paths[0].suffix.lower() in (".py", ".fcmacro"):
        actions.append(
            API.CustomFileAction(
                text=tr("FileExplorerExt", "Run Macro/Script"),
                icon=_icon("play-macro.svg"),
                activated=action_run_macro,
            )
        )
        actions.append(
            API.CustomFileAction(
                text=tr("FileExplorerExt", "Install to macro folder"),
                icon=_icon("macros.svg"),
                activated=action_install_macro,
            )
        )

    return actions


API.add_action_provider(builtin_actions, key="FileExplorerExt-Builtin-Actions")

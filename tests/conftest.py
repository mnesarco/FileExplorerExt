"""Test stubs: the addon imports FreeCAD, FreeCADGui and PySide at module level.

The addon is written for FreeCAD's bundled Qt (imported as ``PySide``), so tests
alias PySide6 and provide a minimal FreeCAD stub. Nothing here is shipped.
"""

import os
import sys
import tempfile
import types
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import PySide6  # noqa: E402
import PySide6.QtCore  # noqa: E402
import PySide6.QtGui  # noqa: E402
import PySide6.QtWidgets  # noqa: E402

sys.modules["PySide"] = PySide6
sys.modules["PySide.QtCore"] = PySide6.QtCore
sys.modules["PySide.QtGui"] = PySide6.QtGui
sys.modules["PySide.QtWidgets"] = PySide6.QtWidgets

_TMP = Path(tempfile.mkdtemp(prefix="fileexplorerext-tests-"))


class Group:
    """In-memory FreeCAD parameter group."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def GetStrings(self, key: str) -> list[str]:
        return [name for name in self.store if name.startswith(key)]

    def GetString(self, key: str, default: str = "") -> str:
        return self.store.get(key, default)

    def SetString(self, key: str, value: str) -> None:
        self.store[key] = value

    def RemString(self, key: str) -> None:
        self.store.pop(key, None)

    def AttachManager(self, obj: object) -> None:
        pass


GROUPS: dict[str, Group] = {}


def _param_get(path: str) -> Group:
    return GROUPS.setdefault(path, Group())


class Console:
    @staticmethod
    def PrintWarning(message: str) -> None:
        pass

    PrintLog = PrintUserWarning = PrintError = PrintNotification = PrintWarning


def _freecad() -> types.ModuleType:
    app = types.ModuleType("FreeCAD")
    app.Console = Console
    app.ParamGet = _param_get
    app.listDocuments = lambda: {}
    app.ActiveDocument = None
    app.GuiUp = False
    app.Gui = types.SimpleNamespace(getMainWindow=lambda: None)
    app.getUserConfigDir = lambda: str(_TMP / "config")
    app.getUserMacroDir = lambda *args: str(_TMP / "macro")
    app.getUserAppDataDir = lambda: str(_TMP / "appdata")
    app.getUserCachePath = lambda: str(_TMP / "cache")
    app.getImportType = lambda ext: []
    app.addImportType = lambda *args: None
    app.addDocumentObserver = lambda *args: None
    app.removeDocumentObserver = lambda *args: None
    app.Qt = types.SimpleNamespace(translate=lambda context, text, *args: text)
    return app


sys.modules["FreeCAD"] = _freecad()

_gui = types.ModuleType("FreeCADGui")
_gui.getMainWindow = lambda: None
_gui.addLanguagePath = lambda *args: None
_gui.addCommand = lambda *args: None
_gui.runCommand = lambda *args: None
sys.modules["FreeCADGui"] = _gui

sys.path.insert(0, str(Path(__file__).parent.parent))

_APP = PySide6.QtWidgets.QApplication.instance() or PySide6.QtWidgets.QApplication([])


@pytest.fixture(autouse=True)
def _clean_parameters() -> None:
    GROUPS.clear()
    yield
    GROUPS.clear()

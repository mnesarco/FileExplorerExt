# SPDX-License-Identifier: LGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Frank David Martínez Muñoz <mnesarco@gmail.com>
# SPDX-FileNotice: Part of the File Explorer addon.

"""Tests for the path helpers behind delete, trash, paste, rename and recents."""

from __future__ import annotations

import types
from pathlib import Path

import pytest

import FreeCAD as App

from freecad.FileExplorerExt import _preferences
from freecad.FileExplorerExt._fclist import FCListImportHandler
from freecad.FileExplorerExt._files import delete_path, path_touches_open_document
from freecad.FileExplorerExt._tree import FileSystemModel, _is_inside


def _doc(filename: Path) -> types.SimpleNamespace:
    return types.SimpleNamespace(Name=filename.stem, FileName=str(filename))


def test_delete_file_and_folder(tmp_path: Path) -> None:
    file = tmp_path / "a.txt"
    file.write_text("a")
    delete_path(str(file))
    assert not file.exists()

    folder = tmp_path / "dir"
    (folder / "nested").mkdir(parents=True)
    delete_path(str(folder))
    assert not folder.exists()


def test_delete_symlink_keeps_the_target(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "keep.txt").write_text("keep")
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)

    delete_path(str(link))

    assert not link.exists()
    assert (target / "keep.txt").exists()


def test_delete_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        delete_path(str(tmp_path / "gone"))


def test_open_document_blocks_its_file_and_its_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened = tmp_path / "proj" / "open.FCStd"
    opened.parent.mkdir()
    opened.write_text("x")
    monkeypatch.setattr(App, "listDocuments", lambda: {"d": _doc(opened)})

    assert path_touches_open_document(opened)
    assert path_touches_open_document(opened.parent)
    assert not path_touches_open_document(tmp_path / "unrelated")


def test_rename_validation(tmp_path: Path) -> None:
    model = FileSystemModel()
    source = tmp_path / "a.txt"
    source.write_text("a")
    (tmp_path / "b.txt").write_text("b")

    assert model._rename_error(source, "") is not None
    assert model._rename_error(source, "..") is not None
    assert model._rename_error(source, "x/y") is not None
    assert model._rename_error(source, "b.txt") is not None
    assert model._rename_error(source, "c.txt") is None


def test_paste_into_own_subtree_is_detected(tmp_path: Path) -> None:
    folder = tmp_path / "a"
    sub = folder / "sub"
    sub.mkdir(parents=True)
    (folder / "f.txt").write_text("x")

    assert _is_inside(sub, folder)
    assert _is_inside(folder, folder)
    assert not _is_inside(tmp_path / "b", folder)


def test_recent_files_roundtrip() -> None:
    _preferences.add_recent_file("/a.FCStd")
    _preferences.add_recent_file("/b.FCStd")
    assert _preferences.get_recent_files() == ["/b.FCStd", "/a.FCStd"]

    _preferences.remove_recent_file("/b.FCStd")
    assert _preferences.get_recent_files() == ["/a.FCStd"]


def test_rename_and_delete_follow_recents() -> None:
    _preferences.add_recent_file("/old/dir/f.FCStd")
    _preferences.add_recent_file("/other/g.FCStd")

    _preferences.rename_recent_path("/old/dir", "/new/dir")
    assert _preferences.get_recent_files() == ["/other/g.FCStd", "/new/dir/f.FCStd"]

    _preferences.remove_recent_subtree("/new/dir")
    assert _preferences.get_recent_files() == ["/other/g.FCStd"]


def test_session_file_is_utf8(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    document = tmp_path / "Ñandú.FCStd"
    document.write_text("x")
    monkeypatch.setattr(App, "listDocuments", lambda: {"d": _doc(document)})

    session = tmp_path / "session.fclist"
    FCListImportHandler.save(str(session))

    assert "Ñandú.FCStd" in session.read_text(encoding="utf-8")

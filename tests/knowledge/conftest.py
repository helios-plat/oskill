"""Fixtures for knowledge skill tests."""
from __future__ import annotations
import os
from pathlib import Path
import pytest
import fitz
from PIL import Image


@pytest.fixture()
def stratum_home(tmp_path, monkeypatch):
    """Monkeypatch STRATUM_HOME to a temp directory."""
    home = tmp_path / "stratum"
    home.mkdir()
    # Patch env and the cfg store
    monkeypatch.setenv("STRATUM_HOME", str(home))
    import oprim._config as _cfg_mod
    _cfg_mod._store["STRATUM_HOME"] = str(home)
    yield home
    # Cleanup
    _cfg_mod._store.pop("STRATUM_HOME", None)


@pytest.fixture()
def simple_pdf(tmp_path):
    path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    for i, line in enumerate([
        "Hello World test PDF content for testing purposes.",
        "Second line: more content here.",
        "Third line: plenty of extractable text.",
        "Fourth line: more text to exceed scanned threshold.",
    ]):
        page.insert_text((50, 50 + i * 20), line)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture()
def simple_txt(tmp_path):
    path = tmp_path / "test.txt"
    path.write_text("Hello world! This is a plain text file.\n" * 10)
    return path


@pytest.fixture()
def simple_md(tmp_path):
    path = tmp_path / "note.md"
    path.write_text("# Test Note\n\nThis is a markdown note with some content.\n\nSecond paragraph here.\n")
    return path


@pytest.fixture()
def simple_html(tmp_path):
    path = tmp_path / "page.html"
    path.write_text(
        "<html><head><title>Test</title></head><body>"
        "<h1>Test Article</h1>"
        "<p>This is a test HTML document with enough content to extract.</p>"
        "<p>Second paragraph for good measure.</p>"
        "</body></html>"
    )
    return path


@pytest.fixture()
def simple_png(tmp_path):
    path = tmp_path / "test.png"
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    img.save(str(path))
    return path


@pytest.fixture()
def screen_png(tmp_path):
    path = tmp_path / "screenshot.png"
    img = Image.new("RGB", (1920, 1080), color=(0, 128, 255))
    img.save(str(path))
    return path

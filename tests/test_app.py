"""Unit tests for the File Drop app.

These tests do not need a database: they stub out list_files() and exercise the
HTML rendering, including the security-critical filename escaping.

Run with:  pytest
"""

import os
import sys

import pytest

# Make the app module importable (app/main.py).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import main  # noqa: E402


@pytest.mark.unit
def test_home_escapes_malicious_filename(monkeypatch):
    """A filename containing HTML must be escaped, not rendered (XSS regression)."""
    monkeypatch.setattr(
        main, "list_files", lambda: [("abc123", "<script>alert(1)</script>", 10)]
    )
    page = main.home()
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


@pytest.mark.unit
def test_home_shows_empty_state(monkeypatch):
    monkeypatch.setattr(main, "list_files", lambda: [])
    page = main.home()
    assert "No files yet" in page


@pytest.mark.unit
def test_home_lists_a_file(monkeypatch):
    monkeypatch.setattr(main, "list_files", lambda: [("xyz789", "report.pdf", 2048)])
    page = main.home()
    assert "report.pdf" in page
    assert "/file/xyz789" in page
    assert "2,048 B" in page

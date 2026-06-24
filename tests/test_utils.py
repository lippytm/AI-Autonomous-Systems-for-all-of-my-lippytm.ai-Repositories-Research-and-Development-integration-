"""
Tests for core utilities.
"""
import pytest

from src.utils.helpers import (
    flatten_findings,
    group_by,
    sha256,
    slugify,
    truncate,
    utc_now,
)


def test_truncate_short_string():
    assert truncate("hello", 10) == "hello"


def test_truncate_long_string():
    result = truncate("hello world", 8)
    assert len(result) == 8
    assert result.endswith("…")


def test_slugify():
    assert slugify("Hello World!") == "hello-world"
    assert slugify("  spaces  ") == "spaces"
    assert slugify("Python 3.10") == "python-310"


def test_utc_now_format():
    ts = utc_now()
    assert "T" in ts
    assert ts.endswith("+00:00")


def test_sha256_deterministic():
    assert sha256("test") == sha256("test")
    assert sha256("a") != sha256("b")


def test_flatten_findings():
    results = [
        {
            "agent": "code_improvement",
            "repository": "owner/repo",
            "findings": [
                {"category": "quality", "description": "fix this", "severity": "info"}
            ],
        },
        {
            "agent": "repository",
            "repository": "owner/repo",
            "findings": [],
        },
    ]
    flat = flatten_findings(results)
    assert len(flat) == 1
    assert flat[0]["agent"] == "code_improvement"
    assert flat[0]["repository"] == "owner/repo"


def test_group_by():
    items = [
        {"type": "a", "value": 1},
        {"type": "b", "value": 2},
        {"type": "a", "value": 3},
    ]
    grouped = group_by(items, "type")
    assert len(grouped["a"]) == 2
    assert len(grouped["b"]) == 1

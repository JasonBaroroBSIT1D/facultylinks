"""Unit tests for database isolation guard (no DB connection)."""

from __future__ import annotations

import os

import pytest

from app.test_db_guard import assert_test_database_isolated, database_identity, fingerprint


def test_fingerprint_differs_for_different_db_names():
    host = "db.example.com"
    a = f"postgresql://user:pass@{host}:5432/facultylinks"
    b = f"postgresql://user:pass@{host}:5432/facultylinks_test"
    assert fingerprint(a) != fingerprint(b)


def test_rejects_production_database_name(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TEST_DATABASE_NAME", "facultylinks_test")
    with pytest.raises(RuntimeError, match="facultylinks"):
        assert_test_database_isolated("postgresql://h:5432/facultylinks")
    assert_test_database_isolated("postgresql://h:5432/facultylinks_test")


def test_rejects_same_host_and_db_as_production(monkeypatch):
    monkeypatch.setenv("TEST_DATABASE_NAME", "facultylinks_test")
    prod = "postgresql://pooler.example.com:5432/facultylinks_test"
    monkeypatch.setenv("DATABASE_URL", prod)
    with pytest.raises(RuntimeError, match="same host"):
        assert_test_database_isolated(prod)
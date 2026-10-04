"""Shared pytest fixtures."""

import os
import sys

import pytest

# Make the project root importable when pytest runs from any directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402


@pytest.fixture
def app(tmp_path):
    """A fresh application backed by an isolated, temporary database."""
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_client(client):
    """Create a client through the API and return its JSON representation."""
    def _make_client(name="Arjun", **fields):
        response = client.post("/api/clients", json={"name": name, **fields})
        assert response.status_code == 201, response.get_json()
        return response.get_json()
    return _make_client

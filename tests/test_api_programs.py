"""Tests for the program and calorie API endpoints."""

import pytest


def test_list_programs(client):
    response = client.get("/api/programs")
    assert response.status_code == 200
    assert {p["code"] for p in response.get_json()} == {"FL", "MG", "BG"}


@pytest.mark.parametrize("code", ["FL", "mg", "BG"])
def test_get_program(client, code):
    response = client.get(f"/api/programs/{code}")
    assert response.status_code == 200
    assert response.get_json()["code"] == code.upper()


def test_get_unknown_program_returns_404(client):
    response = client.get("/api/programs/XYZ")
    assert response.status_code == 404
    assert "not found" in response.get_json()["error"]


def test_calories(client):
    response = client.post("/api/calories", json={"weight": 70, "program": "FL"})
    assert response.status_code == 200
    assert response.get_json() == {"program": "FL", "weight": 70.0, "calories": 1540}


@pytest.mark.parametrize("payload", [
    {"program": "FL"},
    {"weight": 70},
    {"weight": -5, "program": "FL"},
    {"weight": 70, "program": "NOPE"},
])
def test_calories_validation_errors(client, payload):
    response = client.post("/api/calories", json=payload)
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_calories_rejects_non_json_body(client):
    response = client.post("/api/calories", data="weight=70",
                           content_type="text/plain")
    assert response.status_code == 400
    assert response.get_json()["error"] == "Request body must be a JSON object"

"""Tests for client management, progress logging and CSV export."""

import csv
import io

import pytest

import models


class TestCreateClient:
    def test_create_with_full_profile(self, client):
        payload = {"name": "Arjun", "age": 28, "height": 175, "weight": 80,
                   "program": "fl", "target_weight": 72, "target_adherence": 90,
                   "membership_end": "2026-12-31"}
        response = client.post("/api/clients", json=payload)
        assert response.status_code == 201
        body = response.get_json()
        assert body["program"] == "FL"
        assert body["calories"] == 1760  # 80 kg x 22
        assert body["membership_status"] == "Active"
        assert body["membership_end"] == "2026-12-31"
        assert body["id"] > 0

    def test_create_minimal_has_no_calories(self, make_client):
        body = make_client("Meena")
        assert body["calories"] is None and body["program"] is None

    def test_duplicate_name_is_conflict(self, client, make_client):
        make_client("Arjun")
        response = client.post("/api/clients", json={"name": "arjun"})
        assert response.status_code == 409
        assert "already exists" in response.get_json()["error"]

    @pytest.mark.parametrize("payload, message", [
        ({}, "'name' is required"),
        ({"name": "  "}, "'name' is required"),
        ({"name": "A", "age": 0}, "'age' must be at least 1"),
        ({"name": "A", "age": 30.5}, "whole number"),
        ({"name": "A", "weight": -70}, "'weight' must be greater than 0"),
        ({"name": "A", "height": "tall"}, "'height' must be a number"),
        ({"name": "A", "target_adherence": 120}, "at most 100"),
        ({"name": "A", "program": "Yoga"}, "Unknown program"),
        ({"name": "A", "membership_status": "Gold"}, "membership_status"),
        ({"name": "A", "membership_end": "31/12/2026"}, "YYYY-MM-DD"),
    ])
    def test_validation_errors(self, client, payload, message):
        response = client.post("/api/clients", json=payload)
        assert response.status_code == 400
        assert message in response.get_json()["error"]

    def test_membership_status_is_normalised(self, make_client):
        assert make_client("Ravi", membership_status="inactive")["membership_status"] == "Inactive"


class TestReadUpdateDeleteClient:
    def test_list_clients_sorted_by_name(self, client, make_client):
        for name in ("Zara", "Arjun", "Meena"):
            make_client(name)
        names = [c["name"] for c in client.get("/api/clients").get_json()]
        assert names == ["Arjun", "Meena", "Zara"]

    def test_get_client_is_case_insensitive(self, client, make_client):
        make_client("Arjun")
        response = client.get("/api/clients/ARJUN")
        assert response.status_code == 200
        assert response.get_json()["name"] == "Arjun"

    def test_get_missing_client_is_404(self, client):
        response = client.get("/api/clients/Ghost")
        assert response.status_code == 404
        assert response.get_json()["error"] == "Client 'Ghost' not found"

    def test_patch_recalculates_calories(self, client, make_client):
        make_client("Arjun", weight=80, program="FL")
        response = client.patch("/api/clients/Arjun", json={"program": "MG"})
        assert response.status_code == 200
        assert response.get_json()["calories"] == 2800  # 80 kg x 35

    def test_patch_clearing_weight_clears_calories(self, client, make_client):
        make_client("Arjun", weight=80, program="FL")
        body = client.patch("/api/clients/Arjun", json={"weight": None}).get_json()
        assert body["weight"] is None and body["calories"] is None

    def test_patch_keeps_unspecified_fields(self, client, make_client):
        make_client("Arjun", age=28, weight=80)
        body = client.patch("/api/clients/Arjun", json={"age": 29}).get_json()
        assert body["age"] == 29 and body["weight"] == 80

    def test_patch_with_same_name_is_allowed(self, client, make_client):
        make_client("Arjun")
        response = client.patch("/api/clients/Arjun", json={"name": "arjun", "age": 30})
        assert response.status_code == 200

    def test_patch_cannot_rename(self, client, make_client):
        make_client("Arjun")
        response = client.patch("/api/clients/Arjun", json={"name": "Bob"})
        assert response.status_code == 400

    def test_patch_missing_client_is_404(self, client):
        assert client.patch("/api/clients/Ghost", json={"age": 30}).status_code == 404

    def test_patch_invalid_value(self, client, make_client):
        make_client("Arjun")
        assert client.patch("/api/clients/Arjun", json={"weight": 0}).status_code == 400

    def test_patch_program_can_be_cleared(self, client, make_client):
        make_client("Arjun", weight=80, program="FL")
        body = client.patch("/api/clients/Arjun", json={"program": ""}).get_json()
        assert body["program"] is None and body["calories"] is None

    def test_delete_client(self, client, make_client):
        make_client("Arjun")
        assert client.delete("/api/clients/Arjun").status_code == 204
        assert client.get("/api/clients/Arjun").status_code == 404

    def test_delete_missing_client_is_404(self, client):
        assert client.delete("/api/clients/Ghost").status_code == 404


class TestProgress:
    def test_log_and_summarise_progress(self, client, make_client):
        make_client("Arjun")
        for week, adherence in (("Week 01 - 2026", 80), ("Week 02 - 2026", 90)):
            response = client.post("/api/clients/Arjun/progress",
                                   json={"week": week, "adherence": adherence})
            assert response.status_code == 201
        body = client.get("/api/clients/Arjun/progress").get_json()
        assert body["client"] == "Arjun"
        assert body["weeks_logged"] == 2
        assert body["average_adherence"] == 85.0
        assert [e["week"] for e in body["entries"]] == ["Week 01 - 2026", "Week 02 - 2026"]

    def test_week_defaults_to_current_week(self, client, make_client):
        make_client("Arjun")
        body = client.post("/api/clients/Arjun/progress", json={"adherence": 70}).get_json()
        assert body["week"].startswith("Week ")

    def test_empty_progress(self, client, make_client):
        make_client("Arjun")
        body = client.get("/api/clients/Arjun/progress").get_json()
        assert body["weeks_logged"] == 0 and body["entries"] == []

    @pytest.mark.parametrize("payload", [{}, {"adherence": 101}, {"adherence": -1},
                                         {"adherence": "high"}])
    def test_invalid_adherence(self, client, make_client, payload):
        make_client("Arjun")
        assert client.post("/api/clients/Arjun/progress", json=payload).status_code == 400

    def test_progress_for_missing_client_is_404(self, client):
        assert client.post("/api/clients/Ghost/progress",
                           json={"adherence": 50}).status_code == 404
        assert client.get("/api/clients/Ghost/progress").status_code == 404

    def test_deleting_client_removes_progress(self, app, client, make_client):
        client_id = make_client("Arjun")["id"]
        client.post("/api/clients/Arjun/progress", json={"adherence": 50})
        client.delete("/api/clients/Arjun")
        with app.app_context():
            assert models.list_progress(client_id) == []


def test_export_clients_csv(client, make_client):
    make_client("Arjun", age=28, weight=80, program="FL")
    make_client("Meena")
    response = client.get("/api/export/clients.csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]
    rows = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))
    assert [r["name"] for r in rows] == ["Arjun", "Meena"]
    assert rows[0]["calories"] == "1760"
    assert list(rows[0]) == list(models.CLIENT_COLUMNS)


def test_models_reject_unknown_columns(app):
    with app.app_context(), pytest.raises(ValueError, match="Unknown client columns"):
        models.create_client({"name": "X", "drop table": 1})

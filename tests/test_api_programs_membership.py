"""Tests for the program generator and membership endpoints."""

from datetime import date

import pytest

import fitness


class TestGenerateProgram:
    def test_generate_without_client(self, client):
        response = client.post("/api/programs/generate",
                               json={"experience": "beginner", "program": "MG", "seed": 5})
        assert response.status_code == 200
        body = response.get_json()
        assert body["focus"] == "Hypertrophy" and body["program"] == "MG"
        assert len(body["plan"]) == 9
        assert body == client.post("/api/programs/generate",
                                   json={"experience": "beginner", "program": "MG",
                                         "seed": 5}).get_json()

    def test_generate_uses_client_program(self, client, make_client):
        make_client("Arjun", program="FL")
        response = client.post("/api/clients/Arjun/generate-program",
                               json={"experience": "advanced"})
        assert response.status_code == 200
        body = response.get_json()
        assert body["client"] == "Arjun"
        assert body["focus"] == "Conditioning"
        assert body["days_per_week"] == 5

    def test_generate_for_client_without_program(self, client, make_client):
        make_client("Meena")
        body = client.post("/api/clients/Meena/generate-program",
                           json={"experience": "beginner"}).get_json()
        assert body["focus"] == "Full Body" and body["program"] is None

    @pytest.mark.parametrize("payload", [{}, {"experience": "pro"},
                                         {"experience": "beginner", "seed": "abc"},
                                         {"experience": "beginner", "program": "Yoga"}])
    def test_generate_validation(self, client, payload):
        assert client.post("/api/programs/generate", json=payload).status_code == 400

    def test_generate_for_missing_client(self, client):
        assert client.post("/api/clients/Ghost/generate-program",
                           json={"experience": "beginner"}).status_code == 404


class TestMembershipEndpoints:
    def test_membership_status(self, client, make_client):
        end = fitness.add_months(date.today(), 2).isoformat()
        make_client("Arjun", membership_end=end)
        body = client.get("/api/clients/Arjun/membership").get_json()
        assert body["client"] == "Arjun"
        assert body["effective_status"] == "Active"
        assert body["membership_end"] == end
        assert body["renewal_due"] is False

    def test_expired_membership(self, client, make_client):
        make_client("Arjun", membership_end="2020-01-01")
        body = client.get("/api/clients/Arjun/membership").get_json()
        assert body["effective_status"] == "Expired" and body["renewal_due"]

    def test_renew_reactivates_and_extends(self, client, make_client):
        make_client("Arjun", membership_status="Inactive", membership_end="2020-01-01")
        response = client.post("/api/clients/Arjun/membership/renew", json={"months": 6})
        assert response.status_code == 200
        body = response.get_json()
        assert body["status"] == "Active" and body["is_active"]
        assert body["membership_end"] == fitness.add_months(date.today(), 6).isoformat()
        assert client.get("/api/clients/Arjun").get_json()["membership_end"] == \
            body["membership_end"]

    @pytest.mark.parametrize("payload", [{}, {"months": 0}, {"months": 36}])
    def test_renew_validation(self, client, make_client, payload):
        make_client("Arjun")
        response = client.post("/api/clients/Arjun/membership/renew", json=payload)
        assert response.status_code == 400

    def test_membership_for_missing_client(self, client):
        assert client.get("/api/clients/Ghost/membership").status_code == 404
        assert client.post("/api/clients/Ghost/membership/renew",
                           json={"months": 1}).status_code == 404

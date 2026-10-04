"""Tests for BMI, workout logging, body metrics and the client summary."""

from datetime import date

import pytest

from database import get_db


class TestBmiEndpoints:
    def test_bmi(self, client):
        response = client.post("/api/bmi", json={"height": 175, "weight": 70})
        assert response.status_code == 200
        assert response.get_json()["bmi"] == 22.9

    @pytest.mark.parametrize("payload", [{}, {"height": 175}, {"height": 0, "weight": 70}])
    def test_bmi_validation(self, client, payload):
        assert client.post("/api/bmi", json=payload).status_code == 400

    def test_client_bmi(self, client, make_client):
        make_client("Arjun", height=180, weight=81)
        body = client.get("/api/clients/Arjun/bmi").get_json()
        assert body == {"client": "Arjun", "bmi": 25.0, "category": "Overweight",
                        "risk": body["risk"]}

    def test_client_bmi_requires_height_and_weight(self, client, make_client):
        make_client("Arjun", weight=80)
        response = client.get("/api/clients/Arjun/bmi")
        assert response.status_code == 400
        assert "height and weight" in response.get_json()["error"]


class TestWorkouts:
    def test_log_workout_with_exercises(self, client, make_client):
        make_client("Arjun")
        payload = {"date": "2026-03-02", "workout_type": "strength", "duration_min": 75,
                   "notes": "Felt strong",
                   "exercises": [{"name": "Back Squat", "sets": 5, "reps": 5, "weight": 100},
                                 {"name": "Plank", "sets": 3, "reps": 1}]}
        response = client.post("/api/clients/Arjun/workouts", json=payload)
        assert response.status_code == 201
        body = response.get_json()
        assert body["workout_type"] == "Strength"
        assert body["duration_min"] == 75
        assert body["exercises"] == [
            {"name": "Back Squat", "sets": 5, "reps": 5, "weight": 100.0},
            {"name": "Plank", "sets": 3, "reps": 1, "weight": 0.0},
        ]

    def test_workout_defaults(self, client, make_client):
        make_client("Arjun")
        body = client.post("/api/clients/Arjun/workouts",
                           json={"workout_type": "Mobility"}).get_json()
        assert body["date"] == date.today().isoformat()
        assert body["duration_min"] == 60
        assert body["notes"] is None and body["exercises"] == []

    def test_workouts_listed_newest_first(self, client, make_client):
        make_client("Arjun")
        for day in ("2026-03-01", "2026-03-05", "2026-03-03"):
            client.post("/api/clients/Arjun/workouts",
                        json={"date": day, "workout_type": "Cardio"})
        body = client.get("/api/clients/Arjun/workouts").get_json()
        assert [w["date"] for w in body["workouts"]] == ["2026-03-05", "2026-03-03", "2026-03-01"]

    @pytest.mark.parametrize("payload, message", [
        ({}, "'workout_type' is required"),
        ({"workout_type": "Dancing"}, "must be one of"),
        ({"workout_type": "Strength", "duration_min": 0}, "at least 1"),
        ({"workout_type": "Strength", "date": "yesterday"}, "YYYY-MM-DD"),
        ({"workout_type": "Strength", "exercises": "squats"}, "must be a list"),
        ({"workout_type": "Strength", "exercises": ["squats"]}, "exercises[0] must be an object"),
        ({"workout_type": "Strength", "exercises": [{"name": "Squat", "sets": 0, "reps": 5}]},
         "exercises[0]: 'sets' must be at least 1"),
        ({"workout_type": "Strength", "exercises": [{"sets": 3, "reps": 5}]},
         "exercises[0]: 'name' is required"),
    ])
    def test_workout_validation(self, client, make_client, payload, message):
        make_client("Arjun")
        response = client.post("/api/clients/Arjun/workouts", json=payload)
        assert response.status_code == 400
        assert message in response.get_json()["error"]

    def test_invalid_exercise_does_not_save_workout(self, client, make_client):
        make_client("Arjun")
        client.post("/api/clients/Arjun/workouts", json={
            "workout_type": "Strength",
            "exercises": [{"name": "Squat", "sets": 3, "reps": 5}, {"name": "Bad"}]})
        assert client.get("/api/clients/Arjun/workouts").get_json()["workouts"] == []

    def test_workouts_for_missing_client(self, client):
        assert client.get("/api/clients/Ghost/workouts").status_code == 404
        assert client.post("/api/clients/Ghost/workouts",
                           json={"workout_type": "Strength"}).status_code == 404


class TestMetrics:
    def test_log_metrics_updates_profile_weight(self, client, make_client):
        make_client("Arjun", weight=80, program="FL")
        response = client.post("/api/clients/Arjun/metrics",
                               json={"date": "2026-03-04", "weight": 78.5, "waist": 84,
                                     "bodyfat": 18})
        assert response.status_code == 201
        assert response.get_json()["weight"] == 78.5
        profile = client.get("/api/clients/Arjun").get_json()
        assert profile["weight"] == 78.5
        assert profile["calories"] == 1727  # int(78.5 x 22)

    def test_metrics_without_weight_keep_profile(self, client, make_client):
        make_client("Arjun", weight=80)
        client.post("/api/clients/Arjun/metrics", json={"waist": 84})
        assert client.get("/api/clients/Arjun").get_json()["weight"] == 80

    def test_metrics_listed_chronologically(self, client, make_client):
        make_client("Arjun")
        for day, weight in (("2026-03-10", 79), ("2026-03-01", 80)):
            client.post("/api/clients/Arjun/metrics", json={"date": day, "weight": weight})
        body = client.get("/api/clients/Arjun/metrics").get_json()
        assert [m["date"] for m in body["metrics"]] == ["2026-03-01", "2026-03-10"]

    @pytest.mark.parametrize("payload", [{}, {"date": "2026-03-01"}, {"weight": -1},
                                         {"bodyfat": 90}])
    def test_metrics_validation(self, client, make_client, payload):
        make_client("Arjun")
        assert client.post("/api/clients/Arjun/metrics", json=payload).status_code == 400

    def test_metrics_for_missing_client(self, client):
        assert client.get("/api/clients/Ghost/metrics").status_code == 404


class TestSummary:
    def test_full_summary(self, client, make_client):
        make_client("Arjun", age=28, height=175, weight=85, program="FL",
                    target_weight=75, target_adherence=80)
        for adherence in (70, 90, 95):
            client.post("/api/clients/Arjun/progress", json={"adherence": adherence})
        client.post("/api/clients/Arjun/workouts", json={"workout_type": "Strength"})
        client.post("/api/clients/Arjun/metrics",
                    json={"date": "2026-03-04", "weight": 84, "waist": 90})

        body = client.get("/api/clients/Arjun/summary").get_json()
        assert body["profile"]["name"] == "Arjun"
        assert body["program"]["code"] == "FL"
        assert body["progress"] == {"weeks_logged": 3, "average_adherence": 85.0}
        assert body["goals"]["weight_to_target"] == 9.0
        assert body["goals"]["adherence_on_track"] is True
        assert body["workouts_logged"] == 1
        assert body["last_metrics"]["weight"] == 84
        assert body["bmi"]["category"] == "Overweight"

    def test_minimal_summary(self, client, make_client):
        make_client("Meena", target_adherence=90)
        body = client.get("/api/clients/Meena/summary").get_json()
        assert body["program"] is None
        assert body["bmi"] is None
        assert body["last_metrics"] is None
        assert body["goals"]["weight_to_target"] is None
        assert body["goals"]["adherence_on_track"] is None  # nothing logged yet

    def test_adherence_off_track(self, client, make_client):
        make_client("Meena", target_adherence=90)
        client.post("/api/clients/Meena/progress", json={"adherence": 60})
        body = client.get("/api/clients/Meena/summary").get_json()
        assert body["goals"]["adherence_on_track"] is False

    def test_summary_for_missing_client(self, client):
        assert client.get("/api/clients/Ghost/summary").status_code == 404


def test_deleting_client_cascades_to_tracking_data(app, client, make_client):
    make_client("Arjun")
    client.post("/api/clients/Arjun/workouts",
                json={"workout_type": "Strength",
                      "exercises": [{"name": "Squat", "sets": 3, "reps": 5}]})
    client.post("/api/clients/Arjun/metrics", json={"weight": 80})
    client.delete("/api/clients/Arjun")
    with app.app_context():
        db = get_db()
        for table in ("workouts", "exercises", "metrics"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0

"""Tests for application-level routes and error handling."""

from app import __version__, create_app


def test_create_app_applies_test_config(tmp_path):
    db_path = tmp_path / "nested" / "config.db"
    app = create_app({"TESTING": True, "DATABASE": str(db_path)})
    assert app.testing
    assert db_path.exists()  # schema is created on start-up


def test_database_path_from_environment(monkeypatch, tmp_path):
    db_path = tmp_path / "env.db"
    monkeypatch.setenv("ACEEST_DATABASE", str(db_path))
    assert create_app().config["DATABASE"] == str(db_path)


def test_init_db_command(app):
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert "Initialised the database." in result.output


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "service": "aceest-fitness",
                                   "version": __version__}


def test_index_renders_programs(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "ACEest FUNCTIONAL FITNESS" in html
    for name in ("Fat Loss (FL)", "Muscle Gain (MG)", "Beginner (BG)"):
        assert name in html


def test_index_lists_clients(client, make_client):
    make_client("Priya", program="MG")
    html = client.get("/").get_data(as_text=True)
    assert "Priya" in html and "No clients yet" not in html


def test_index_without_clients(client):
    assert "No clients yet" in client.get("/").get_data(as_text=True)


def test_unknown_route_returns_json_404(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_wrong_method_returns_json_405(client):
    response = client.get("/api/calories")
    assert response.status_code == 405
    assert "error" in response.get_json()

"""Tests for application-level routes and error handling."""

from app import __version__, create_app


def test_create_app_applies_test_config():
    app = create_app({"TESTING": True})
    assert app.testing


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


def test_unknown_route_returns_json_404(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_wrong_method_returns_json_405(client):
    response = client.get("/api/calories")
    assert response.status_code == 405
    assert "error" in response.get_json()

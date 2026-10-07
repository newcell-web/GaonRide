import pytest
import datetime
from backend.config import AI_AVAILABLE


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "ai_available" in data
    assert "db_ok" in data
    assert data["db_ok"] is True


def test_health_ai_available_matches_config(client):
    response = client.get("/api/health")
    data = response.json()
    assert data["ai_available"] == AI_AVAILABLE


def test_create_ride_request(client):
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    payload = {
        "passenger_name": "Test User",
        "origin": "Gerua",
        "destination": "Rangia",
        "travel_date": tomorrow,
        "preferred_time": "09:00",
        "passenger_count": 1,
        "language": "en"
    }
    response = client.post("/api/requests/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["passenger_name"] == "Test User"
    assert data["status"] in ("grouped", "pending")
    assert "id" in data


def test_create_request_creates_group(client):
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    payload = {
        "passenger_name": "User One",
        "origin": "Gerua",
        "destination": "Rangia",
        "travel_date": tomorrow,
        "preferred_time": "09:00",
        "passenger_count": 1,
    }
    r = client.post("/api/requests/", json=payload)
    assert r.status_code == 201
    request_data = r.json()
    assert request_data.get("group_id") is not None


def test_get_groups(client):
    response = client.get("/api/groups/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_seed_and_get_groups(client):
    # Seed demo data (trailing slash matches the router route)
    seed_response = client.post("/api/seed/")
    assert seed_response.status_code == 200

    # Should now have groups
    groups_response = client.get("/api/groups/")
    assert groups_response.status_code == 200
    groups = groups_response.json()
    assert len(groups) > 0


def test_seed_delete_clears_demo_data(client):
    # Seed first
    client.post("/api/seed/")

    # Delete demo data
    delete_response = client.delete("/api/seed/")
    assert delete_response.status_code == 200

    # Groups should be empty now
    groups = client.get("/api/groups/").json()
    assert len(groups) == 0


def test_voice_transcribe_without_key_returns_503(client):
    # If AI is not available, expect 503
    if AI_AVAILABLE:
        pytest.skip("Groq key is configured; skipping no-key test")

    import io
    fake_audio = io.BytesIO(b"fake audio data")
    response = client.post(
        "/api/voice/transcribe",
        files={"file": ("test.webm", fake_audio, "audio/webm")}
    )
    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"] or "Groq" in response.json()["detail"]


def test_voice_parse_without_key_returns_503(client):
    if AI_AVAILABLE:
        pytest.skip("Groq key is configured; skipping no-key test")

    response = client.post("/api/voice/parse", json={"text": "go from Gerua to Rangia tomorrow morning"})
    assert response.status_code == 503


def test_unknown_api_route_returns_404(client):
    response = client.get("/api/nonexistent-route-xyz")
    assert response.status_code == 404

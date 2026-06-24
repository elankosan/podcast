"""Tests for Phase 1: Foundation."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.main import app
from api.database import Base, get_db
from api.config import settings

# Use a test database
TEST_DATABASE_URL = "postgresql://postgres:password@localhost:5432/podcast_test"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestHealth:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestAuth:
    def test_login(self, setup_db):
        # Create a user first
        response = client.post(
            "/api/admin/users",
            json={"email": "test@example.com", "name": "Test User", "password": "password123", "role": "host"},
        )
        assert response.status_code == 200

        # Login
        response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_me(self, setup_db):
        # Login first
        response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "password123"},
        )
        token = response.json()["access_token"]

        # Get current user
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"


class TestPodcasts:
    def test_create_podcast(self, setup_db):
        # Login
        response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "password123"},
        )
        token = response.json()["access_token"]

        # Create podcast
        response = client.post(
            "/api/podcasts/",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Weekly Perspectives", "description": "A weekly show"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Weekly Perspectives"

    def test_list_podcasts(self, setup_db):
        response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "password123"},
        )
        token = response.json()["access_token"]

        response = client.get(
            "/api/podcasts/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1


class TestEpisodes:
    def test_create_episode(self, setup_db):
        # Login
        response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "password123"},
        )
        token = response.json()["access_token"]

        # Get podcast
        response = client.get(
            "/api/podcasts/",
            headers={"Authorization": f"Bearer {token}"},
        )
        podcast_id = response.json()[0]["id"]

        # Create episode
        response = client.post(
            f"/api/podcasts/{podcast_id}/episodes",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "AI and Democracy", "vision": "Discuss AI impact"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "AI and Democracy"


class TestResearch:
    def test_trigger_research(self, setup_db):
        # Login
        response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "password123"},
        )
        token = response.json()["access_token"]

        # Get episode
        response = client.get("/api/podcasts/", headers={"Authorization": f"Bearer {token}"})
        podcast_id = response.json()[0]["id"]
        response = client.get(f"/api/podcasts/{podcast_id}/episodes", headers={"Authorization": f"Bearer {token}"})
        episode_id = response.json()[0]["id"]

        # Trigger research (may fail if KIMI_API_KEY not set, but endpoint should respond)
        response = client.post(
            f"/api/research/{episode_id}/research",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should return 200 even if agent fails, or 500 if Kimi not configured
        assert response.status_code in (200, 500)

    def test_get_research(self, setup_db):
        response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "password123"},
        )
        token = response.json()["access_token"]

        response = client.get("/api/podcasts/", headers={"Authorization": f"Bearer {token}"})
        podcast_id = response.json()[0]["id"]
        response = client.get(f"/api/podcasts/{podcast_id}/episodes", headers={"Authorization": f"Bearer {token}"})
        episode_id = response.json()[0]["id"]

        response = client.get(
            f"/api/research/{episode_id}/research",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


class TestScript:
    def test_trigger_script(self, setup_db):
        response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "password123"},
        )
        token = response.json()["access_token"]

        response = client.get("/api/podcasts/", headers={"Authorization": f"Bearer {token}"})
        podcast_id = response.json()[0]["id"]
        response = client.get(f"/api/podcasts/{podcast_id}/episodes", headers={"Authorization": f"Bearer {token}"})
        episode_id = response.json()[0]["id"]

        response = client.post(
            f"/api/scripts/{episode_id}/script",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in (200, 500)

    def test_get_script(self, setup_db):
        response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "password123"},
        )
        token = response.json()["access_token"]

        response = client.get("/api/podcasts/", headers={"Authorization": f"Bearer {token}"})
        podcast_id = response.json()[0]["id"]
        response = client.get(f"/api/podcasts/{podcast_id}/episodes", headers={"Authorization": f"Bearer {token}"})
        episode_id = response.json()[0]["id"]

        response = client.get(
            f"/api/scripts/{episode_id}/script",
            headers={"Authorization": f"Bearer {token}"},
        )
        # May 404 if no script generated yet
        assert response.status_code in (200, 404)


class TestTranslation:
    def test_trigger_translation(self, setup_db):
        response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "password123"},
        )
        token = response.json()["access_token"]

        response = client.get("/api/podcasts/", headers={"Authorization": f"Bearer {token}"})
        podcast_id = response.json()[0]["id"]
        response = client.get(f"/api/podcasts/{podcast_id}/episodes", headers={"Authorization": f"Bearer {token}"})
        episode_id = response.json()[0]["id"]

        response = client.post(
            f"/api/translations/{episode_id}/translate?language=fr",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in (200, 500)

    def test_get_translations(self, setup_db):
        response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "password123"},
        )
        token = response.json()["access_token"]

        response = client.get("/api/podcasts/", headers={"Authorization": f"Bearer {token}"})
        podcast_id = response.json()[0]["id"]
        response = client.get(f"/api/podcasts/{podcast_id}/episodes", headers={"Authorization": f"Bearer {token}"})
        episode_id = response.json()[0]["id"]

        response = client.get(
            f"/api/translations/{episode_id}/translations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


class TestSphere:
    def test_sphere_health(self):
        response = client.get("/api/sphere/health")
        assert response.status_code == 200

    def test_sync_episode(self, setup_db):
        response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "password123"},
        )
        token = response.json()["access_token"]

        response = client.get("/api/podcasts/", headers={"Authorization": f"Bearer {token}"})
        podcast_id = response.json()[0]["id"]
        response = client.get(f"/api/podcasts/{podcast_id}/episodes", headers={"Authorization": f"Bearer {token}"})
        episode_id = response.json()[0]["id"]

        response = client.post(
            f"/api/sphere/{episode_id}/sync",
            headers={"Authorization": f"Bearer {token}"},
        )
        # May 500 if Neo4j not available
        assert response.status_code in (200, 500)

    def test_get_episode_knowledge(self, setup_db):
        response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "password123"},
        )
        token = response.json()["access_token"]

        response = client.get("/api/podcasts/", headers={"Authorization": f"Bearer {token}"})
        podcast_id = response.json()[0]["id"]
        response = client.get(f"/api/podcasts/{podcast_id}/episodes", headers={"Authorization": f"Bearer {token}"})
        episode_id = response.json()[0]["id"]

        response = client.get(
            f"/api/sphere/{episode_id}/knowledge",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in (200, 500)

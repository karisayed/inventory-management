"""
Tests for task API endpoints.
"""
import pytest

import main


@pytest.fixture(autouse=True)
def reset_tasks():
    """Tasks live in module-level state, so reset around every test."""
    main.tasks.clear()
    main.next_task_id = main.FIRST_TASK_ID
    yield
    main.tasks.clear()
    main.next_task_id = main.FIRST_TASK_ID


PAYLOAD = {"title": "Check stock", "priority": "high", "dueDate": "2025-10-08"}


class TestTasksEndpoints:
    """Test suite for task endpoints."""

    def test_get_tasks_empty(self, client):
        """Test listing tasks when none exist."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_task(self, client):
        """Test creating a task returns a pending task with an id."""
        response = client.post("/api/tasks", json=PAYLOAD)
        assert response.status_code == 200

        task = response.json()
        assert isinstance(task["id"], int)
        assert task["id"] > 4  # must not collide with mock task ids
        assert task["title"] == "Check stock"
        assert task["priority"] == "high"
        assert task["dueDate"] == "2025-10-08"
        assert task["status"] == "pending"

    def test_create_task_default_priority(self, client):
        """Test priority defaults to medium."""
        response = client.post("/api/tasks", json={"title": "x", "dueDate": "2025-10-08"})
        assert response.status_code == 200
        assert response.json()["priority"] == "medium"

    def test_create_task_invalid_payload(self, client):
        """Test missing fields and bad priority are rejected."""
        assert client.post("/api/tasks", json={"title": "x"}).status_code == 422
        bad = {**PAYLOAD, "priority": "urgent"}
        assert client.post("/api/tasks", json=bad).status_code == 422

    def test_get_tasks_newest_first(self, client):
        """Test listing returns created tasks, newest first."""
        first = client.post("/api/tasks", json=PAYLOAD).json()
        second = client.post("/api/tasks", json={**PAYLOAD, "title": "Second"}).json()

        data = client.get("/api/tasks").json()
        assert [t["id"] for t in data] == [second["id"], first["id"]]

    def test_toggle_task(self, client):
        """Test toggling flips status back and forth."""
        task_id = client.post("/api/tasks", json=PAYLOAD).json()["id"]

        response = client.patch(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        assert response.json()["id"] == task_id

        response = client.patch(f"/api/tasks/{task_id}")
        assert response.json()["status"] == "pending"

    def test_toggle_persists(self, client):
        """Test toggled status is visible in the list."""
        task_id = client.post("/api/tasks", json=PAYLOAD).json()["id"]
        client.patch(f"/api/tasks/{task_id}")
        assert client.get("/api/tasks").json()[0]["status"] == "completed"

    def test_delete_task(self, client):
        """Test deleting removes only that task."""
        keep = client.post("/api/tasks", json=PAYLOAD).json()["id"]
        gone = client.post("/api/tasks", json=PAYLOAD).json()["id"]

        response = client.delete(f"/api/tasks/{gone}")
        assert response.status_code == 200

        ids = [t["id"] for t in client.get("/api/tasks").json()]
        assert ids == [keep]

    def test_ids_not_reused_after_delete(self, client):
        """Test ids stay unique after deleting the newest task."""
        a = client.post("/api/tasks", json=PAYLOAD).json()["id"]
        client.delete(f"/api/tasks/{a}")
        b = client.post("/api/tasks", json=PAYLOAD).json()["id"]
        assert a != b

    def test_toggle_nonexistent_task(self, client):
        """Test toggling an unknown id returns 404."""
        response = client.patch("/api/tasks/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_nonexistent_task(self, client):
        """Test deleting an unknown id returns 404."""
        response = client.delete("/api/tasks/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

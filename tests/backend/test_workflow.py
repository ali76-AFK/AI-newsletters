from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_workflow_zero_subscribers():
    # Ensure no subscribers
    resp = client.get("/api/subscribers")
    assert resp.status_code == 200
    data = resp.json()
    for s in data.get("subscribers", []):
        # mark all as inactive for this test
        client.post(
            "/api/subscribers/unsubscribe",
            json={"email": s["email"]},
        )

    # Create a newsletter
    payload = {
        "title": "Zero Sub Test",
        "topic": "ai_news",
        "body": "Body",
    }
    resp = client.post("/api/newsletters", json=payload)
    assert resp.status_code == 201
    newsletter_id = resp.json()["id"]

    # Running workflow should return 400 due to no active subscribers
    resp = client.post(f"/api/workflows/newsletter/{newsletter_id}/run")
    assert resp.status_code == 400
    assert "No active subscribers" in resp.json()["detail"]


def test_workflow_success_and_idempotent():
    # Subscribe a user
    client.post(
        "/api/subscribers",
        json={
            "email": "workflow-test@example.com",
            "name": "Workflow Test",
            "topics": ["ai_news"],
        },
    )

    # Create a newsletter
    payload = {
        "title": "Workflow Test Newsletter",
        "topic": "ai_news",
        "body": "Body",
    }
    resp = client.post("/api/newsletters", json=payload)
    assert resp.status_code == 201
    newsletter_id = resp.json()["id"]

    # First run
    resp = client.post(f"/api/workflows/newsletter/{newsletter_id}/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"]["subscriber_count"] == 1
    assert data["result"]["created_drafts"] == 1

    # Second run should not create additional drafts for same subscriber
    resp = client.post(f"/api/workflows/newsletter/{newsletter_id}/run")
    assert resp.status_code == 200
    data2 = resp.json()
    assert data2["result"]["subscriber_count"] == 1
    assert data2["result"]["created_drafts"] == 1

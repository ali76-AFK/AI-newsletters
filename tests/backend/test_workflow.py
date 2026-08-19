from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def unique_title(prefix: str) -> str:
    return f"{prefix} {uuid4().hex}"


def create_low_risk_approved_newsletter() -> int:
    payload = {
        "title": unique_title("Workflow test newsletter"),
        "topic": "ai_news",
        "body": (
            "Researchers published documentation for an evaluation dataset. "
            "The documentation describes methodology and known limitations."
        ),
    }

    response = client.post("/api/newsletters", json=payload)
    assert response.status_code == 201

    newsletter_id = response.json()["id"]

    response = client.post(
        f"/api/newsletters/{newsletter_id}/classify-and-store"
    )
    assert response.status_code == 200

    response = client.post(
        f"/api/newsletters/{newsletter_id}/approve"
    )
    assert response.status_code == 200

    return newsletter_id


def test_workflow_zero_subscribers():
    response = client.post(
        "/api/newsletters",
        json={
            "title": unique_title("Zero subscriber test"),
            "topic": "devops",
            "body": "A short operations update.",
        },
    )
    assert response.status_code == 201

    newsletter_id = response.json()["id"]

    response = client.post(
        f"/api/workflows/newsletter/{newsletter_id}/run"
    )

    assert response.status_code == 400
    assert "No active subscribers" in response.json()["detail"]


def test_workflow_success_and_idempotent():
    email = unique_email("workflow-test")

    response = client.post(
        "/api/subscribers",
        json={
            "email": email,
            "name": "Workflow Test",
            "topics": ["ai_news"],
        },
    )
    assert response.status_code == 201

    newsletter_id = create_low_risk_approved_newsletter()

    response = client.post(
        f"/api/workflows/newsletter/{newsletter_id}/run"
    )
    assert response.status_code == 200

    data = response.json()["result"]
    assert data["subscriber_count"] >= 1
    assert data["created_drafts"] >= 1
    assert data["send_summary"]["count"] >= 1

    drafts_response = client.get(
        f"/api/drafts/newsletter/{newsletter_id}"
    )
    assert drafts_response.status_code == 200

    drafts_before = [
        item
        for item in drafts_response.json()["drafts"]
        if item["subscriber_email"] == email
    ]
    assert len(drafts_before) == 1

    response = client.post(
        f"/api/workflows/newsletter/{newsletter_id}/run"
    )
    assert response.status_code == 200

    drafts_response = client.get(
        f"/api/drafts/newsletter/{newsletter_id}"
    )
    assert drafts_response.status_code == 200

    drafts_after = [
        item
        for item in drafts_response.json()["drafts"]
        if item["subscriber_email"] == email
    ]
    assert len(drafts_after) == 1


def test_subscriber_update_replaces_topics_without_duplicates():
    email = unique_email("subscriber-update")

    first = client.post(
        "/api/subscribers",
        json={
            "email": email,
            "name": "First Name",
            "topics": ["ai_news", "robotics"],
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/api/subscribers",
        json={
            "email": email,
            "name": "Updated Name",
            "topics": ["ai_news"],
        },
    )
    assert second.status_code == 201

    response = client.get("/api/subscribers")
    assert response.status_code == 200

    subscriber = next(
        item
        for item in response.json()["subscribers"]
        if item["email"] == email
    )

    assert subscriber["name"] == "Updated Name"
    assert subscriber["is_active"] is True
    assert subscriber["topics"] == ["ai_news"]

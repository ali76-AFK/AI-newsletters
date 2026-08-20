from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db import get_session
from backend.app.models import Newsletter


client = TestClient(app)


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def unique_title(prefix: str) -> str:
    return f"{prefix} {uuid4().hex}"


def create_newsletter(topic: str = "ai_news") -> int:
    response = client.post(
        "/api/newsletters",
        json={
            "title": unique_title("Safety policy newsletter"),
            "topic": topic,
            "body": (
                "This is a local test newsletter with a factual update "
                "and no sensitive details."
            ),
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def set_risk(
    newsletter_id: int,
    risk_level: str,
    approved: bool = False,
) -> None:
    with get_session() as db:
        newsletter = db.get(Newsletter, newsletter_id)
        assert newsletter is not None

        newsletter.risk_level = risk_level
        newsletter.risk_reason = "Test-assigned risk level."
        newsletter.approved = approved
        newsletter.review_decision = None
        newsletter.review_note = None
        newsletter.status = (
            "pending_review"
            if risk_level in {"high", "critical"}
            else "classified"
        )


def test_critical_newsletter_cannot_be_manually_approved():
    newsletter_id = create_newsletter()
    set_risk(newsletter_id, "critical")

    response = client.post(
        f"/api/newsletters/{newsletter_id}/approve"
    )

    assert response.status_code == 400
    assert "require human review" in response.json()["detail"]

    with get_session() as db:
        newsletter = db.get(Newsletter, newsletter_id)
        assert newsletter is not None
        assert newsletter.approved is False


def test_critical_newsletter_cannot_send_through_direct_workflow():
    email = unique_email("critical-workflow")

    subscribe = client.post(
        "/api/subscribers",
        json={
            "email": email,
            "name": "Critical Workflow Test",
            "topics": ["ai_news"],
        },
    )
    assert subscribe.status_code == 201

    newsletter_id = create_newsletter()
    set_risk(newsletter_id, "critical", approved=True)

    response = client.post(
        f"/api/workflows/newsletter/{newsletter_id}/run"
    )

    assert response.status_code == 400
    assert "require human review" in response.json()["detail"]

    with get_session() as db:
        newsletter = db.get(Newsletter, newsletter_id)
        assert newsletter is not None
        assert newsletter.status == "pending_review"


def test_low_risk_approved_newsletter_sends_and_is_marked_sent():
    email = unique_email("low-risk-send")

    subscribe = client.post(
        "/api/subscribers",
        json={
            "email": email,
            "name": "Low Risk Send Test",
            "topics": ["ai_news"],
        },
    )
    assert subscribe.status_code == 201

    newsletter_id = create_newsletter()
    set_risk(newsletter_id, "low")

    approve = client.post(
        f"/api/newsletters/{newsletter_id}/approve"
    )
    assert approve.status_code == 200
    assert approve.json()["approved"] is True

    response = client.post(
        f"/api/workflows/newsletter/{newsletter_id}/run"
    )

    assert response.status_code == 200
    assert response.json()["result"]["send_summary"]["count"] >= 1

    with get_session() as db:
        newsletter = db.get(Newsletter, newsletter_id)
        assert newsletter is not None
        assert newsletter.status == "sent"


def test_high_risk_requires_human_review_route():
    newsletter_id = create_newsletter()
    set_risk(newsletter_id, "high")

    direct_approval = client.post(
        f"/api/newsletters/{newsletter_id}/approve"
    )
    assert direct_approval.status_code == 400

    pending = client.get("/api/reviews/pending")
    assert pending.status_code == 200

    pending_ids = {
        item["id"]
        for item in pending.json()["pending_reviews"]
    }
    assert newsletter_id in pending_ids

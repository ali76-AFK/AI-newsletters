from __future__ import annotations

from datetime import datetime
from typing import List

from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from .langgraph_state import DraftSummary, SubscriberState, WorkflowState, SendSummary
from .models import DraftEmail, Newsletter, Subscriber, SubscriberTopic, WorkflowExecution
from .email_sender import send_email, EmailSendError


class WorkflowGraphError(Exception):
    pass


def build_workflow_graph(db: Session) -> StateGraph[WorkflowState]:
    graph = StateGraph(WorkflowState)

    def load_newsletter_node(state: WorkflowState) -> WorkflowState:
        newsletter = db.get(Newsletter, state.newsletter_id)
        if newsletter is None:
            raise WorkflowGraphError(f"Newsletter {state.newsletter_id} not found")

        wf = (
            db.query(WorkflowExecution)
            .filter(WorkflowExecution.newsletter_id == state.newsletter_id)
            .order_by(WorkflowExecution.started_at.desc())
            .first()
        )
        if wf is None:
            raise WorkflowGraphError(
                f"No workflow execution found for newsletter {state.newsletter_id}",
            )

        wf.state = "running"
        wf.completed_at = None
        db.flush()

        state.topic = newsletter.topic
        state.workflow_id = wf.id
        return state

    def load_subscribers_node(state: WorkflowState) -> WorkflowState:
        if state.topic is None:
            raise WorkflowGraphError("Topic not set in state")

        subscribers: List[Subscriber] = (
            db.query(Subscriber)
            .join(SubscriberTopic)
            .filter(
                Subscriber.is_active.is_(True),
                SubscriberTopic.topic == state.topic,
            )
            .order_by(Subscriber.created_at.desc())
            .all()
        )

        if not subscribers:
            raise WorkflowGraphError("No active subscribers for this topic")

        state.subscribers = [
            SubscriberState(
                id=sub.id,
                email=sub.email,
                name=sub.name,
            )
            for sub in subscribers
        ]

        return state

    def create_drafts_node(state: WorkflowState) -> WorkflowState:
        newsletter = db.get(Newsletter, state.newsletter_id)
        if newsletter is None:
            raise WorkflowGraphError(f"Newsletter {state.newsletter_id} not found")

        created: List[DraftSummary] = []

        for sub_state in state.subscribers:
            subject = newsletter.title
            body = (
                f"Hello {sub_state.name or 'subscriber'},\n\n"
                f"{newsletter.body}\n\nBest regards,\nYour AI Newsletter"
            )

            existing = (
                db.query(DraftEmail)
                .filter(
                    DraftEmail.newsletter_id == newsletter.id,
                    DraftEmail.subscriber_id == sub_state.id,
                )
                .first()
            )

            if existing:
                existing.subject = subject
                existing.body = body
                draft = existing
            else:
                draft = DraftEmail(
                    newsletter_id=newsletter.id,
                    subscriber_id=sub_state.id,
                    subject=subject,
                    body=body,
                    status="draft",
                )
                db.add(draft)

            db.flush()
            created.append(
                DraftSummary(
                    id=draft.id,
                    subscriber_id=sub_state.id,
                    subject=subject,
                ),
            )

        state.created_drafts = created
        return state

    def simulate_send_node(state: WorkflowState) -> WorkflowState:
        newsletter = db.get(Newsletter, state.newsletter_id)
        if newsletter is None:
            raise WorkflowGraphError(f"Newsletter {state.newsletter_id} not found")

        # Guardrail: only send if approved and not high risk
        if not newsletter.approved:
            raise WorkflowGraphError("Newsletter not approved; cannot send.")
        if newsletter.risk_level == "high":
            raise WorkflowGraphError("High-risk newsletter; sending blocked.")

        sender = "newsletter-orchestrator@example.com"
        recipients = [s.email for s in state.subscribers]
        subject = newsletter.title
        # For simplicity, reuse newsletter.body; in practice, use refined drafts per subscriber.
        body = newsletter.body

        try:
            send_email(sender, recipients, subject, body)
        except EmailSendError as exc:
            raise WorkflowGraphError(f"Email sending failed: {exc}") from exc

        state.send_summary = SendSummary(
            sender=sender,
            recipients=recipients,
            subject=subject,
            count=len(recipients),
        )
        return state

    def update_workflow_node(state: WorkflowState) -> WorkflowState:
        wf = db.get(WorkflowExecution, state.workflow_id)
        newsletter = db.get(Newsletter, state.newsletter_id)

        if wf is None or newsletter is None:
            raise WorkflowGraphError("Workflow or newsletter not found while updating")

        wf.state = "completed"
        wf.completed_at = datetime.utcnow()
        newsletter.status = "drafting"  # could be 'sent' later if desired
        db.flush()

        return state

    graph.add_node("load_newsletter", load_newsletter_node)
    graph.add_node("load_subscribers", load_subscribers_node)
    graph.add_node("create_drafts", create_drafts_node)
    graph.add_node("simulate_send", simulate_send_node)
    graph.add_node("update_workflow", update_workflow_node)

    graph.set_entry_point("load_newsletter")
    graph.add_edge("load_newsletter", "load_subscribers")
    graph.add_edge("load_subscribers", "create_drafts")
    graph.add_edge("create_drafts", "simulate_send")
    graph.add_edge("simulate_send", "update_workflow")
    graph.add_edge("update_workflow", END)

    return graph

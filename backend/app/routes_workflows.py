from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from langgraph.graph import StateGraph
from sqlalchemy.orm import Session

from .db import get_session
from .langgraph_state import WorkflowState
from .langgraph_workflow import (
    WorkflowGraphError,
    build_workflow_graph,
)

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def get_db():
    with get_session() as session:
        yield session


@router.post(
    "/newsletter/{newsletter_id}/run",
    status_code=status.HTTP_200_OK,
)
def run_newsletter_workflow(
    newsletter_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    Run deterministic workflow for a given newsletter via LangGraph,
    including draft creation and send simulation.
    """
    initial_state = WorkflowState(
        newsletter_id=newsletter_id,
        workflow_id=0,
    )

    try:
        graph_builder: StateGraph[WorkflowState] = build_workflow_graph(db)
        app = graph_builder.compile()
        raw_state: Any = app.invoke(initial_state)
        if isinstance(raw_state, dict):
            result_state = WorkflowState(**raw_state)
        else:
            result_state = WorkflowState(**dict(raw_state))
    except WorkflowGraphError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workflow failed",
        ) from exc

    send_info = None
    if result_state.send_summary is not None:
        send_info = {
            "sender": result_state.send_summary.sender,
            "recipients": result_state.send_summary.recipients,
            "subject": result_state.send_summary.subject,
            "count": result_state.send_summary.count,
        }

    return {
        "status": "ok",
        "result": {
            "newsletter_id": result_state.newsletter_id,
            "workflow_id": result_state.workflow_id,
            "created_drafts": len(result_state.created_drafts),
            "subscriber_count": len(result_state.subscribers),
            "send_summary": send_info,
        },
    }

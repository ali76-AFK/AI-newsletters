from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from .models import AutomationState


AUTOMATION_COOLDOWN_SECONDS = 15 * 60
MAX_AUTOMATED_SENDS_PER_DAY = 3


def get_or_create_automation_state(db: Session) -> AutomationState:
    state = db.get(AutomationState, 1)

    if state is None:
        state = AutomationState(
            id=1,
            enabled=False,
            halted_for_review=False,
            halt_reason=None,
            daily_send_count=0,
            daily_send_date=None,
        )
        db.add(state)
        db.flush()

    return state


def start_automation(db: Session) -> AutomationState:
    state = get_or_create_automation_state(db)
    state.enabled = True
    state.halted_for_review = False
    state.halt_reason = None
    db.flush()
    return state


def stop_automation(db: Session) -> AutomationState:
    state = get_or_create_automation_state(db)
    state.enabled = False
    db.flush()
    return state


def halt_automation_for_review(
    db: Session,
    reason: str,
) -> AutomationState:
    state = get_or_create_automation_state(db)
    state.enabled = False
    state.halted_for_review = True
    state.halt_reason = reason
    db.flush()
    return state


def reset_daily_counter_if_needed(
    state: AutomationState,
    now: datetime,
) -> None:
    """Reset the sent count at the start of a new local calendar day."""
    if state.daily_send_date is None or state.daily_send_date.date() != now.date():
        state.daily_send_date = now
        state.daily_send_count = 0


def cooldown_remaining_seconds(
    state: AutomationState,
    now: datetime,
) -> int:
    """Return remaining cooldown seconds, or zero when a tick is allowed."""
    if state.last_run_at is None:
        return 0

    elapsed = (now - state.last_run_at).total_seconds()
    remaining = AUTOMATION_COOLDOWN_SECONDS - elapsed
    return max(0, int(remaining))


def can_run_automation_tick(
    state: AutomationState,
    now: datetime,
) -> tuple[bool, str | None]:
    """
    Check code-enforced safety rules before a tick can create/send content.
    """
    reset_daily_counter_if_needed(state, now)

    remaining = cooldown_remaining_seconds(state, now)
    if remaining > 0:
        return (
            False,
            f"Cooldown active. Try again in approximately {remaining} seconds.",
        )

    if state.daily_send_count >= MAX_AUTOMATED_SENDS_PER_DAY:
        return (
            False,
            f"Daily automation limit reached ({MAX_AUTOMATED_SENDS_PER_DAY} sends).",
        )

    return True, None


def record_automated_send(
    state: AutomationState,
    now: datetime,
) -> None:
    """Record a successfully auto-approved and sent newsletter."""
    reset_daily_counter_if_needed(state, now)
    state.daily_send_count += 1
    state.daily_send_date = now
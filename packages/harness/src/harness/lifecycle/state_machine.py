"""Lifecycle state machine per ARCHITECTURE.md §6.

States (subset of original 11 — discovery-side states like 'discovered',
'filtered', 'scored' belong to Wave 3 JD discovery and are not built yet):

  tailored      ← default after verdict=complete
  applied       ← user clicked "I submitted this"
  oa            ← online assessment received
  interview     ← interview scheduled / conducted
  rejected      ← got rejection (terminal)
  offer         ← got offer (terminal — proceed to acceptance externally)
  archived      ← user manually archived (terminal-like; un-archive returns to tailored)
  dismissed     ← user discarded an unsubmitted draft (truly terminal, from tailored only)

Transitions are user-driven; backend validates that the requested
target state is reachable from the current state per VALID_TRANSITIONS.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, TypedDict


LifecycleState = Literal[
    "tailored",
    "applied",
    "oa",
    "interview",
    "rejected",
    "offer",
    "archived",
    "dismissed",
]

def seed_initial(state: LifecycleState = "tailored") -> dict:
    """Build the lifecycle dict for a freshly-completed run.

    Centralizes the {current_state, events: [first_event]} shape so callers
    don't reconstruct it from literals (which drift). Used by repl.stages.
    late_feedback when verdict=complete.
    """
    return {
        "current_state": state,
        "events": [
            {
                "state": state,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }


LIFECYCLE_STATES: tuple[LifecycleState, ...] = (
    "tailored",
    "applied",
    "oa",
    "interview",
    "rejected",
    "offer",
    "archived",
    "dismissed",
)

# Forward + (limited) backward transitions. Backward useful when user
# mistakenly marks "applied" before actually submitting.
VALID_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    "tailored":  {"applied", "dismissed", "archived"},
    "applied":   {"oa", "interview", "rejected", "offer", "archived", "tailored"},  # backward to tailored = mistake undo
    "oa":        {"interview", "rejected", "offer", "archived", "applied"},          # backward to applied
    "interview": {"rejected", "offer", "archived", "oa"},                            # backward to oa
    "rejected":  {"archived"},   # terminal except for archive cleanup
    "offer":     {"archived"},   # terminal except for archive cleanup
    "archived":  {"tailored"},   # un-archive returns to tailored (one-way; user can re-walk)
    "dismissed": set(),          # truly terminal
}

# Terminal states for `is_terminal`. archived is *not* terminal because the
# user can un-archive it back to `tailored`. rejected/offer/dismissed are
# treated as terminal for the purpose of the active job-search loop.
_TERMINAL: set[LifecycleState] = {"rejected", "offer", "dismissed"}


class LifecycleEvent(TypedDict, total=False):
    state: LifecycleState
    timestamp: str  # ISO 8601
    note: str
    channel: str  # optional, e.g. "linkedin" / "company_portal" / "email"


def is_terminal(state: LifecycleState) -> bool:
    """Return True if `state` is a terminal state in the active loop."""
    return state in _TERMINAL


def apply_transition(
    current: LifecycleState,
    target: LifecycleState,
    note: str | None = None,
    channel: str | None = None,
    now: datetime | None = None,
) -> LifecycleEvent:
    """Validate + return a new event. Caller persists it to state.json.

    Raises ValueError if the transition isn't allowed from `current`.
    """
    if target not in VALID_TRANSITIONS.get(current, set()):
        raise ValueError(
            f"invalid lifecycle transition: {current} → {target}. "
            f"Valid from {current}: {sorted(VALID_TRANSITIONS.get(current, set()))}"
        )
    when = (now or datetime.now(timezone.utc)).isoformat()
    event: LifecycleEvent = {"state": target, "timestamp": when}
    if note:
        event["note"] = note
    if channel:
        event["channel"] = channel
    return event

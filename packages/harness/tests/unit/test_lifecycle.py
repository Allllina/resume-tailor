"""Tests for harness.lifecycle.state_machine (Wave 4 Step C).

Covers:
- All forward transitions valid (tailored→applied, applied→oa, oa→interview,
  interview→rejected/offer)
- Backward transitions allowed (applied→tailored, oa→applied, interview→oa)
- `dismissed` terminal — no exits
- `rejected` / `offer` only allow `archived`
- `archived` → `tailored` (un-archive)
- Invalid transition raises ValueError with descriptive message
- `is_terminal` correct
- `apply_transition` returns event dict with state + timestamp + optional
  note/channel
"""
from datetime import datetime, timezone

import pytest

from harness.lifecycle import (
    LIFECYCLE_STATES,
    VALID_TRANSITIONS,
    apply_transition,
    is_terminal,
)


# ----- Forward transitions -----

@pytest.mark.parametrize("current,target", [
    ("tailored", "applied"),
    ("tailored", "dismissed"),
    ("tailored", "archived"),
    ("applied", "oa"),
    ("applied", "interview"),
    ("applied", "rejected"),
    ("applied", "offer"),
    ("applied", "archived"),
    ("oa", "interview"),
    ("oa", "rejected"),
    ("oa", "offer"),
    ("oa", "archived"),
    ("interview", "rejected"),
    ("interview", "offer"),
    ("interview", "archived"),
])
def test_forward_transitions_valid(current, target):
    ev = apply_transition(current, target)
    assert ev["state"] == target
    assert "timestamp" in ev


# ----- Backward transitions (mistake-undo) -----

@pytest.mark.parametrize("current,target", [
    ("applied", "tailored"),    # un-mark "I submitted this"
    ("oa", "applied"),          # OA wasn't real, back to applied
    ("interview", "oa"),        # interview was a follow-up to OA
    ("archived", "tailored"),   # un-archive
])
def test_backward_transitions_allowed(current, target):
    ev = apply_transition(current, target)
    assert ev["state"] == target


# ----- Terminal: dismissed has no exits -----

def test_dismissed_has_no_exits():
    assert VALID_TRANSITIONS["dismissed"] == set()
    for s in LIFECYCLE_STATES:
        with pytest.raises(ValueError):
            apply_transition("dismissed", s)


# ----- rejected / offer only allow archived -----

@pytest.mark.parametrize("terminal", ["rejected", "offer"])
def test_terminal_states_only_archive(terminal):
    assert VALID_TRANSITIONS[terminal] == {"archived"}
    # archived is allowed
    ev = apply_transition(terminal, "archived")
    assert ev["state"] == "archived"
    # everything else fails
    for s in LIFECYCLE_STATES:
        if s == "archived":
            continue
        with pytest.raises(ValueError):
            apply_transition(terminal, s)


# ----- archived → tailored only -----

def test_archived_unarchives_to_tailored_only():
    assert VALID_TRANSITIONS["archived"] == {"tailored"}
    ev = apply_transition("archived", "tailored")
    assert ev["state"] == "tailored"
    with pytest.raises(ValueError):
        apply_transition("archived", "applied")


# ----- Invalid transition -----

def test_invalid_transition_raises_with_message():
    with pytest.raises(ValueError) as exc:
        apply_transition("tailored", "offer")  # skip 'applied'
    msg = str(exc.value)
    assert "tailored" in msg and "offer" in msg
    assert "Valid from tailored" in msg


# ----- is_terminal -----

def test_is_terminal_correctness():
    assert is_terminal("rejected")
    assert is_terminal("offer")
    assert is_terminal("dismissed")
    # archived can be un-archived → not terminal in the active loop
    assert not is_terminal("archived")
    assert not is_terminal("tailored")
    assert not is_terminal("applied")
    assert not is_terminal("oa")
    assert not is_terminal("interview")


# ----- Event shape -----

def test_event_includes_optional_note_and_channel():
    ev = apply_transition(
        "tailored",
        "applied",
        note="submitted via referral",
        channel="linkedin",
    )
    assert ev["state"] == "applied"
    assert ev["note"] == "submitted via referral"
    assert ev["channel"] == "linkedin"
    # timestamp parses as ISO
    datetime.fromisoformat(ev["timestamp"])


def test_event_omits_optional_fields_when_unset():
    ev = apply_transition("tailored", "applied")
    assert "note" not in ev
    assert "channel" not in ev


def test_event_uses_provided_now():
    fixed = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
    ev = apply_transition("tailored", "applied", now=fixed)
    assert ev["timestamp"] == fixed.isoformat()

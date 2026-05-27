"""Test schema registry loading the 6 Wave 0 contracts."""
import pytest
from harness.schemas.loader import SchemaRegistry, SchemaValidationError


EXPECTED_SCHEMAS = {
    "harness-tailor-input",
    "harness-tailor-output",
    "pass3-verifier-io",
    "policy-gateway-decision",
    "metrics-event",
    "feedback-ingestion",
}


def test_loads_all_wave0_schemas(repo_root):
    reg = SchemaRegistry(repo_root)
    assert EXPECTED_SCHEMAS.issubset(set(reg.schema_names()))


def test_validates_correct_input(repo_root):
    """A minimal valid harness-tailor-input should pass."""
    reg = SchemaRegistry(repo_root)
    reg.validate("harness-tailor-input", {
        "mode": "manual",
        "jd": {"source": "paste", "raw_text": "x" * 100},
        "candidate_profile_ref": "assets/profile/user-profile.md",
        "target_market": "mainland-china",
    })  # should not raise


def test_rejects_invalid_input_enum(repo_root):
    """mode='invalid_mode' violates the enum — should raise."""
    reg = SchemaRegistry(repo_root)
    with pytest.raises(SchemaValidationError) as excinfo:
        reg.validate("harness-tailor-input", {
            "mode": "invalid_mode",
            "jd": {"source": "paste", "raw_text": "x" * 100},
            "candidate_profile_ref": "x",
            "target_market": "mainland-china",
        })
    # Error message should mention the failing field path or value
    assert "mode" in str(excinfo.value) or "invalid_mode" in str(excinfo.value)


def test_rejects_missing_required(repo_root):
    """Missing required field 'mode' should raise."""
    reg = SchemaRegistry(repo_root)
    with pytest.raises(SchemaValidationError):
        reg.validate("harness-tailor-input", {
            "jd": {"source": "paste", "raw_text": "x" * 100},
            "candidate_profile_ref": "x",
            "target_market": "mainland-china",
        })


def test_rejects_jd_raw_text_too_short(repo_root):
    """jd.raw_text has minLength 50 in the schema."""
    reg = SchemaRegistry(repo_root)
    with pytest.raises(SchemaValidationError):
        reg.validate("harness-tailor-input", {
            "mode": "manual",
            "jd": {"source": "paste", "raw_text": "short"},  # < 50 chars
            "candidate_profile_ref": "x",
            "target_market": "mainland-china",
        })


def test_unknown_schema_name_raises(repo_root):
    reg = SchemaRegistry(repo_root)
    with pytest.raises(SchemaValidationError) as excinfo:
        reg.validate("nonexistent-schema", {})
    assert "Unknown schema" in str(excinfo.value) or "nonexistent" in str(excinfo.value)


def test_validates_metrics_event(repo_root):
    """Sanity check on a different schema."""
    reg = SchemaRegistry(repo_root)
    reg.validate("metrics-event", {
        "event_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2026-05-04T10:00:00Z",
        "category": "task_effectiveness",
        "metric_name": "task_success",
        "value": True,
        "context": {"stage": "feedback", "tier": 1},
    })


def test_validates_policy_gateway_decision(repo_root):
    reg = SchemaRegistry(repo_root)
    reg.validate("policy-gateway-decision", {
        "decision_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2026-05-04T10:00:00Z",
        "action_type": "bullet_rewrite",
        "verdict": "allow",
        "policies_evaluated": [
            {"policy_id": "R-1", "result": "pass"},
        ],
    })


def test_schema_names_returns_list(repo_root):
    reg = SchemaRegistry(repo_root)
    names = reg.schema_names()
    assert isinstance(names, list)
    assert all(isinstance(n, str) for n in names)
    assert len(names) >= 6


def test_loads_wave3_schemas(repo_root):
    """Wave 3 schemas should auto-load via SchemaRegistry."""
    reg = SchemaRegistry(repo_root)
    names = set(reg.schema_names())
    assert "submit-channel" in names
    assert "submit-audit" in names
    assert "additional-questions" in names


def test_validates_submit_channel_input(repo_root):
    reg = SchemaRegistry(repo_root)
    reg.validate("submit-channel", {
        "draft_id": "abc-123",
        "channel": "linkedin",
        "method": "userscript"
    })


def test_rejects_unknown_channel(repo_root):
    reg = SchemaRegistry(repo_root)
    with pytest.raises(SchemaValidationError):
        reg.validate("submit-channel", {
            "draft_id": "x",
            "channel": "facebook",  # not in enum
            "method": "userscript"
        })


def test_validates_submit_audit_outcome_enum(repo_root):
    reg = SchemaRegistry(repo_root)
    reg.validate("submit-audit", {
        "audit_id": "550e8400-e29b-41d4-a716-446655440000",
        "draft_id": "x",
        "channel": "linkedin",
        "method": "userscript",
        "outcome": "submitted",
        "timestamp": "2026-05-06T12:00:00Z"
    })
    with pytest.raises(SchemaValidationError):
        reg.validate("submit-audit", {
            "audit_id": "550e8400-e29b-41d4-a716-446655440000",
            "draft_id": "x",
            "channel": "linkedin",
            "method": "userscript",
            "outcome": "weird_outcome",
            "timestamp": "2026-05-06T12:00:00Z"
        })


def test_validates_additional_questions_minimal(repo_root):
    reg = SchemaRegistry(repo_root)
    reg.validate("additional-questions", {"schema_version": "0.1.0"})


# ===== Wave 2.7 multi-user schemas =====


def test_loads_wave2_7_schemas(repo_root):
    reg = SchemaRegistry(repo_root)
    names = set(reg.schema_names())
    assert "user-profile" in names
    assert "resume-upload-input" in names
    assert "experience-upload-input" in names


def test_validates_user_profile_minimal(repo_root):
    reg = SchemaRegistry(repo_root)
    reg.validate("user-profile", {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "created_at": "2026-05-06T12:00:00Z",
        "candidate_names": ["Test User"],
    })


def test_user_profile_accepts_jingwen_default_slug(repo_root):
    """Migration seeds user_id='default' (slug, not UUID) — schema must accept."""
    reg = SchemaRegistry(repo_root)
    reg.validate("user-profile", {
        "user_id": "default",
        "created_at": "2026-05-06T12:00:00Z",
        "candidate_names": ["张明", "Zhang Ming"],
    })


def test_user_profile_rejects_invalid_user_id(repo_root):
    reg = SchemaRegistry(repo_root)
    with pytest.raises(SchemaValidationError):
        reg.validate("user-profile", {
            "user_id": "not a uuid or slug",  # spaces not allowed
            "created_at": "2026-05-06T12:00:00Z",
            "candidate_names": ["x"],
        })


def test_resume_upload_input_format_enum(repo_root):
    reg = SchemaRegistry(repo_root)
    reg.validate("resume-upload-input", {"file_name": "r.tex", "format": "tex"})
    with pytest.raises(SchemaValidationError):
        reg.validate("resume-upload-input", {"file_name": "r.txt", "format": "txt"})


def test_resume_upload_input_size_limit(repo_root):
    reg = SchemaRegistry(repo_root)
    with pytest.raises(SchemaValidationError):
        reg.validate("resume-upload-input", {
            "file_name": "huge.pdf",
            "format": "pdf",
            "size_bytes": 6 * 1024 * 1024,  # > 5MB cap per Wave 2.7 post-dogfood bump
        })


def test_experience_upload_input_max_30(repo_root):
    reg = SchemaRegistry(repo_root)
    files = [{"file_name": f"exp{i}.md", "format": "md"} for i in range(30)]
    reg.validate("experience-upload-input", {"files": files})
    with pytest.raises(SchemaValidationError):
        reg.validate("experience-upload-input", {
            "files": files + [{"file_name": "one_too_many.md", "format": "md"}],
        })


# ===== Wave 4 Step C — lifecycle schemas =====


def test_loads_lifecycle_event_schema(repo_root):
    reg = SchemaRegistry(repo_root)
    assert "lifecycle-event" in reg.schema_names()


def test_validates_lifecycle_event_minimal(repo_root):
    reg = SchemaRegistry(repo_root)
    reg.validate("lifecycle-event", {
        "state": "applied",
        "timestamp": "2026-05-06T12:00:00Z",
    })


def test_validates_lifecycle_event_with_note_and_channel(repo_root):
    reg = SchemaRegistry(repo_root)
    reg.validate("lifecycle-event", {
        "state": "applied",
        "timestamp": "2026-05-06T12:00:00Z",
        "note": "via referral",
        "channel": "linkedin",
    })


def test_rejects_invalid_lifecycle_state(repo_root):
    reg = SchemaRegistry(repo_root)
    with pytest.raises(SchemaValidationError):
        reg.validate("lifecycle-event", {
            "state": "won_powerball",  # not in enum
            "timestamp": "2026-05-06T12:00:00Z",
        })


def test_run_summary_accepts_lifecycle_state(repo_root):
    reg = SchemaRegistry(repo_root)
    reg.validate("run-summary", {
        "run_id": "550e8400-e29b-41d4-a716-446655440000",
        "created_at": "2026-05-06T12:00:00Z",
        "verdict": "complete",
        "ui_status": "submitted",
        "lifecycle_state": "applied",
    })
    with pytest.raises(SchemaValidationError):
        reg.validate("run-summary", {
            "run_id": "550e8400-e29b-41d4-a716-446655440000",
            "created_at": "2026-05-06T12:00:00Z",
            "verdict": "complete",
            "ui_status": "submitted",
            "lifecycle_state": "won_powerball",
        })


# ===== Wave 4 D.2a/D.2b — rewrite-engine-output schema =====


def test_loads_rewrite_engine_output_schema(repo_root):
    reg = SchemaRegistry(repo_root)
    assert "rewrite-engine-output" in reg.schema_names()


def test_validates_rewrite_engine_output_minimal(repo_root):
    reg = SchemaRegistry(repo_root)
    reg.validate("rewrite-engine-output", {
        "section_a_fit_diagnosis": "fit prose",
        "section_b_priority_signals": [],
        "section_c_experience_prioritization": {},
        "section_d_resume_narrative": "",
        "section_e_cross_company_variations": "single-JD",
        "section_f_section_by_section_guidance": {},
        "section_g_bullets": [
            {
                "id": "01-kearney-bullet-1",
                "text": "did the thing",
                "claimed_facts": ["did the thing"],
                "experience_id": "01-kearney",
                "final_category": 2,
            }
        ],
        "section_h_resume_structure": {},
        "section_i_final_resume_draft": "",
        "section_j_decision_log": [
            {
                "experience_id": "01-kearney",
                "decision": "rewrote_for_tier_2",
                "rationale": "Cat 2 rewrite.",
            }
        ],
        "_method": "llm",
    })


def test_harness_tailor_output_accepts_rewrite_engine_output_block(repo_root):
    reg = SchemaRegistry(repo_root)
    reg.validate("harness-tailor-output", {
        "run_id": "550e8400-e29b-41d4-a716-446655440000",
        "input_ref": "x.json",
        "verdict": "complete",
        "tier_assigned": 2,
        "matched_resume_version": "C_product_ops",
        "tex_artifact_path": "out.tex",
        "trace": {
            "perception_events": [],
            "planning_events": [],
            "action_events": [],
            "feedback_events": [],
        },
        "metrics": {"total_tokens": 0, "total_claude_calls": 0, "elapsed_seconds": 0.1},
        "rewrite_engine_output": {
            "section_a_fit_diagnosis": "x",
            "section_g_bullets": [],
            "_method": "llm",
        },
    })


def test_harness_tailor_output_accepts_lifecycle_block(repo_root):
    reg = SchemaRegistry(repo_root)
    reg.validate("harness-tailor-output", {
        "run_id": "550e8400-e29b-41d4-a716-446655440000",
        "input_ref": "x.json",
        "verdict": "complete",
        "tier_assigned": 1,
        "matched_resume_version": "C_product_ops",
        "tex_artifact_path": "out.tex",
        "trace": {
            "perception_events": [],
            "planning_events": [],
            "action_events": [],
            "feedback_events": [],
        },
        "metrics": {"total_tokens": 0, "total_claude_calls": 0, "elapsed_seconds": 0.1},
        "lifecycle": {
            "current_state": "applied",
            "events": [
                {"state": "tailored", "timestamp": "2026-05-06T12:00:00Z"},
                {"state": "applied", "timestamp": "2026-05-06T12:01:00Z", "channel": "linkedin"},
            ],
        },
    })

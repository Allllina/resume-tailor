"""Test rules loader for R-1..R-8 hard rules."""
import pytest
from harness.policy.rules_loader import RulesLoader


def test_loads_forbidden_categories(repo_root):
    loader = RulesLoader(repo_root)
    cats = loader.forbidden_categories()
    assert isinstance(cats, list)
    assert "ai_punctuation" in cats
    assert "colloquial" in cats
    assert "consultant_report_framing" in cats
    assert "llm_fabricated" in cats


def test_finds_violation_for_em_dash(repo_root):
    """Hits an ai_punctuation pattern (——)."""
    loader = RulesLoader(repo_root)
    violations = loader.find_violations("foo——bar")
    assert len(violations) >= 1
    em_dash = next(v for v in violations if v["pattern"] == "——")
    assert em_dash["category"] == "ai_punctuation"
    assert em_dash["replacement"] == "：或，"
    assert "rationale" in em_dash


def test_finds_violation_for_arrow(repo_root):
    loader = RulesLoader(repo_root)
    violations = loader.find_violations("step1 → step2")
    assert any(v["pattern"] == "→" for v in violations)


def test_finds_violation_llm_fabricated(repo_root):
    loader = RulesLoader(repo_root)
    violations = loader.find_violations("分析显示用户增长 30%")
    assert any(v["pattern"] == "分析显示" for v in violations)


def test_finds_multiple_violations(repo_root):
    loader = RulesLoader(repo_root)
    text = "押注——分析显示客户表面诉求是 X，实质为 Y"
    violations = loader.find_violations(text)
    patterns = {v["pattern"] for v in violations}
    # At least these three should be flagged
    assert "押注" in patterns
    assert "——" in patterns
    assert "分析显示" in patterns


def test_no_violations_in_clean_text(repo_root):
    loader = RulesLoader(repo_root)
    violations = loader.find_violations("这是一段干净的文本，没有违规模式。")
    assert violations == []


def test_violation_includes_match_type(repo_root):
    """match_type field added in Task 2 fix-up should be exposed in find_violations output."""
    loader = RulesLoader(repo_root)
    violations = loader.find_violations("foo——bar")
    em_dash = next(v for v in violations if v["pattern"] == "——")
    assert em_dash.get("match_type") == "literal"


def test_hard_locked_fields(repo_root):
    loader = RulesLoader(repo_root)
    locked = loader.hard_locked_fields()
    assert isinstance(locked, list)
    assert len(locked) == 9
    assert "公司名" in locked
    assert "学校" in locked
    assert "联系方式" in locked


def test_detection_heuristics(repo_root):
    loader = RulesLoader(repo_root)
    heuristics = loader.detection_heuristics()
    assert isinstance(heuristics, list)
    assert len(heuristics) >= 1
    pattern_types = {h["pattern_type"] for h in heuristics}
    assert "specific_number_without_anchor" in pattern_types
    assert "tool_name_not_in_whitelist" in pattern_types


def test_actions_when_unsourced(repo_root):
    """Exposes the canonical action enum for downstream typing."""
    loader = RulesLoader(repo_root)
    actions = loader.actions_when_unsourced()
    assert actions == ["remove", "mark_TBD", "ask_user"]


def test_unit_input_empty_text(repo_root):
    loader = RulesLoader(repo_root)
    assert loader.find_violations("") == []


def test_loader_with_explicit_paths(tmp_path, repo_root):
    """RulesLoader can be constructed with explicit paths for testability."""
    # Default path resolution still works
    default = RulesLoader(repo_root)
    assert default.forbidden_categories()

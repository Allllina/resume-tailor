"""Test Tier1Tools facade — instantiates all 6 Tier 1 transforms."""
from unittest.mock import MagicMock
from pathlib import Path

from harness.repl.eval import Tier1Tools
from harness.tier1.lens_router import LensRouter
from harness.tier1.master_selector import MasterSelector
from harness.tier1.skill_injector import SkillInjector
from harness.tier1.label_rewriter import LabelRewriter
from harness.tier1.summary_writer import SummaryWriter
from harness.tier1.disambiguator import Disambiguator


def test_instantiates_all_tier1_tools(repo_root):
    mock_llm = MagicMock()
    mock_policy = MagicMock()
    tools = Tier1Tools(repo_root=repo_root, llm_client=mock_llm, policy_gateway=mock_policy)

    assert isinstance(tools.lens_router, LensRouter)
    assert isinstance(tools.master_selector, MasterSelector)
    assert isinstance(tools.skill_injector, SkillInjector)
    assert isinstance(tools.label_rewriter, LabelRewriter)
    assert isinstance(tools.summary_writer, SummaryWriter)
    assert isinstance(tools.disambiguator, Disambiguator)


def test_exposes_repo_root_and_dependencies(repo_root):
    mock_llm = MagicMock()
    mock_policy = MagicMock()
    tools = Tier1Tools(repo_root=repo_root, llm_client=mock_llm, policy_gateway=mock_policy)

    assert tools.repo_root == repo_root
    assert tools.llm is mock_llm
    # Backward-compat alias still works
    assert tools.claude is mock_llm
    assert tools.policy is mock_policy


def test_lens_router_uses_claude(repo_root):
    """LensRouter must receive the LLM client for LLM fallback path."""
    mock_llm = MagicMock()
    mock_policy = MagicMock()
    tools = Tier1Tools(repo_root=repo_root, llm_client=mock_llm, policy_gateway=mock_policy)
    # LensRouter stores its client as `_claude` (private attr per Task 9 impl —
    # not renamed to keep the transform internals stable across the abstraction).
    assert tools.lens_router._claude is mock_llm


def test_label_rewriter_uses_claude(repo_root):
    mock_llm = MagicMock()
    mock_policy = MagicMock()
    tools = Tier1Tools(repo_root=repo_root, llm_client=mock_llm, policy_gateway=mock_policy)
    assert tools.label_rewriter._claude is mock_llm


def test_summary_writer_uses_claude(repo_root):
    mock_llm = MagicMock()
    mock_policy = MagicMock()
    tools = Tier1Tools(repo_root=repo_root, llm_client=mock_llm, policy_gateway=mock_policy)
    assert tools.summary_writer._claude is mock_llm

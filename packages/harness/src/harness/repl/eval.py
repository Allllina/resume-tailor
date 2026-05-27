"""Eval stage — tool router + call interceptor (Wave 1 minimal).

Per HARNESS_DESIGN.md §3.2 (Eval). Wave 1 minimal: a Tier1Tools facade
holding instantiated Tier 1 transforms (no per-call schema validation
or call interception yet — those land Wave 2 when first concrete
function-calling lifecycle ships).
"""
from pathlib import Path
from typing import Any

from harness.llm.pii_filtering_provider import PIIFilteringLLM
from harness.tier1.lens_router import LensRouter
from harness.tier1.master_selector import MasterSelector
from harness.tier1.skill_injector import SkillInjector
from harness.tier1.label_rewriter import LabelRewriter
from harness.tier1.summary_writer import SummaryWriter
from harness.tier1.summary_injector import inject_summary as inject_summary_fn
from harness.tier1.disambiguator import Disambiguator


class Tier1Tools:
    """Facade exposing all 6 Tier 1 transforms wired to shared deps.

    Wave 2.7: optional `user_master_path` plumbs a per-user uploaded
    master.tex into MasterSelector. When set, master selection short-
    circuits to that path regardless of lens.

    Wave 4 C.1.3 + D.5 follow-up: optional `user_dir` enables the full
    MasterSelector priority chain (per-lens master under
    `<user_dir>/masters/<lens>/master.tex` first, then legacy single
    `<user_dir>/master.tex`, then project sample). Pass `user_dir`
    instead of `user_master_path` for new call sites; both may be
    passed together for explicit override, but `user_dir` takes
    precedence inside MasterSelector when both are present.

    Wave 4 (Critical pre-D.4): when `candidate_names` is non-empty, the
    provided `llm_client` is wrapped in `PIIFilteringLLM` so every
    downstream LLM call (lens routing, competency extraction, label
    rewrite, summary writing, rewrite engine) goes through the PII /
    injection gate. Empty (or missing) `candidate_names` falls through
    to the inner provider directly — preserves existing test fixtures
    that do not need the wrapper and matches the "default jingwen"
    legacy code path.
    """

    def __init__(
        self,
        repo_root: Path,
        llm_client: Any,
        policy_gateway: Any,
        user_master_path: Path | None = None,
        user_dir: Path | None = None,
        candidate_names: list[str] | None = None,
    ):
        self.repo_root = repo_root
        # Wrap LLM with PII filter only when candidate_names are supplied;
        # phones + emails are still redacted by the wrapper independently of
        # name list, but constructing the wrapper for tests that pass `None`
        # would change `tools.llm is mock_llm` identity for many existing
        # cases. Keep the no-wrap fallthrough for backward compatibility.
        if candidate_names:
            self.llm = PIIFilteringLLM(llm_client, candidate_names)
        else:
            self.llm = llm_client
        self.policy = policy_gateway
        self.lens_router = LensRouter(self.llm)
        self.master_selector = MasterSelector(
            repo_root,
            user_master_path=user_master_path,
            user_dir=user_dir,
        )
        self.skill_injector = SkillInjector()
        self.label_rewriter = LabelRewriter(self.llm)
        self.summary_writer = SummaryWriter(self.llm)
        self.summary_injector = inject_summary_fn  # function, not class
        self.disambiguator = Disambiguator(repo_root)

    @property
    def claude(self):
        """Backward-compat alias for self.llm."""
        return self.llm

"""Policy gateway — every action passes through here.

Per HARNESS_DESIGN.md §6 Control Plane → Harness boundary.
Schema: contracts/schemas/policy-gateway-decision.schema.json

Combines:
- PII filter (Task 3, harness.policy.pii_filter)
- RulesLoader R-1..R-8 (Task 6, harness.policy.rules_loader)
- Injection defense (this wave, .injection_defense)

evaluate_action() returns a schema-compliant decision dict.
"""
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .pii_filter import PIIFilter
from .rules_loader import RulesLoader
from .injection_defense import detect_injection


Verdict = Literal["allow", "deny", "ask_user", "degrade"]

# Action types that operate on user-supplied / LLM-generated content (subject to
# injection + R-2 forbidden checks).
_CONTENT_BEARING_ACTIONS = frozenset({
    "bullet_rewrite",
    "skill_inject",
    "summary_write",
    "disambiguator_add",
})


class PolicyGateway:
    def __init__(self, repo_root: Path, candidate_names: list[str]):
        self.pii = PIIFilter(known_names=candidate_names)
        self.rules = RulesLoader(repo_root)

    def evaluate_action(
        self,
        action_type: str,
        actor: str,
        subject: dict,
        content: str = "",
    ) -> dict:
        """Evaluate a proposed action. Returns policy-gateway-decision.schema.json compliant dict."""
        policies_evaluated: list[dict] = []
        verdict: Verdict = "allow"
        denial_reason: str | None = None
        degradation_target: str | None = None

        # 1. Injection defense — only on content-bearing actions with non-empty content
        if action_type in _CONTENT_BEARING_ACTIONS and content:
            injections = detect_injection(content)
            policies_evaluated.append({
                "policy_id": "injection_defense",
                "result": "fail" if injections else "pass",
                "rationale": (
                    f"Found markers: {injections}" if injections
                    else "No injection markers detected"
                ),
            })
            if injections:
                verdict = "deny"
                denial_reason = f"Possible prompt injection detected: {injections[:3]}"

        # 2. R-2 forbidden patterns — only on content-bearing actions
        if action_type in _CONTENT_BEARING_ACTIONS and content and verdict == "allow":
            violations = self.rules.find_violations(content)
            policies_evaluated.append({
                "policy_id": "R-2",
                "result": "fail" if violations else "pass",
                "rationale": (
                    f"Found {len(violations)} forbidden pattern(s): "
                    + ", ".join(v["pattern"] for v in violations[:3])
                ) if violations else "No forbidden patterns",
            })
            if violations:
                verdict = "degrade"
                degradation_target = "retry_with_violation_feedback"

        # 3. (Future) PII pre-flight — caller is currently responsible for redaction
        # before this gateway. We just record that the policy was evaluated as N/A.
        # When PII redaction becomes mandatory at gateway level, switch to enforce.

        decision: dict = {
            "decision_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action_type": action_type,
            "actor": actor,
            "subject": subject,
            "verdict": verdict,
            "policies_evaluated": policies_evaluated,
        }
        # Schema declares denial_reason / ask_user_question / degradation_target
        # as type=string; omit (don't include as null) when not applicable.
        if denial_reason is not None:
            decision["denial_reason"] = denial_reason
        if degradation_target is not None:
            decision["degradation_target"] = degradation_target
        return decision

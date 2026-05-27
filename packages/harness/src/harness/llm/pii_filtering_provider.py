"""PII-filtering wrapper around any LLMProvider.

Implements LLMProvider Protocol; delegates to inner provider after
redacting candidate name + phones + emails from system + user
prompts. Also runs detect_injection() on user content; raises
InjectionDetectedError when injection markers found.

WHY: closes HARNESS_COMPLIANCE_AUDIT.md Gap 1 (PII leak) by enforcing
filtering at the Provider boundary, so every caller (competency,
rewrite, summary, future verifier) gets the same gate.

INVARIANT (mirrors pii_filter.py): the wrapper does NOT restore PII
from the LLM response. The caller receives whatever the LLM emitted
(typically still containing the [CANDIDATE_NAME] / [PHONE_N] /
[EMAIL_N] placeholders). Restore is the caller's job — and per
pii_filter.py docstring lines 30-40 it must only happen for LOCAL
TRUSTED OUTPUT (the .tex artifact) — never re-send restored text
to an LLM, never log it, never forward externally.
"""
from harness.llm.protocol import LLMProvider
from harness.policy.injection_defense import detect_injection
from harness.policy.pii_filter import PIIFilter


class InjectionDetectedError(Exception):
    """Raised when prompt injection markers found in user content.

    Carries `.markers` (list[str]) for caller to log/surface and
    `.context` (str) for a short call-site label.
    """

    def __init__(self, markers: list[str], context: str = ""):
        self.markers = markers
        self.context = context
        super().__init__(
            f"prompt injection detected ({len(markers)} markers): {markers[:3]}"
            + (f" [{context}]" if context else "")
        )


class PIIFilteringLLM:
    """LLMProvider decorator that redacts PII + denies on injection.

    Forwards to inner provider after gate. Exposes the inner provider's
    last_usage for metrics passthrough.
    """

    def __init__(self, inner: LLMProvider, candidate_names: list[str]):
        self._inner = inner
        self._filter = PIIFilter(known_names=candidate_names)

    @property
    def last_usage(self):
        return getattr(self._inner, "last_usage", None)

    async def call(
        self,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> str:
        # 1. Injection check (user content only — system is trusted code).
        markers = detect_injection(user)
        if markers:
            raise InjectionDetectedError(markers, context="user prompt")

        # 2. Redact PII from BOTH system and user. System may contain
        #    candidate-tag prompts that mention names; redact symmetrically.
        redacted_system, _ = self._filter.redact(system)
        redacted_user, _ = self._filter.redact(user)

        # 3. Delegate. inner.last_usage is set by the inner provider on
        #    success; our property forwards it.
        return await self._inner.call(
            system=redacted_system,
            user=redacted_user,
            max_tokens=max_tokens,
            temperature=temperature,
        )

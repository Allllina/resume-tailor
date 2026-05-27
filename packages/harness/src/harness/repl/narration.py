"""Generate first-person narration string for a run, from its events.

Used by run-summary list and DraftCard rendering. Deterministic; no LLM.
"""
from datetime import datetime, timezone


def humanize_age(created_at_iso: str, now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now(timezone.utc)
    dt = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    secs = (now - dt).total_seconds()
    if secs < 120:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)} min ago"
    if secs < 7200:
        return "1 hour ago"
    if secs < 86400:
        return f"{int(secs // 3600)} hours ago"
    if secs < 86400 * 2:
        return "yesterday"
    if secs < 86400 * 7:
        return dt.strftime("%a")
    return dt.strftime("%b %d")


def lens_label_zh(lens: str | None) -> str:
    return {
        "A_strategy_research": "A 战略研究",
        "B_data_analytics": "B 数据分析",
        "C_product_ops": "C 产品运营",
        "D_finance_markets": "D 金融市场",
        "HC_human_capital": "HC 人力资本",
    }.get(lens or "", "")


def generate_narration(state_dict: dict, now: datetime | None = None) -> str:
    """Build a 1-sentence first-person summary from a persisted state dict.

    state_dict is the harness-tailor-output shape (what assemble_output emits).
    """
    created = state_dict.get("created_at") or datetime.now(timezone.utc).isoformat()
    age = humanize_age(created, now=now)
    lens = (state_dict.get("lens_routing") or {}).get("primary_lens")
    label = lens_label_zh(lens)
    deg = state_dict.get("degradation_events") or []
    if not deg:
        tail = "no issues."
    elif len(deg) == 1:
        tail = f"{deg[0].get('stage', '?')} stage degraded."
    else:
        tail = f"{len(deg)} stages degraded."
    if label:
        return f"I tailored this {age}. {label} lens, {tail}"
    return f"I tailored this {age}. {tail}"

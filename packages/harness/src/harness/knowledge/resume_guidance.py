"""Maps O*NET competency data → resume-specific guidance for the Skill.

This layer translates raw O*NET output (importance-scored skills, knowledge
areas, tech lists) into the structured guidance the Skill needs to:
  - categorise the role (role family + subtype)
  - build the 3-tier keyword architecture
  - apply the right bullet verb patterns and proof hierarchy
  - surface anti-patterns for this role type

No LLM calls — deterministic mapping + rule tables.
"""
from __future__ import annotations

# ── Role family detection ─────────────────────────────────────────────────────
# Maps O*NET SOC major groups + key skill signals to role families.

_SOC_TO_FAMILY: dict[str, tuple[str, str]] = {
    # (family, subtype)
    "15-1252": ("Technology & Engineering", "backend_systems"),
    "15-1211": ("Technology & Engineering", "backend_systems"),
    "15-1243": ("Technology & Engineering", "backend_systems"),
    "15-1244": ("Technology & Engineering", "infrastructure"),
    "15-1231": ("Technology & Engineering", "infrastructure"),
    "15-2051": ("Data & Analytics", "data_science"),
    "15-2041": ("Data & Analytics", "data_science"),
    "15-1253": ("Technology & Engineering", "frontend"),
    "15-1254": ("Technology & Engineering", "frontend"),
    "15-1299": ("Product & Operations", "technical_pm"),
    "11-3021": ("Technology & Engineering", "infrastructure"),
    "13-2051": ("Finance & Investment", "investment_analysis"),
    "13-2052": ("Finance & Investment", "investment_analysis"),
    "11-3031": ("Finance & Investment", "corporate_finance"),
    "13-1161": ("Marketing & Growth", "market_research"),
    "11-2021": ("Marketing & Growth", "brand_strategy"),
    "13-1081": ("Consulting & Strategy", "management_consulting"),
    "11-1011": ("General Management & BD", "general_management"),
    "11-2022": ("General Management & BD", "business_development"),
}

_SKILL_FAMILY_SIGNALS: dict[str, tuple[str, str]] = {
    "Programming": ("Technology & Engineering", "backend_systems"),
    "Systems Analysis": ("Technology & Engineering", "backend_systems"),
    "Mathematics": ("Data & Analytics", "data_science"),
    "Statistical Analysis": ("Data & Analytics", "data_science"),
    "Operations Analysis": ("Consulting & Strategy", "management_consulting"),
    "Judgment and Decision Making": ("Consulting & Strategy", "management_consulting"),
    "Sales and Marketing": ("Marketing & Growth", "brand_strategy"),
    "Economics and Accounting": ("Finance & Investment", "investment_analysis"),
}

# ── Per-family guidance tables ────────────────────────────────────────────────

_FAMILY_GUIDANCE: dict[str, dict] = {
    "Technology & Engineering": {
        "proof_hierarchy": "Technical complexity → Scale/reliability → Business impact",
        "bullet_pattern": "Technical problem → Design decision → Implementation → Outcome (latency/throughput/reliability)",
        "primary_verbs": [
            "Architected", "Designed", "Built", "Implemented", "Optimised",
            "Migrated", "Reduced", "Scaled", "Refactored", "Deployed",
        ],
        "anti_patterns": [
            "Used [tool] to implement [feature]  ← no outcome",
            "Helped the team with backend tasks  ← no ownership",
            "Worked on the codebase  ← no specificity",
        ],
        "quantification_signals": [
            "p99 latency (ms)", "throughput (QPS/RPS)", "uptime / SLA (%)",
            "infra cost saved ($)", "lines of code / test coverage change",
            "deploy frequency", "number of services / users affected",
        ],
        "ats_tip": "Lead with tech stack in skills section; mirror exact tool names from JD.",
    },
    "Data & Analytics": {
        "proof_hierarchy": "Business question → Analytical method → Insight → Decision driven",
        "bullet_pattern": "Metric or business question → Analytical approach → Insight found → Action or impact",
        "primary_verbs": [
            "Modelled", "Analysed", "Built", "Identified", "Forecasted",
            "Designed", "Automated", "Reduced", "Improved", "Delivered",
        ],
        "anti_patterns": [
            "Performed data analysis  ← no method, no outcome",
            "Created dashboards for stakeholders  ← no impact stated",
        ],
        "quantification_signals": [
            "model accuracy / AUC / F1", "prediction lift (%)",
            "time saved (hours/week)", "dataset size (rows/TB)",
            "A/B test uplift (%)", "revenue or cost influenced ($)",
        ],
        "ats_tip": "Include specific tools (SQL, Python, Tableau) and methodology terms (A/B test, regression, NLP).",
    },
    "Product & Operations": {
        "proof_hierarchy": "User problem → Initiative → Ship → Metric outcome",
        "bullet_pattern": "User or business problem → Roadmap decision → Cross-functional execution → Measurable result",
        "primary_verbs": [
            "Launched", "Defined", "Led", "Shipped", "Prioritised",
            "Drove", "Aligned", "Reduced", "Grew", "Owned",
        ],
        "anti_patterns": [
            "Worked with engineers to ship feature  ← no ownership signal",
            "Participated in sprint planning  ← passive framing",
        ],
        "quantification_signals": [
            "DAU/MAU change", "conversion rate (%)", "retention delta (%)",
            "NPS change", "revenue impact ($)", "time-to-ship (days)",
            "team size coordinated", "OKR attainment (%)",
        ],
        "ats_tip": "Include product methodology terms: OKRs, roadmap, PRD, A/B testing, user research.",
    },
    "Finance & Investment": {
        "proof_hierarchy": "Investment thesis / transaction → Analytical work → Recommendation → Outcome",
        "bullet_pattern": "Deal or portfolio context → Analytical contribution → Recommendation → Close or return",
        "primary_verbs": [
            "Modelled", "Analysed", "Led", "Evaluated", "Structured",
            "Executed", "Recommended", "Built", "Closed", "Managed",
        ],
        "anti_patterns": [
            "Assisted with financial modelling  ← no ownership",
            "Supported the deal team  ← too passive for senior roles",
        ],
        "quantification_signals": [
            "deal size ($M)", "portfolio return (IRR / MOIC)",
            "AUM ($)", "model accuracy (vs actuals)",
            "cost reduction ($)", "revenue growth (%)",
        ],
        "ats_tip": "Use deal credentials and credential abbreviations (CFA, DCF, LBO, M&A) verbatim.",
    },
    "Consulting & Strategy": {
        "proof_hierarchy": "Client problem → Framework → Insight → Recommendation → Impact",
        "bullet_pattern": "Client/business problem → Structured approach → Non-obvious insight → Recommendation + adoption",
        "primary_verbs": [
            "Led", "Synthesised", "Developed", "Recommended", "Identified",
            "Structured", "Delivered", "Drove", "Built", "Presented",
        ],
        "anti_patterns": [
            "Helped prepare client deliverables  ← no ownership",
            "Contributed to the project  ← too vague",
        ],
        "quantification_signals": [
            "client revenue / cost impact ($M)", "number of stakeholders",
            "project timeline (weeks)", "team size managed",
            "slide deck pages delivered  ← last resort",
        ],
        "ats_tip": "Use framework terms (MECE, structured problem solving) and client industry terminology.",
    },
    "Marketing & Growth": {
        "proof_hierarchy": "Channel / campaign → Strategy → Execution → Funnel metric",
        "bullet_pattern": "Marketing objective → Strategy or experiment → Execution → Conversion / retention / ROAS metric",
        "primary_verbs": [
            "Grew", "Launched", "Optimised", "Drove", "Executed",
            "Designed", "Built", "Managed", "Increased", "Reduced",
        ],
        "anti_patterns": [
            "Managed social media accounts  ← no outcome",
            "Created content for the brand  ← no impact metric",
        ],
        "quantification_signals": [
            "CAC ($)", "ROAS (x)", "CTR / CVR (%)",
            "MQL / SQL count", "organic traffic growth (%)",
            "campaign budget managed ($)", "subscriber / follower growth",
        ],
        "ats_tip": "Include channel-specific terms: SEO, SEM, CRM, MQL, funnel stage, attribution model.",
    },
    "General Management & BD": {
        "proof_hierarchy": "Business scope → Strategic decision → Execution → P&L or partnership outcome",
        "bullet_pattern": "Scope of responsibility → Strategic initiative → Execution + team → Revenue / partnership result",
        "primary_verbs": [
            "Led", "Built", "Scaled", "Closed", "Drove",
            "Managed", "Launched", "Grew", "Negotiated", "Owned",
        ],
        "anti_patterns": [
            "Responsible for business development  ← duties language",
            "Worked across teams to deliver results  ← no specificity",
        ],
        "quantification_signals": [
            "P&L size ($M)", "team headcount", "revenue growth (%/$)",
            "deal value ($M)", "market share (%)",
            "partnerships closed (#)", "client retention (%)",
        ],
        "ats_tip": "Lead with scope signals: P&L, team size, geographic coverage.",
    },
}

# ── Subtype refinements ───────────────────────────────────────────────────────

_SUBTYPE_NOTES: dict[str, str] = {
    "backend_systems": (
        "Backend / Systems: emphasise latency, throughput, reliability, API design, "
        "system architecture decisions. Tech stack in skills section must match JD exactly."
    ),
    "frontend": (
        "Frontend: emphasise Core Web Vitals, rendering performance, component architecture, "
        "accessibility, design-system collaboration. Include framework versions (React 18, etc.)."
    ),
    "infrastructure": (
        "Infrastructure / DevOps: emphasise uptime SLAs, CI/CD pipeline metrics, "
        "infra cost, deployment frequency, incident response time."
    ),
    "data_science": (
        "Data Science / ML: lead with model outcomes (accuracy, AUC, lift) before methodology. "
        "Include dataset scale and business decision that resulted from the model."
    ),
    "technical_pm": (
        "Technical PM: balance engineering credibility with product ownership. "
        "Show you can write specs AND ship — include engineering collaboration signals."
    ),
    "investment_analysis": (
        "Investment Analysis: deal credentials first, analytical method second. "
        "Always name deal size or AUM. Include credential abbreviations verbatim."
    ),
    "corporate_finance": (
        "Corporate Finance: emphasise forecast accuracy, cost reduction, capital allocation. "
        "Show cross-functional influence — finance business-partnering is a differentiator."
    ),
    "management_consulting": (
        "Management Consulting: MECE structure signals matter. "
        "Emphasise slide output quality, client seniority, and recommendation adoption."
    ),
}


# ── Public API ────────────────────────────────────────────────────────────────

def detect_role_family(soc_code: str, top_skills: list[str]) -> tuple[str, str]:
    """Return (family, subtype) from SOC code, falling back to skill signals."""
    prefix6 = soc_code.replace(".", "")[:7]  # e.g. "15-1252"
    if prefix6 in _SOC_TO_FAMILY:
        return _SOC_TO_FAMILY[prefix6]

    # Fallback: first matching skill signal
    for skill in top_skills:
        if skill in _SKILL_FAMILY_SIGNALS:
            return _SKILL_FAMILY_SIGNALS[skill]

    return ("General Management & BD", "general_management")


def build_keyword_tiers(
    occ_title: str,
    top_skills: list[str],
    top_knowledge: list[str],
    hot_tech: list[str],
    all_tech: list[str],
) -> dict:
    """Build 3-tier keyword architecture from O*NET data.

    Tier 1 — headline + summary (core role identity)
    Tier 2 — bullet-level capability keywords
    Tier 3 — tools / platforms (skills section)
    """
    tier1 = [occ_title] + [s for s in top_skills[:3]]
    tier2 = top_skills[3:10] + [k for k in top_knowledge[:4]]
    tier3 = hot_tech[:10] if hot_tech else all_tech[:10]

    return {
        "tier1_core_identity": tier1,
        "tier2_capability": tier2,
        "tier3_tools": tier3,
    }


def build_resume_guidance(
    soc_code: str,
    occ_title: str,
    top_skills: list[str],
    top_knowledge: list[str],
    hot_tech: list[str],
    all_tech: list[str],
) -> dict:
    """Assemble the full resume guidance block for a given occupation."""
    family, subtype = detect_role_family(soc_code, top_skills)
    base = _FAMILY_GUIDANCE.get(family, _FAMILY_GUIDANCE["General Management & BD"])
    subtype_note = _SUBTYPE_NOTES.get(subtype, "")
    keywords = build_keyword_tiers(occ_title, top_skills, top_knowledge, hot_tech, all_tech)

    return {
        "role_family": family,
        "subtype": subtype,
        "subtype_note": subtype_note,
        "proof_hierarchy": base["proof_hierarchy"],
        "bullet_pattern": base["bullet_pattern"],
        "primary_verbs": base["primary_verbs"],
        "anti_patterns": base["anti_patterns"],
        "quantification_signals": base["quantification_signals"],
        "ats_tip": base["ats_tip"],
        "keyword_tiers": keywords,
    }

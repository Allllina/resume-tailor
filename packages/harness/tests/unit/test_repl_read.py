"""Test REPL Read stage — Tier 1 context assembly."""
from harness.repl.read import assemble_tier1_context


SAMPLE_INDEX = {
    "experiences": [
        {
            "id": "01-kearney",
            "company": "A.T. Kearney",
            "recognition_per_industry": {
                "internet_strategic": {"score": "high"},
            },
            "vertical_fit_per_lens": {
                "C_product_ops": {"score": "adjacent"},
                "A_strategy_research": {"score": "core"},
            },
        },
        {
            "id": "03-desaysv",
            "company": "Desay SV",
            "recognition_per_industry": {
                "internet_strategic": {"score": "low"},
            },
            "vertical_fit_per_lens": {
                "C_product_ops": {"score": "core"},
            },
        },
        {
            "id": "no-relevance",
            "company": "Random",
            "recognition_per_industry": {},
            "vertical_fit_per_lens": {},
        },
    ],
}


def test_returns_dict_with_required_keys():
    ctx = assemble_tier1_context(
        jd_text="some jd",
        master_tex="% master",
        index_slice=SAMPLE_INDEX,
        target_industry="internet_strategic",
        target_lens="C_product_ops",
    )
    assert "jd_text" in ctx
    assert "master_tex" in ctx
    assert "relevant_experiences" in ctx
    assert "target_industry" in ctx
    assert "target_lens" in ctx
    assert "token_budget" in ctx


def test_filters_relevant_experiences():
    """Only experiences with non-null recognition or fit on the targets."""
    ctx = assemble_tier1_context(
        jd_text="x",
        master_tex="x",
        index_slice=SAMPLE_INDEX,
        target_industry="internet_strategic",
        target_lens="C_product_ops",
    )
    relevant_ids = {e["id"] for e in ctx["relevant_experiences"]}
    # Both kearney + desay have signal; no-relevance has neither
    assert "01-kearney" in relevant_ids
    assert "03-desaysv" in relevant_ids
    assert "no-relevance" not in relevant_ids


def test_relevant_experience_includes_score_summaries():
    ctx = assemble_tier1_context(
        jd_text="x",
        master_tex="x",
        index_slice=SAMPLE_INDEX,
        target_industry="internet_strategic",
        target_lens="C_product_ops",
    )
    kearney = next(e for e in ctx["relevant_experiences"] if e["id"] == "01-kearney")
    assert kearney["recognition"] == "high"
    assert kearney["fit"] == "adjacent"


def test_handles_missing_axes_gracefully():
    """An exp with empty recognition/fit dicts should not blow up."""
    ctx = assemble_tier1_context(
        jd_text="x",
        master_tex="x",
        index_slice={"experiences": [
            {"id": "x", "company": "X", "recognition_per_industry": {}, "vertical_fit_per_lens": {}}
        ]},
        target_industry="internet_strategic",
        target_lens="C_product_ops",
    )
    # Filtered out (no signal on either axis)
    assert ctx["relevant_experiences"] == []


def test_default_token_budget_is_8000():
    ctx = assemble_tier1_context(
        jd_text="x",
        master_tex="x",
        index_slice=SAMPLE_INDEX,
        target_industry="internet_strategic",
        target_lens="C_product_ops",
    )
    assert ctx["token_budget"] == 8_000


def test_custom_token_budget():
    ctx = assemble_tier1_context(
        jd_text="x",
        master_tex="x",
        index_slice=SAMPLE_INDEX,
        target_industry="internet_strategic",
        target_lens="C_product_ops",
        token_budget=20_000,
    )
    assert ctx["token_budget"] == 20_000


def test_handles_null_disambiguator_per_industry_gracefully():
    """Some experiences have disambiguator_per_industry: null — should not crash read."""
    idx = {
        "experiences": [
            {
                "id": "x",
                "company": "X",
                "recognition_per_industry": {"internet_strategic": {"score": "high"}},
                "vertical_fit_per_lens": {"C_product_ops": {"score": "core"}},
                "disambiguator_per_industry": None,
            }
        ]
    }
    ctx = assemble_tier1_context(
        jd_text="x",
        master_tex="x",
        index_slice=idx,
        target_industry="internet_strategic",
        target_lens="C_product_ops",
    )
    assert len(ctx["relevant_experiences"]) == 1

import pytest
"""Test R-7 disambiguator lookup + Cat 1/2-only apply rule."""
from harness.tier1.disambiguator import Disambiguator


@pytest.mark.skip(reason="requires user-specific experience data — adapt IDs to your own data after `make seed-sample`")
def test_loads_disambiguator_for_desaysv_internet_strategic(repo_root):
    d = Disambiguator(repo_root)
    text = d.lookup(experience_id="03-desaysv", target_industry="internet_strategic")
    assert text is not None
    assert "汽车电子" in text


def test_returns_none_for_kearney_internet_strategic(repo_root):
    """01-kearney has disambiguator_per_industry: null per index.json (品牌足够强)."""
    d = Disambiguator(repo_root)
    text = d.lookup(experience_id="01-kearney", target_industry="internet_strategic")
    assert text is None


def test_returns_none_for_unknown_experience(repo_root):
    d = Disambiguator(repo_root)
    assert d.lookup(experience_id="99-nonexistent", target_industry="internet_strategic") is None


def test_returns_none_for_unknown_industry(repo_root):
    d = Disambiguator(repo_root)
    assert d.lookup(experience_id="03-desaysv", target_industry="nonexistent_industry") is None


@pytest.mark.skip(reason="requires user-specific experience data — adapt IDs to your own data after `make seed-sample`")
def test_apply_in_cat_1_adds_parenthetical(repo_root):
    """Cat 1 main bullet: disambiguator should be added."""
    d = Disambiguator(repo_root)
    out = d.apply(
        experience_id="03-desaysv",
        target_industry="internet_strategic",
        company_text="德赛西威",
        final_category=1,
    )
    assert "德赛西威" in out
    assert "（" in out and "）" in out  # full-width parens


@pytest.mark.skip(reason="requires user-specific experience data — adapt IDs to your own data after `make seed-sample`")
def test_apply_in_cat_2_adds_parenthetical(repo_root):
    d = Disambiguator(repo_root)
    out = d.apply(
        experience_id="03-desaysv",
        target_industry="internet_strategic",
        company_text="德赛西威",
        final_category=2,
    )
    assert "汽车电子" in out


def test_apply_in_cat_3_does_NOT_add(repo_root):
    """R-7 round 3 fix: backup line (Cat 3) —招聘方 1 秒扫过, 括号被忽略 → 不加."""
    d = Disambiguator(repo_root)
    out = d.apply(
        experience_id="03-desaysv",
        target_industry="internet_strategic",
        company_text="德赛西威",
        final_category=3,
    )
    assert out == "德赛西威"
    assert "汽车电子" not in out


def test_apply_in_cat_4_does_NOT_add(repo_root):
    """Cat 4 (砍) shouldn't appear at all but if asked, return company_text only."""
    d = Disambiguator(repo_root)
    out = d.apply(
        experience_id="03-desaysv",
        target_industry="internet_strategic",
        company_text="德赛西威",
        final_category=4,
    )
    assert out == "德赛西威"


def test_apply_no_disambiguator_returns_company_text(repo_root):
    """Kearney has no disambiguator — return company_text unchanged even at Cat 1."""
    d = Disambiguator(repo_root)
    out = d.apply(
        experience_id="01-kearney",
        target_industry="internet_strategic",
        company_text="科尔尼",
        final_category=1,
    )
    assert out == "科尔尼"

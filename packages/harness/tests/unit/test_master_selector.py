"""Test master selector with fallback policy."""
import pytest
from pathlib import Path
from harness.tier1.master_selector import MasterSelector, MasterSelection, MasterMissingError


def test_selects_C_for_product_ops_lens(repo_root):
    sel = MasterSelector(repo_root)
    result = sel.select(primary_lens="C_product_ops")
    assert isinstance(result, MasterSelection)
    assert result.master_path.exists()
    assert "C_product_ops" in str(result.master_path)
    assert result.fallback_used is False


def test_loads_metadata(repo_root):
    sel = MasterSelector(repo_root)
    result = sel.select(primary_lens="C_product_ops")
    assert isinstance(result.metadata, dict)
    # delivered status should appear (per VERSION_LOG 2026-05-01 ABCD/HC base 拆分)
    assert "status" in result.metadata


def test_selects_A(repo_root):
    sel = MasterSelector(repo_root)
    result = sel.select(primary_lens="A_strategy_research")
    assert "A_strategy_research" in str(result.master_path)


def test_selects_HC(repo_root):
    sel = MasterSelector(repo_root)
    result = sel.select(primary_lens="HC_human_capital")
    # The HC dir is named HC_human_capital_analytics on disk
    assert "HC_human_capital" in str(result.master_path)


def test_selects_B(repo_root):
    sel = MasterSelector(repo_root)
    result = sel.select(primary_lens="B_data_analytics")
    assert "B_data_analytics" in str(result.master_path)


def test_unknown_lens_raises(repo_root):
    sel = MasterSelector(repo_root)
    with pytest.raises((KeyError, MasterMissingError)):
        sel.select(primary_lens="Z_nonexistent")


def test_fallback_when_master_missing(tmp_path):
    """If primary lens has no resume.zh.tex, fall back to a sibling that does."""
    versions = tmp_path / "assets" / "resume-bank" / "versions"
    versions.mkdir(parents=True)

    # A_strategy_research — has tex (delivered)
    a_dir = versions / "A_strategy_research"
    a_dir.mkdir()
    (a_dir / "resume.zh.tex").write_text("% A master")
    (a_dir / "metadata.json").write_text('{"status": "delivered"}')

    # D_finance_markets — only metadata, planned
    d_dir = versions / "D_finance_markets"
    d_dir.mkdir()
    (d_dir / "metadata.json").write_text('{"status": "planned"}')

    sel = MasterSelector(tmp_path)
    result = sel.select(primary_lens="D_finance_markets")
    assert result.fallback_used is True
    assert result.master_path.exists()
    # Fell back to A
    assert "A_strategy_research" in str(result.master_path)


def test_no_master_anywhere_raises(tmp_path):
    versions = tmp_path / "assets" / "resume-bank" / "versions"
    versions.mkdir(parents=True)
    sel = MasterSelector(tmp_path)
    with pytest.raises(MasterMissingError):
        sel.select(primary_lens="A_strategy_research")


# ---------- Wave 4 C.1.3 multi-lens priority chain ----------


def _seed_versions_dir(repo_root: Path) -> None:
    """Seed a project versions/ tree with one valid lens master so the
    fallback paths have something to land on."""
    versions = repo_root / "assets" / "resume-bank" / "versions"
    versions.mkdir(parents=True)
    a_dir = versions / "A_strategy_research"
    a_dir.mkdir()
    (a_dir / "resume.zh.tex").write_text("% A project sample")
    (a_dir / "metadata.json").write_text('{"status": "delivered"}')
    c_dir = versions / "C_product_ops"
    c_dir.mkdir()
    (c_dir / "resume.zh.tex").write_text("% C project sample")
    (c_dir / "metadata.json").write_text('{"status": "delivered"}')


def test_per_lens_master_takes_priority_over_legacy(tmp_path):
    """When both <user_dir>/masters/<lens>/master.tex and <user_dir>/master.tex
    exist, the per-lens master wins."""
    _seed_versions_dir(tmp_path)
    user_dir = tmp_path / "user-x"
    (user_dir / "masters" / "C_product_ops").mkdir(parents=True)
    (user_dir / "masters" / "C_product_ops" / "master.tex").write_text(
        "% per-lens C master"
    )
    (user_dir / "masters" / "C_product_ops" / "generated_at.txt").write_text(
        "2026-05-07T01:00:00+00:00"
    )
    (user_dir / "masters" / "C_product_ops" / "generation_method.txt").write_text(
        "rewrite_from_upload_and_bank"
    )
    (user_dir / "master.tex").write_text("% legacy single master")

    sel = MasterSelector(tmp_path, user_dir=user_dir)
    result = sel.select(primary_lens="C_product_ops")
    assert result.master_path.read_text() == "% per-lens C master"
    assert result.metadata["source"] == "user_uploaded_per_lens"
    assert result.metadata["lens"] == "C_product_ops"
    assert result.metadata["generated_at"] == "2026-05-07T01:00:00+00:00"
    assert result.metadata["generation_method"] == "rewrite_from_upload_and_bank"
    assert result.fallback_used is False


def test_legacy_single_master_fallback_when_per_lens_absent(tmp_path):
    """When <user_dir>/masters/<lens>/ is empty but <user_dir>/master.tex
    exists, MasterSelector returns the legacy master with the new source enum."""
    _seed_versions_dir(tmp_path)
    user_dir = tmp_path / "user-y"
    user_dir.mkdir()
    (user_dir / "master.tex").write_text("% legacy single master")

    sel = MasterSelector(tmp_path, user_dir=user_dir)
    result = sel.select(primary_lens="C_product_ops")
    assert result.master_path.read_text() == "% legacy single master"
    assert result.metadata["source"] == "user_uploaded_legacy"
    assert result.metadata["lens"] == "C_product_ops"
    assert result.fallback_used is False


def test_project_lens_sample_when_no_user_master(tmp_path):
    """Empty user_dir → fall through to assets/resume-bank/versions/<lens>/.

    D11 update: `_seed_versions_dir` writes resume.zh.tex (the private real
    master). With the D11 priority chain that's now `project_master` rather
    than `project_sample`.
    """
    _seed_versions_dir(tmp_path)
    user_dir = tmp_path / "user-z"
    user_dir.mkdir()  # empty: no master, no masters/ subdir

    sel = MasterSelector(tmp_path, user_dir=user_dir)
    result = sel.select(primary_lens="C_product_ops")
    assert "C_product_ops" in str(result.master_path)
    assert result.metadata["source"] == "project_master"
    assert result.fallback_used is False


def test_project_sibling_fallback_when_primary_sample_missing(tmp_path):
    """User has nothing; project lens master missing for primary; sibling
    has a sample → fallback_used=True with project_sample_fallback source."""
    versions = tmp_path / "assets" / "resume-bank" / "versions"
    versions.mkdir(parents=True)
    # Only A is seeded; C is empty
    a_dir = versions / "A_strategy_research"
    a_dir.mkdir()
    (a_dir / "resume.zh.tex").write_text("% A project sample")
    (a_dir / "metadata.json").write_text('{"status": "delivered"}')
    (versions / "C_product_ops").mkdir()
    (versions / "C_product_ops" / "metadata.json").write_text('{"status": "planned"}')

    user_dir = tmp_path / "user-w"
    user_dir.mkdir()

    sel = MasterSelector(tmp_path, user_dir=user_dir)
    result = sel.select(primary_lens="C_product_ops")
    assert result.fallback_used is True
    assert "A_strategy_research" in str(result.master_path)
    assert result.metadata["source"] == "project_sample_fallback"


# ---------- D11 sample-aware path resolution ----------


def test_project_master_takes_priority_over_sample(tmp_path):
    """Both resume.zh.tex AND resume.sample.zh.tex present →
    project_master wins (private real seed beats sample sibling)."""
    versions = tmp_path / "assets" / "resume-bank" / "versions"
    versions.mkdir(parents=True)
    c_dir = versions / "C_product_ops"
    c_dir.mkdir()
    (c_dir / "resume.zh.tex").write_text("% C private real")
    (c_dir / "resume.sample.zh.tex").write_text("% C committed sample")
    (c_dir / "metadata.json").write_text('{"status": "delivered"}')
    (c_dir / "metadata.sample.json").write_text(
        '{"version": "sample-1.0", "sample": true}'
    )

    sel = MasterSelector(tmp_path)
    result = sel.select(primary_lens="C_product_ops")
    assert result.master_path.read_text() == "% C private real"
    assert result.metadata["source"] == "project_master"
    assert result.fallback_used is False


def test_project_sample_when_only_sample_present(tmp_path):
    """Only resume.sample.zh.tex present (fresh-clone state) →
    project_sample with sample metadata."""
    versions = tmp_path / "assets" / "resume-bank" / "versions"
    versions.mkdir(parents=True)
    c_dir = versions / "C_product_ops"
    c_dir.mkdir()
    (c_dir / "resume.sample.zh.tex").write_text("% C committed sample")
    (c_dir / "metadata.sample.json").write_text(
        '{"version": "sample-1.0", "lens_label": "C_product_ops", "sample": true}'
    )

    sel = MasterSelector(tmp_path)
    result = sel.select(primary_lens="C_product_ops")
    assert result.master_path.read_text() == "% C committed sample"
    assert result.metadata["source"] == "project_sample"
    assert result.metadata.get("sample") is True
    assert result.fallback_used is False


def test_sibling_fallback_prefers_sample(tmp_path):
    """Primary lens missing entirely; sibling has a sample;
    fallback should resolve to the sibling sample with the
    project_sample_fallback enum."""
    versions = tmp_path / "assets" / "resume-bank" / "versions"
    versions.mkdir(parents=True)
    a_dir = versions / "A_strategy_research"
    a_dir.mkdir()
    (a_dir / "resume.sample.zh.tex").write_text("% A committed sample")
    (a_dir / "metadata.sample.json").write_text('{"sample": true}')
    (versions / "C_product_ops").mkdir()  # primary lens empty

    sel = MasterSelector(tmp_path)
    result = sel.select(primary_lens="C_product_ops")
    assert result.fallback_used is True
    assert result.master_path.read_text() == "% A committed sample"
    assert result.metadata["source"] == "project_sample_fallback"


def test_legacy_user_master_path_kwarg_still_works(tmp_path):
    """Backward-compat: `user_master_path=` (Wave 2.7) keeps the old
    metadata.source = "user_uploaded" enum so existing callers continue
    to map to "custom" via planning.py."""
    _seed_versions_dir(tmp_path)
    legacy = tmp_path / "legacy-master.tex"
    legacy.write_text("% legacy supplied via user_master_path")

    sel = MasterSelector(tmp_path, user_master_path=legacy)
    result = sel.select(primary_lens="C_product_ops")
    assert result.master_path == legacy
    assert result.metadata["source"] == "user_uploaded"

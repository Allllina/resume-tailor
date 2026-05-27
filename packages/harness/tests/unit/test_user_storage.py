"""Unit tests for harness.users.storage."""
import json
from pathlib import Path

import pytest

from harness.users.storage import (
    InvalidLensError,
    InvalidUserIdError,
    UserStorage,
)


@pytest.fixture
def storage(tmp_path):
    return UserStorage(tmp_path)


def test_validate_user_id_accepts_uuid(storage):
    storage.user_dir("550e8400-e29b-41d4-a716-446655440000")  # no raise


def test_validate_user_id_accepts_slug(storage):
    storage.user_dir("default")  # no raise


def test_validate_user_id_rejects_empty(storage):
    with pytest.raises(InvalidUserIdError):
        storage.user_dir("")


def test_validate_user_id_rejects_path_traversal(storage):
    for bad in ["../etc/passwd", "..", "../user", "/abs", "user/../other", "user with space"]:
        with pytest.raises(InvalidUserIdError):
            storage.user_dir(bad)


def test_validate_user_id_rejects_uppercase(storage):
    with pytest.raises(InvalidUserIdError):
        storage.user_dir("JINGWEN")


def test_save_load_profile_roundtrip(storage):
    storage.save_profile("user-a", {
        "user_id": "user-a",
        "created_at": "2026-05-06T12:00:00Z",
        "candidate_names": ["Alice"],
    })
    loaded = storage.load_profile("user-a")
    assert loaded is not None
    assert loaded["user_id"] == "user-a"
    assert loaded["candidate_names"] == ["Alice"]
    assert "last_updated" in loaded


def test_load_profile_returns_none_when_missing(storage):
    assert storage.load_profile("not-yet") is None


def test_has_profile_toggles(storage):
    assert not storage.has_profile("user-b")
    storage.save_profile("user-b", {
        "user_id": "user-b",
        "created_at": "2026-05-06T12:00:00Z",
        "candidate_names": ["Bob"],
    })
    assert storage.has_profile("user-b")


def test_save_master_writes_tex(storage):
    path = storage.save_master("user-c", r"\documentclass{article}\begin{document}hi\end{document}", "tex")
    assert path.name == "master.tex"
    assert path.exists()
    assert "documentclass" in path.read_text()
    assert storage.has_master("user-c")


def test_get_master_tex_raises_when_missing(storage):
    with pytest.raises(FileNotFoundError):
        storage.get_master_tex("nobody")


def test_add_and_list_experiences(storage):
    eid1 = storage.add_experience("user-d", "exp1.md", "# Project 1\n\ncontent")
    eid2 = storage.add_experience("user-d", "exp2.md", "# Project 2")
    items = storage.list_experiences("user-d")
    assert len(items) == 2
    ids = {e["id"] for e in items}
    assert {eid1, eid2} == ids
    assert all("file_name" in e and "uploaded_at" in e for e in items)


def test_list_experiences_empty_when_no_index(storage):
    storage.ensure_user_dir("user-e")
    assert storage.list_experiences("user-e") == []


def test_remove_experience(storage):
    eid = storage.add_experience("user-f", "exp.md", "content")
    assert storage.remove_experience("user-f", eid) is True
    assert storage.list_experiences("user-f") == []
    # file gone
    assert not (storage.user_dir("user-f") / "experiences" / f"{eid}.md").exists()


def test_remove_experience_returns_false_when_not_found(storage):
    storage.add_experience("user-g", "x.md", "y")
    assert storage.remove_experience("user-g", "no-such-id") is False


def test_get_experience_content_roundtrip(storage):
    eid = storage.add_experience("user-h", "x.md", "the content here")
    assert storage.get_experience_content("user-h", eid) == "the content here"
    assert storage.get_experience_content("user-h", "missing") is None


def test_runs_dir_creates_and_returns(storage):
    rd = storage.runs_dir("user-i")
    assert rd.exists()
    assert rd.is_dir()
    assert rd.name == "runs"


def test_save_profile_atomic_no_partial_write(storage, monkeypatch):
    """Smoke: verify rename-based atomicity by checking final file exists, no .tmp residue."""
    storage.save_profile("user-j", {
        "user_id": "user-j",
        "created_at": "2026-05-06T12:00:00Z",
        "candidate_names": ["X"],
    })
    d = storage.user_dir("user-j")
    files = sorted(p.name for p in d.iterdir() if p.is_file())
    assert "profile.json" in files
    assert not any(f.endswith(".tmp") for f in files)


# ---------- per-lens master methods (Wave 4 C.1 multi-lens onboarding) ----------


def test_add_lens_master_writes_files(storage):
    path = storage.add_lens_master(
        "user-lm",
        "C_product_ops",
        "% per-lens master content",
        "user_upload",
    )
    assert path.name == "master.tex"
    assert path.exists()
    assert "per-lens master" in path.read_text()
    sibling = path.parent
    assert (sibling / "generated_at.txt").exists()
    assert (sibling / "generation_method.txt").read_text().strip() == "user_upload"


def test_add_lens_master_rejects_unknown_lens(storage):
    with pytest.raises(InvalidLensError):
        storage.add_lens_master("user-lm-bad", "Z_made_up", "x", "user_upload")


def test_add_lens_master_rejects_bad_method(storage):
    with pytest.raises(ValueError):
        storage.add_lens_master("user-lm-bad-m", "A_strategy_research", "x", "weird")


def test_has_lens_master_toggles(storage):
    assert storage.has_lens_master("user-h", "B_data_analytics") is False
    storage.add_lens_master(
        "user-h",
        "B_data_analytics",
        "% B master",
        "rewrite_from_upload_and_bank",
    )
    assert storage.has_lens_master("user-h", "B_data_analytics") is True
    # Unknown lens → False (no raise)
    assert storage.has_lens_master("user-h", "Z_made_up") is False


def test_get_lens_master_path_returns_path(storage):
    assert storage.get_lens_master_path("u-glm", "A_strategy_research") is None
    storage.add_lens_master(
        "u-glm", "A_strategy_research", "% A", "user_upload"
    )
    p = storage.get_lens_master_path("u-glm", "A_strategy_research")
    assert p is not None
    assert p.exists() and p.name == "master.tex"


def test_list_lens_masters_returns_inventory(storage):
    storage.add_lens_master(
        "u-list", "A_strategy_research", "% A", "user_upload"
    )
    storage.add_lens_master(
        "u-list", "C_product_ops", "% C", "rewrite_from_upload_and_bank"
    )
    inv = storage.list_lens_masters("u-list")
    assert set(inv.keys()) == {"A_strategy_research", "C_product_ops"}
    assert inv["A_strategy_research"]["method"] == "user_upload"
    assert inv["C_product_ops"]["method"] == "rewrite_from_upload_and_bank"
    # Each entry carries an existing path
    for entry in inv.values():
        assert entry["path"].exists()
        assert entry["generated_at"]  # non-empty ISO string


def test_list_lens_masters_empty_when_no_dir(storage):
    storage.ensure_user_dir("u-empty-list")
    assert storage.list_lens_masters("u-empty-list") == {}


def test_list_lens_masters_skips_unknown_dirs(storage):
    """A stray non-enum directory under masters/ must be ignored."""
    storage.add_lens_master(
        "u-junk", "A_strategy_research", "% A", "user_upload"
    )
    base = storage.user_dir("u-junk") / "masters"
    (base / "junk-dir").mkdir()
    (base / "junk-dir" / "master.tex").write_text("% junk")
    inv = storage.list_lens_masters("u-junk")
    assert "junk-dir" not in inv
    assert "A_strategy_research" in inv


def test_remove_lens_master(storage):
    storage.add_lens_master(
        "u-rm", "D_finance_markets", "% D", "user_upload"
    )
    assert storage.remove_lens_master("u-rm", "D_finance_markets") is True
    assert storage.has_lens_master("u-rm", "D_finance_markets") is False
    assert storage.remove_lens_master("u-rm", "D_finance_markets") is False


def test_lens_dir_path_traversal_blocked(storage):
    """The lens enum is a closed set — `..` would not match any member."""
    with pytest.raises(InvalidLensError):
        storage.add_lens_master("u-trav", "..", "x", "user_upload")

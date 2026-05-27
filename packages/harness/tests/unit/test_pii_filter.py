"""Test PII redaction + restoration.

Per HARNESS_COMPLIANCE_AUDIT.md Gap 1 (HIGH SEVERITY).
"""
from harness.policy.pii_filter import PIIFilter, PIIToken


def test_redacts_chinese_phone():
    f = PIIFilter()
    redacted, mapping = f.redact("Call me at +86 138-2316-6715 or 13823166715")
    assert "138-2316-6715" not in redacted
    assert "13823166715" not in redacted
    assert any(t.kind == "PHONE" for t in mapping)


def test_redacts_us_phone():
    f = PIIFilter()
    redacted, mapping = f.redact("US line: +1 929-791-3436")
    assert "929-791-3436" not in redacted
    assert any(t.kind == "PHONE" for t in mapping)


def test_redacts_email():
    f = PIIFilter()
    redacted, mapping = f.redact("Contact jwchen2024@outlook.com for details")
    assert "jwchen2024@outlook.com" not in redacted
    assert any(t.kind == "EMAIL" for t in mapping)


def test_redacts_full_name():
    f = PIIFilter(known_names=["张明", "Zhang Ming"])
    redacted, mapping = f.redact("张明 has worked at Mercer")
    assert "张明" not in redacted
    assert "[CANDIDATE_NAME]" in redacted


def test_restore_round_trip():
    f = PIIFilter(known_names=["张明"])
    original = "张明, +86 138-2316-6715, jwchen2024@outlook.com"
    redacted, mapping = f.redact(original)
    restored = f.restore(redacted, mapping)
    assert restored == original


def test_does_not_redact_company_names():
    f = PIIFilter(known_names=["张明"])
    text = "Worked at 美世咨询 (Mercer Consulting) and 科尔尼"
    redacted, _ = f.redact(text)
    assert "美世咨询" in redacted
    assert "Mercer Consulting" in redacted
    assert "科尔尼" in redacted


def test_redact_empty_text():
    f = PIIFilter(known_names=["张明"])
    redacted, mapping = f.redact("")
    assert redacted == ""
    assert mapping == []


def test_redact_no_pii():
    f = PIIFilter(known_names=["张明"])
    text = "This text has no PII at all."
    redacted, mapping = f.redact(text)
    assert redacted == text
    assert mapping == []


def test_multiple_phones_get_distinct_placeholders():
    f = PIIFilter()
    redacted, mapping = f.redact("CN: +86 138-2316-6715. US: +1 929-791-3436.")
    # Two distinct placeholders, both restored correctly
    assert "[PHONE_1]" in redacted
    assert "[PHONE_2]" in redacted
    assert len([t for t in mapping if t.kind == "PHONE"]) == 2


def test_longer_name_takes_precedence():
    """If known_names = ['陈', '张明'], '张明 ate' should redact 张明 not 陈."""
    f = PIIFilter(known_names=["陈", "张明"])
    redacted, mapping = f.redact("张明 ate dinner")
    # '张明' should be the redacted span, not just '陈'
    candidate_tokens = [t for t in mapping if t.kind == "CANDIDATE_NAME"]
    assert any(t.original == "张明" for t in candidate_tokens)


def test_C1_name_substring_in_email_does_not_leak():
    """C-1: name substring overlapping email local-part must not leak email digits/chars to LLM."""
    f = PIIFilter(known_names=["mingsample"])
    redacted, mapping = f.redact("Email: mingsamplealina@gmail.com")
    # Email must be FULLY redacted (not partially)
    assert "alina@gmail.com" not in redacted
    assert "@gmail.com" not in redacted
    # Either email is detected as EMAIL token, or as part of CANDIDATE_NAME — but the
    # full address must not appear in plain text in the redacted output
    assert any(t.kind == "EMAIL" for t in mapping)


def test_C2_duplicate_phone_handled():
    """C-2: same phone appearing twice gets two distinct placeholders, both restorable."""
    f = PIIFilter()
    text = "Primary: +86 138-2316-6715. Backup: +86 138-2316-6715."
    redacted, mapping = f.redact(text)
    assert "138-2316-6715" not in redacted
    assert "[PHONE_1]" in redacted
    assert "[PHONE_2]" in redacted
    restored = f.restore(redacted, mapping)
    assert restored == text


def test_I1_us_parenthesized_phone():
    f = PIIFilter()
    redacted, mapping = f.redact("US: (929) 791-3436")
    assert "929" not in redacted
    assert "791-3436" not in redacted
    assert any(t.kind == "PHONE" for t in mapping)


def test_I1_hk_phone():
    f = PIIFilter()
    redacted, mapping = f.redact("HK office: +852 9123 4567")
    assert "9123 4567" not in redacted
    assert "9123" not in redacted
    assert any(t.kind == "PHONE" for t in mapping)


def test_I3_latin_name_uses_word_boundary():
    """I-3: Latin-script name 'Chen' must NOT match inside English company name 'Chenel'."""
    f = PIIFilter(known_names=["Chen"])
    redacted, _ = f.redact("Worked at Chenel and Chevron, mentored by Chen")
    # 'Chen' as standalone word redacted
    # but 'Chenel' / 'Chevron' preserved as company signal
    assert "Chenel" in redacted
    assert "Chevron" in redacted
    # The standalone Chen got redacted
    assert "mentored by [CANDIDATE_NAME]" in redacted


def test_I3_cjk_name_no_word_boundary():
    """CJK names continue to match without word boundaries (Chinese has no \\b)."""
    f = PIIFilter(known_names=["张明"])
    redacted, _ = f.redact("候选人张明曾在Mercer工作。")
    assert "张明" not in redacted
    assert "[CANDIDATE_NAME]" in redacted
    # Companies preserved
    assert "Mercer" in redacted

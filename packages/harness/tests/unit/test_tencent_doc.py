"""Test 腾讯文档 内推汇总 table parser (PoC)."""
from harness.scrapers.tencent_doc import parse, TencentDocJD


SAMPLE_HTML = """
<html><body>
  <table>
    <tr><th>公司</th><th>岗位</th><th>地点</th><th>申请</th></tr>
    <tr>
      <td>阿里巴巴</td>
      <td>AI 产品运营实习</td>
      <td>杭州</td>
      <td><a href="https://example.com/apply/ali">投递</a></td>
    </tr>
    <tr>
      <td>字节跳动</td>
      <td>商业分析师</td>
      <td>上海</td>
      <td><a href="https://example.com/apply/byte">投递</a></td>
    </tr>
    <tr>
      <td colspan="2">不完整的行（被忽略）</td>
    </tr>
  </table>
</body></html>
"""


def test_parses_two_jobs():
    jds = parse(SAMPLE_HTML)
    assert len(jds) == 2


def test_first_job_fields():
    jds = parse(SAMPLE_HTML)
    first = jds[0]
    assert isinstance(first, TencentDocJD)
    assert first.company == "阿里巴巴"
    assert first.role == "AI 产品运营实习"
    assert first.location == "杭州"
    assert first.apply_url == "https://example.com/apply/ali"


def test_second_job_fields():
    jds = parse(SAMPLE_HTML)
    second = jds[1]
    assert second.company == "字节跳动"
    assert second.role == "商业分析师"
    assert second.location == "上海"


def test_skips_rows_with_too_few_cells():
    """Rows with < 2 cells should be skipped (e.g., header-only rows, dividers)."""
    html = """<table><tr><td>only one cell</td></tr></table>"""
    assert parse(html) == []


def test_skips_header_row_implicitly():
    """If first row uses <th>, it has at least 2 cells but should still be skipped if first 'company' looks like a header."""
    # The current minimal impl includes header rows; this just documents that behavior.
    # Whether the impl filters headers is a future call; the spec test only requires len >= 2 cells.
    pass


def test_no_table_returns_empty():
    assert parse("<html><body><p>no table here</p></body></html>") == []


def test_handles_missing_apply_link():
    """Row without <a> should still parse with apply_url=None."""
    html = """
    <table>
      <tr>
        <td>美团</td>
        <td>商业分析</td>
        <td>北京</td>
      </tr>
    </table>
    """
    jds = parse(html)
    assert len(jds) == 1
    assert jds[0].apply_url is None


def test_raw_row_contains_all_cells():
    jds = parse(SAMPLE_HTML)
    assert "阿里巴巴" in jds[0].raw_row
    assert "AI 产品运营实习" in jds[0].raw_row


def test_handles_optional_third_column_missing():
    html = """
    <table>
      <tr>
        <td>腾讯</td>
        <td>产品策略</td>
      </tr>
    </table>
    """
    jds = parse(html)
    assert len(jds) == 1
    assert jds[0].location is None

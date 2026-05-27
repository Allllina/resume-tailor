"""腾讯文档 内推汇总 parser (PoC).

Per JobHunter-Agent技术思路.md and 2026-05-04 user direction:
不爬招聘网站, 爬腾讯文档共享 doc (各种学生 / 自媒体整理的内推汇总).
腾讯文档 table 结构相对稳定, BeautifulSoup 即可.

Wave 1 PoC: minimal table parser. Real腾讯文档 export HTML may have
nested div containers we'll iterate on in Wave 3 against fixtures.
"""
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup


@dataclass
class TencentDocJD:
    company: str
    role: str
    location: Optional[str]
    apply_url: Optional[str]
    raw_row: str


def parse(html: str) -> list[TencentDocJD]:
    """Parse 腾讯文档 web-view HTML into a list of JD candidates.

    Heuristic: each <tr> with >= 2 cells (<td> or <th>) becomes one JD;
    cell[0]=公司, cell[1]=岗位, cell[2]=地点 (optional). First <a href> in
    the row becomes apply_url.
    """
    soup = BeautifulSoup(html, "lxml")
    jobs: list[TencentDocJD] = []

    for row in soup.select("tr"):
        cell_tags = row.find_all(["td", "th"])
        cells = [c.get_text(strip=True) for c in cell_tags]
        if len(cells) < 2:
            continue

        # Skip pure-header rows (all cells are <th>) — 腾讯文档 tables
        # typically use <th> only for the header row. Data rows use <td>.
        if all(c.name == "th" for c in cell_tags):
            continue

        company = cells[0]
        role = cells[1]
        if not company or not role:
            continue

        location = cells[2] if len(cells) > 2 and cells[2] else None

        # Find first <a href=...> in this row
        link = row.find("a", href=True)
        apply_url = link["href"] if link else None

        jobs.append(TencentDocJD(
            company=company,
            role=role,
            location=location,
            apply_url=apply_url,
            raw_row=" | ".join(cells),
        ))

    return jobs

"""BCB document scraper: search, parse, and iterate over regulatory documents."""

import calendar
import time
from dataclasses import dataclass
from datetime import date
from typing import Iterator

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

BCB_SEARCH_API = "https://www.bcb.gov.br/api/search/app/normativos/buscanormativos"

IN_SCOPE_TYPES = frozenset({
    "Resolução BCB",
    "Resolução CMN",
    "Resolução Conjunta",
})

_HEADERS = {
    "User-Agent": "regulens-research/0.1 (thiago18coutinho@gmail.com)",
    "Accept": "application/json",
}

@dataclass(frozen=True)
class BcbDocument:
    doc_type: str
    number: int
    date_iso: str
    title: str
    summary: str
    list_item_id: str
    is_revoked: bool
    is_cancelled: bool
    responsible_dept: str

    def __post_init__(self) -> None:
        if not self.list_item_id:
            raise ValueError("list_item_id required")
        if self.number <= 0:
            raise ValueError(f"number must be positive, got {self.number}")


def _strip_html(text: str | None) -> str:
    """Return plain text from an HTML string, or empty string for None/empty."""
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)


def _parse_row(row: dict) -> BcbDocument:
    """Map a single JSON search result row to a BcbDocument."""
    return BcbDocument(
        doc_type=row["TipodoNormativoOWSCHCS"],
        number=int(float(row["NumeroOWSNMBR"])),
        date_iso=row["data"],
        title=row["title"],
        summary=_strip_html(row.get("AssuntoNormativoOWSMTXT")),
        list_item_id=row["listItemId"],
        is_revoked=row.get("RevogadoOWSBOOL", "0") == "1",
        is_cancelled=row.get("CanceladoOWSBOOL", "0") == "1",
        responsible_dept=row.get("ResponsavelOWSText", ""),
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=30),
    retry=retry_if_exception_type(httpx.HTTPError),
)
def fetch_search_page(
    start_date: str,
    end_date: str,
    startrow: int,
    rowlimit: int = 15,
) -> dict:
    """Fetch one page of BCB normativo search results."""
    refinement = (
        f"Data:range("
        f"datetime({start_date}),"
        f"datetime({end_date}T23:59:59)"
        f")"
    )
    params = {
        "querytext": "ContentType:normativo AND contentSource:normativos",
        "rowlimit": rowlimit,
        "startrow": startrow,
        "sortlist": "Data1OWSDATE:descending",
        "refinementfilters": refinement,
    }
    response = httpx.get(BCB_SEARCH_API, params=params, headers=_HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def iter_month(year: int, month: int, rowlimit: int = 15) -> Iterator[BcbDocument]:
    """Yield all in-scope documents published in the given year/month."""
    last_day = calendar.monthrange(year, month)[1]
    start_str = date(year, month, 1).isoformat()
    end_str = date(year, month, last_day).isoformat()

    startrow = 0
    total_rows: int | None = None

    while total_rows is None or startrow < total_rows:
        data = fetch_search_page(start_str, end_str, startrow, rowlimit)
        total_rows = data.get("TotalRows", 0)

        for row in data.get("Rows", []):
            if row.get("TipodoNormativoOWSCHCS") not in IN_SCOPE_TYPES:
                continue
            yield _parse_row(row)

        startrow += rowlimit
        if startrow < total_rows:
            time.sleep(2)


def iter_search_results(start_year: int, end_year: int) -> Iterator[BcbDocument]:
    """Yield all in-scope documents for every month in [start_year, end_year]."""
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            yield from iter_month(year, month)
            time.sleep(2)

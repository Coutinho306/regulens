"""BCB JSON API spike: confirm the search endpoint returns usable JSON.

Saves the response to sample_api_response.json (gitignored) for inspection.
"""

import json

import httpx

BCB_SEARCH_API = "https://www.bcb.gov.br/api/search/app/normativos/buscanormativos"


def fetch_bcb_search(
    start_date: str,
    end_date: str,
    startrow: int = 0,
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
    headers = {
        "User-Agent": "regulens-research/0.1 (thiago18coutinho@gmail.com)",
        "Accept": "application/json",
    }
    response = httpx.get(BCB_SEARCH_API, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    data = fetch_bcb_search("2026-04-21", "2026-04-24")
    with open("sample_api_response.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"TotalRows: {data.get('TotalRows')}")
    print(f"RowCount:  {data.get('RowCount')}")
    if data.get("Rows"):
        print(f"First row title: {data['Rows'][0]['title']}")
    else:
        print("No rows")

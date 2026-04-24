"""One-shot spike: fetch BCB search page and save raw HTML."""

import httpx

URL = "https://www.bcb.gov.br/estabilidadefinanceira/buscanormas"
PARAMS = {
    "conteudo": "Circular",
    "dataInicioBusca": "01/01/2025",
    "dataFimBusca": "31/12/2025",
    "tipoDocumento": "Todos",
}
HEADERS = {
    "User-Agent": "regulens-research/0.1 (thiago18coutinho@gmail.com)",
    "Accept": "text/html",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}
OUTPUT_FILE = "sample_response.html"


def main() -> None:
    print(f"Fetching {URL} ...")
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(URL, params=PARAMS, headers=HEADERS)

    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        raise RuntimeError(f"Unexpected status {response.status_code}: {response.text[:200]}")

    html = response.text
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"Saved {len(response.content):,} bytes → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

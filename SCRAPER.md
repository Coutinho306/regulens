# BCB Scraper

## Source

Banco Central do Brasil (BCB) — public normative documents search.

The public search page at `https://www.bcb.gov.br/estabilidadefinanceira/buscanormas` is a client-side rendered Angular SPA. The served HTML is an empty shell (`<app-root></app-root>`); results are fetched from a SharePoint-backed JSON API after the JavaScript bundle executes.

We bypass the HTML entirely and hit the underlying JSON search API directly. This is faster, more reliable, and less brittle than headless-browser scraping.

## Search endpoint

```
GET https://www.bcb.gov.br/api/search/app/normativos/buscanormativos
```

### Query parameters

| Parameter | Value | Notes |
|---|---|---|
| `querytext` | `ContentType:normativo AND contentSource:normativos` | Always this exact string |
| `rowlimit` | `15` (default) | Page size; can be increased |
| `startrow` | `0` | Pagination offset |
| `sortlist` | `Data1OWSDATE:descending` | Newest first |
| `refinementfilters` | `Data:range(datetime(YYYY-MM-DD),datetime(YYYY-MM-DDT23:59:59))` | Date range filter |

### Request headers

```
User-Agent: regulens-research/0.1 (thiago18coutinho@gmail.com)
Accept:     application/json
```

### Gotchas

- **`T23:59:59` on end date is required.** Without it, the filter snaps to midnight and excludes that day's documents.
- URL-encode via the HTTP library's params argument. Do not build the query string manually — `refinementfilters` contains `:`, `(`, `)` which all need encoding.

## Response schema

```jsonc
{
  "TotalRows": 31,       // total matches for this query (global, not page)
  "RowCount": 15,        // items in this page
  "Rows": [
    {
      "title": "Resolução BCB N° 559",
      "TipodoNormativoOWSCHCS": "Resolução BCB",
      "NumeroOWSNMBR": "559.000000000000",
      "data": "2026-04-23T21:00:11Z",
      "AssuntoNormativoOWSMTXT": "Altera o regulamento...",
      "listItemId": "52875",
      "RevogadoOWSBOOL": "0",
      "CanceladoOWSBOOL": "0",
      "ResponsavelOWSText": "SECRE"
      // (other fields ignored)
    }
  ],
  "Refiners": { /* facet counts, ignored */ }
}
```

### Field meanings

| Field | Type | Notes |
|---|---|---|
| `title` | str | Document title (redundant — includes type + number) |
| `TipodoNormativoOWSCHCS` | str | Clean document type. Use for filtering. |
| `NumeroOWSNMBR` | str | Number as weird decimal string. Parse with `int(float(x))`. |
| `data` | str | ISO 8601 timestamp, UTC |
| `AssuntoNormativoOWSMTXT` | str | Description; **may contain wrapped HTML** (`<div class="ExternalClass...">...</div>`). Strip before use. |
| `listItemId` | str | Internal SharePoint item ID. Used to fetch the full document (see below). |
| `RevogadoOWSBOOL` | `"0"` or `"1"` | String, not bool. Revoked flag. |
| `CanceladoOWSBOOL` | `"0"` or `"1"` | String, not bool. Cancelled flag. |
| `ResponsavelOWSText` | str | Issuing department acronym (e.g. `SECRE`, `DEORF`, `DEPIN`) |

## In-scope document types

Filter `Rows` by `TipodoNormativoOWSCHCS` ∈:

- `Resolução BCB`
- `Resolução CMN`
- `Resolução Conjunta`

Excluded:

- `Comunicado` — operational notices (e.g. swap auctions, USD auctions, leilões). Not regulatory content; excluded from the corpus.

Rationale: Comunicados dominate the result volume (~21/31 in a sample week) but carry no regulatory weight. Including them would dilute retrieval quality for the intended use case.

## Pagination

- Issue request with `startrow = 0`.
- Read `TotalRows` from the response.
- Iterate: `startrow += rowlimit` until `startrow >= TotalRows`.
- BCB returns an empty `Rows` array if `startrow` exceeds available results — treat as loop exit.

## Rate limiting

- **1 request per 2 seconds** minimum (both between pages and between month windows).
- Retries via `tenacity`: 3 attempts, exponential backoff `min=2s`, `max=30s`.
- Retry on: `httpx.HTTPError`, HTTP status 429, 500, 502, 503, 504.
- **Do not retry aggressively on 403 or 401** — if BCB blocks us, stop and investigate.

## Ingestion strategy

For a 2020–2025 corpus:
- Iterate month-by-month (72 month windows).
- Per month: paginate until exhaustion.
- Filter in-memory by `TipodoNormativoOWSCHCS`.
- Yield `BcbDocument` dataclass instances to the downloader.

## Document detail URL

**Not yet documented.** The search API returns `listItemId` but no direct PDF URL.

Pending DevTools spike: click a single Resolução on the real search page, inspect Network tab, capture the request that fetches the full document content (PDF or HTML).

This section will be updated once the detail endpoint is confirmed.

## Open questions

- What does BCB return for documents with attachments (anexos)? Some regulations have multiple PDFs.
- Are scanned-only PDFs distinguishable from text PDFs in the metadata? (Relevant for Week 1 exclusion scope.)
- Is there a stable ETag or `last-modified` on detail responses for incremental re-ingestion? (Deferred — v0.1 is full re-ingest only.)
# BCB Scraper

## Source

Banco Central do Brasil (BCB) — public normative documents search.

The public search page at `https://www.bcb.gov.br/estabilidadefinanceira/buscanormas` is a client-side rendered Angular SPA. The served HTML is an empty shell (`<app-root></app-root>`); results are fetched from a SharePoint-backed JSON API after the JavaScript bundle executes.

We bypass the HTML entirely and hit the underlying JSON APIs directly. This is faster, more reliable, and less brittle than headless-browser scraping.

---

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

### Response schema

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
| `listItemId` | str | Internal SharePoint item ID. Present but unused — we fetch detail by type + number, not by ID. |
| `RevogadoOWSBOOL` | `"0"` or `"1"` | **String**, not bool. Revoked flag. |
| `CanceladoOWSBOOL` | `"0"` or `"1"` | **String**, not bool. Cancelled flag. |
| `ResponsavelOWSText` | str | Issuing department acronym (e.g. `SECRE`, `DEORF`, `DEPIN`) |

---

## In-scope document types

Filter `Rows` by `TipodoNormativoOWSCHCS` ∈:

- `Resolução BCB`
- `Resolução CMN`
- `Resolução Conjunta`

Excluded:

- `Comunicado` — operational notices (e.g. swap auctions, USD auctions, leilões). Not regulatory content; excluded from the corpus.

Rationale: Comunicados dominate the result volume (~21/31 in a sample week) but carry no regulatory weight. Including them would dilute retrieval quality for the intended use case.

---

## Pagination

- Issue request with `startrow = 0`.
- Read `TotalRows` from the response.
- Iterate: `startrow += rowlimit` until `startrow >= TotalRows`.
- BCB returns an empty `Rows` array if `startrow` exceeds available results — treat as loop exit.

---

## Rate limiting

- **1 request per 2 seconds** minimum (both between pages and between month windows).
- Retries via `tenacity`: 3 attempts, exponential backoff `min=2s`, `max=30s`.
- Retry on: `httpx.HTTPError`, HTTP status 429, 500, 502, 503, 504.
- **Do not retry aggressively on 403 or 401** — if BCB blocks us, stop and investigate.

---

## Document detail endpoint

```
GET https://www.bcb.gov.br/api/conteudo/app/normativos/exibenormativo
```

### Query parameters

| Parameter | Value | Notes |
|---|---|---|
| `p1` | URL-encoded document type | e.g. `"Resolução CMN"` → `"Resolu%C3%A7%C3%A3o%20CMN"` |
| `p2` | Document number as integer | e.g. `5297` |

### Response schema

```jsonc
{
  "navegacao": null,
  "view": "views/exibenormativo.aspx",
  "conteudo": [
    {
      "Id": 52880,
      "Titulo": "Resolução CMN N° 5.297",
      "Tipo": "Resolução CMN",
      "Numero": 5297.0,                   // float — coerce with int()
      "VersaoNormativo": 0.0,
      "Data": "2026-04-23T21:54:34Z",
      "DataTexto": "23/4/2026 18:54",
      "Assunto": "...",
      "Revogado": false,                  // actual boolean (unlike search API)
      "Cancelado": false,
      "Texto": "<div>...<p>Art. 1º ...</p>...</div>",  // HTML body; MAY BE NULL
      "Documentos": null,                 // PDF references; MAY BE POPULATED
      "NormasVinculadas": null,
      "Referencias": null,
      "Atualizacoes": null,
      "Voto": null,
      "DOU": null
    }
  ]
}
```

### Field meanings

| Field | Type | Notes |
|---|---|---|
| `Titulo` | str | Full display title |
| `Tipo` | str | Document type (matches search API `TipodoNormativoOWSCHCS`) |
| `Numero` | float | Number — coerce to int with `int(item["Numero"])` |
| `Data` | str | ISO 8601 timestamp, UTC |
| `Assunto` | str | Plain text description (no HTML wrapping here) |
| `Revogado` | bool | **Real boolean** — unlike `RevogadoOWSBOOL` in the search API |
| `Cancelado` | bool | **Real boolean** |
| `Texto` | str \| null | Full regulation body as HTML. **Primary content path.** |
| `Documentos` | list \| null | PDF attachment references. Used as fallback when `Texto` is null. |
| `NormasVinculadas` | list \| null | Links to related/superseding regulations. Not used in v0.1. |

### Critical observations

1. **Primary path is `Texto` (HTML).** When `Texto` is populated, it contains the full regulation body. We store the raw JSON response and extract text from `Texto` using BeautifulSoup. No PDF download needed.

2. **Fallback path when `Texto` is null.** `Documentos` may contain PDF references. For v0.1, these documents are flagged in the run log (`pdf_only_documents` list) and deferred to Week 2 (Docling). Frequency unknown — Week 2 will quantify.

3. **`Texto` HTML structure.** Double-wrapped: `<div class="ExternalClass...">` → `<html><body>` → real content. HTML entities present (`&#58;`, `&#160;`). Inline CSS on paragraphs. `\r\n` line endings. BeautifulSoup `.get_text(separator="\n")` handles all of this.

4. **Article boundaries are textual.** Articles start with `Art. 1º`, `Art. 2º` (superscript ordinal `º`). Paragraphs use `§ 1º`. Incisos use `I -`, `II -`. These are natural chunking units for Week 2.

5. **`Revogado`/`Cancelado` are real booleans here**, unlike the search API's `"0"`/`"1"` strings.

---

## Storage layout

Raw detail responses are stored verbatim as JSON:

```
s3://regulens-corpus/raw/bcb/<type_slug>/<year>/<number>.json
```

Where `type_slug` is lower-case, accents stripped, spaces → dashes:
- `Resolução BCB` → `resolucao-bcb`
- `Resolução CMN` → `resolucao-cmn`
- `Resolução Conjunta` → `resolucao-conjunta`

Rationale: storing the raw API response preserves the source of truth. Text can always be re-extracted; a discarded response cannot be recovered.

---

## Ingestion strategy

For a 2020–2025 corpus:
1. Iterate month-by-month across the search API (72 windows).
2. Per month: paginate search results until exhaustion. Filter to in-scope types.
3. Per document: call detail endpoint, classify as `html` / `pdf_only` / `empty`, upload raw JSON to S3.
4. Log run summary including `pdf_only_documents` list for Week 2 follow-up.

---

## Open questions

- How frequent are `Texto = null` documents in 2020–2025? (Measure in Week 2 full ingest.)
- Do any documents have both `Texto` populated **and** `Documentos` (i.e., HTML + PDF supplement)?
- Are scanned-only PDFs distinguishable from text PDFs in `Documentos` metadata? (Relevant for Docling scope in Week 2.)
- Is there a stable ETag or `last-modified` header for incremental re-ingestion? (Deferred — v0.1 is full re-ingest only.)

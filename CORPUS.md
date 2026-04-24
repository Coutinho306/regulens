## Corpus scope

**Source:** Banco Central do Brasil (BCB) — public normative documents search.

**Document types (in scope):**
- Resolução BCB
- Resolução CMN (Conselho Monetário Nacional)
- Resolução Conjunta

**Excluded:**
- Comunicado — operational notices (swap auctions, dollar auctions, etc.), not regulatory content.
- Documents marked `RevogadoOWSBOOL=1` or `CanceladoOWSBOOL=1` are retained but flagged — relevant for "what changed" queries.
- Scanned-only PDFs without a text layer — deferred to v0.2 (no OCR in v0.1).

**Date range:** 2020-01-01 to 2025-12-31.

**Estimated volume:** 200–400 documents. To be validated in Week 2 after full crawl.

**Language:** Portuguese (Brazilian).

**Update model (v0.1):** full re-ingest on demand. Incremental ingestion deferred.

**Topics:** no topic filter at ingestion. Retrieval and eval will focus on PIX and Open Finance use cases, but the full corpus is indexed to allow broader queries.
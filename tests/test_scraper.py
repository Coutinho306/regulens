"""Smoke tests for ingestion/scraper.py."""

import pytest

from ingestion.scraper import BcbDocument, _parse_row, _strip_html

_FIXTURE_ROW = {
    "title": "Resolução BCB N° 559",
    "TipodoNormativoOWSCHCS": "Resolução BCB",
    "NumeroOWSNMBR": "559.000000000000",
    "data": "2026-04-23T21:00:11Z",
    "AssuntoNormativoOWSMTXT": "Altera o regulamento do PIX.",
    "listItemId": "52875",
    "RevogadoOWSBOOL": "0",
    "CanceladoOWSBOOL": "0",
    "ResponsavelOWSText": "SECRE",
}


def test_parse_row_returns_correct_fields() -> None:
    doc = _parse_row(_FIXTURE_ROW)
    assert doc.doc_type == "Resolução BCB"
    assert doc.number == 559
    assert doc.date_iso == "2026-04-23T21:00:11Z"
    assert doc.list_item_id == "52875"
    assert doc.is_revoked is False
    assert doc.is_cancelled is False
    assert doc.responsible_dept == "SECRE"
    assert doc.summary == "Altera o regulamento do PIX."


def test_parse_row_strips_html_from_summary() -> None:
    row = {
        **_FIXTURE_ROW,
        "AssuntoNormativoOWSMTXT": '<div class="ExternalClassABC">texto regulatório</div>',
    }
    doc = _parse_row(row)
    assert doc.summary == "texto regulatório"


def test_bcbdocument_rejects_zero_number() -> None:
    with pytest.raises(ValueError, match="number must be positive"):
        BcbDocument(
            doc_type="Resolução BCB",
            number=0,
            date_iso="2026-01-01T00:00:00Z",
            title="Test",
            summary="",
            list_item_id="123",
            is_revoked=False,
            is_cancelled=False,
            responsible_dept="SECRE",
        )


def test_bcbdocument_rejects_empty_list_item_id() -> None:
    with pytest.raises(ValueError, match="list_item_id required"):
        BcbDocument(
            doc_type="Resolução BCB",
            number=1,
            date_iso="2026-01-01T00:00:00Z",
            title="Test",
            summary="",
            list_item_id="",
            is_revoked=False,
            is_cancelled=False,
            responsible_dept="SECRE",
        )

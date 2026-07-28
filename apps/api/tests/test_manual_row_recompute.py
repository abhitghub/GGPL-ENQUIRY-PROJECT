"""A hand-keyed line item must come back from bulk-recompute with a GGPL
description. Manual rows carry only the typed wording — no classifier has run
on them — so the house formats have nothing to build from and the column used
to come back empty."""

import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.pop("app", None)

from app.main import app

SEALING_STRIP = "SIZE : 0.1 THK x 1736 LG x 45 W , DUPLEX  S31803 LAMIFLEX SEALING STRIP"


def _recompute(rows: list[dict]) -> list[dict]:
    client = TestClient(app)
    headers = {"X-Org-Id": f"org-manual-{uuid.uuid4().hex}", "X-User-Id": "shashnam@flosil.com"}
    created = client.post(
        "/api/v1/quotes",
        headers=headers,
        json={"customer": "Manual Row Co", "project_ref": "P-manual", "items": []},
    )
    assert created.status_code == 201
    response = client.post(
        f"/api/v1/quotes/{created.json()['id']}/items/bulk-recompute",
        headers=headers,
        json={"rows": rows},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_manual_one_off_row_returns_a_ggpl_description():
    row = {"line_no": 1, "quantity": 2, "uom": "NOS", "raw_description": SEALING_STRIP}
    assert _recompute([row])[0]["ggpl_description"] == (
        "SIZE : 0.1 THK X 1736 LG X 45 W , DUPLEX S31803 LAMIFLEX SEALING STRIP"
    )


def test_manual_row_recompute_keeps_classified_rows_on_the_house_format():
    rows = [
        {"line_no": 1, "quantity": 1, "uom": "NOS", "raw_description": SEALING_STRIP},
        {
            "line_no": 2, "quantity": 1, "uom": "NOS",
            "gasket_type": "SOFT_CUT", "size": '2"', "rating": "150#",
            "moc": "CNAF", "thickness_mm": 3,
            "raw_description": "2 inch 150# CNAF 3mm gasket",
        },
    ]
    recomputed = _recompute(rows)
    assert "LAMIFLEX SEALING STRIP" in recomputed[0]["ggpl_description"]
    second = recomputed[1]["ggpl_description"]
    assert second.startswith("SIZE : 2")
    assert "CNAF" in second
    assert "inch" not in second

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
HEADERS = {
    "Content-Type": "application/json",
    "X-Org-Id": "smoke-org",
    "X-User-Id": "smoke-user",
}


def request(method: str, path: str, payload: dict | None = None, headers: dict | None = None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers=headers or HEADERS,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
            text = raw.decode("utf-8") if raw else ""
            return response.status, json.loads(text) if text else None
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8")
        return exc.code, json.loads(text) if text else None


def main() -> None:
    item = {
        "line_no": 1,
        "quantity": 2,
        "uom": "NOS",
        "raw_description": '4" 150# CNAF RF gasket 3mm ASME B16.21',
        "size": '4"',
        "rating": "150#",
        "moc": "CNAF",
        "gasket_type": "SOFT_CUT",
    }

    status, quote = request(
        "POST",
        "/api/v1/quotes",
        {
            "customer": "Smoke Customer",
            "project_ref": "Smoke Project",
            "items": [item],
            "quote_data": {"quote_no": "SMOKE-1", "unit_prices": [100]},
        },
    )
    assert status == 201, (status, quote)
    quote_id = quote["id"]

    status, rows = request("POST", f"/api/v1/quotes/{quote_id}/items/bulk-recompute", {"indices": [0]})
    assert status == 200 and rows[0]["ggpl_description"], (status, rows)

    status, pdf = request("POST", f"/api/v1/quotes/{quote_id}/exports/pdf", {})
    assert status == 200 and pdf["content_type"] == "application/pdf", (status, pdf)

    status, xlsx = request("POST", f"/api/v1/quotes/{quote_id}/exports/xlsx", {})
    assert status == 200 and "spreadsheetml" in xlsx["content_type"], (status, xlsx)

    status, staged = request(
        "POST",
        f"/api/v1/quotes/{quote_id}/stage",
        {"stage": "po", "reason": "approved smoke quote"},
    )
    assert status == 200 and staged["stage"] == "po", (status, staged)

    other_org_headers = {**HEADERS, "X-Org-Id": "other-org"}
    status, _ = request("GET", f"/api/v1/quotes/{quote_id}", headers=other_org_headers)
    assert status == 404, status

    print(f"phase1 smoke ok: {quote_id}")


if __name__ == "__main__":
    main()

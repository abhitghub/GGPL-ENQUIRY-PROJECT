"""Persisted Updates feed + assigned-work endpoints behind the sidebar page."""

import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.pop("app", None)

from app.db import repo  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas.quotes import QuoteCreate  # noqa: E402
from app.services.notification_hub import notify_assignment, notify_stage_change  # noqa: E402

client = TestClient(app)


def headers(org_id: str, user_id: str) -> dict[str, str]:
    return {"X-Org-Id": org_id, "X-User-Id": user_id}


def _actor(org_id: str, user_id: str, name: str) -> SimpleNamespace:
    return SimpleNamespace(org_id=org_id, user_id=user_id, role="sales", name=name, email="")


def _quote(stage_meta: dict) -> SimpleNamespace:
    return SimpleNamespace(id="q-feed-1", customer="ACME", project_ref="REF-9", quote_no="Q-9", stage_meta=stage_meta)


def test_feed_returns_persisted_events_to_targeted_role_only():
    org = f"feed-org-{uuid.uuid4().hex[:8]}"
    notify_stage_change(
        _actor(org, "sales", "Sales User"),
        _quote({"workflow_stage": "estimation_review"}),
        "estimation_review",
    )

    # Legacy step estimation_review is owned by estimation (+ management).
    body = client.get("/api/v1/notifications", headers=headers(org, "estimation")).json()
    assert body["target"]["user_id"] == "estimation"
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["kind"] == "workflow"
    assert item["quote_id"] == "q-feed-1"
    assert item["by"] == "Sales User"
    assert "ACME" in item["message"]

    # Untargeted role sees nothing; the actor never sees their own action.
    assert client.get("/api/v1/notifications", headers=headers(org, "technical")).json()["items"] == []
    assert client.get("/api/v1/notifications", headers=headers(org, "sales")).json()["items"] == []


def test_admin_can_view_another_persons_feed_but_sales_cannot():
    org = f"feed-org-{uuid.uuid4().hex[:8]}"
    estimation_actor = SimpleNamespace(org_id=org, user_id="estimation", role="estimation", name="Estimation User", email="")
    notify_assignment(estimation_actor, _quote({"workflow_stage": "enquiry", "owner_id": "sales"}), "sales")

    own = client.get("/api/v1/notifications", headers=headers(org, "sales")).json()
    assert [item["kind"] for item in own["items"]] == ["assignment"]

    as_admin = client.get("/api/v1/notifications", params={"user": "sales"}, headers=headers(org, "shashnam"))
    assert as_admin.status_code == 200
    assert [item["kind"] for item in as_admin.json()["items"]] == ["assignment"]
    assert as_admin.json()["target"]["user_id"] == "sales"

    forbidden = client.get("/api/v1/notifications", params={"user": "estimation"}, headers=headers(org, "sales"))
    assert forbidden.status_code == 403

    missing = client.get("/api/v1/notifications", params={"user": "nobody"}, headers=headers(org, "shashnam"))
    assert missing.status_code == 404


def test_assigned_work_lists_owned_and_team_queue_enquiries():
    org = f"feed-org-{uuid.uuid4().hex[:8]}"
    repo.create_quote(
        org,
        "estimation",
        QuoteCreate(
            customer="ACME",
            project_ref="REF-1",
            stage_meta={"workflow_stage": "estimation_review", "owner_id": "sales"},
        ),
    )

    # The sales user owns the record even though it sits with estimation.
    owned = client.get("/api/v1/notifications/assigned", headers=headers(org, "sales")).json()
    assert len(owned["items"]) == 1
    assert owned["items"][0]["assigned_via"] == "owner"
    assert owned["items"][0]["workflow_stage"] == "estimation_review"

    # Estimation gets it through their team queue for the current step.
    queue = client.get("/api/v1/notifications/assigned", headers=headers(org, "estimation")).json()
    assert len(queue["items"]) == 1
    assert queue["items"][0]["assigned_via"] == "team"

    # Technical has no claim on it at this step.
    assert client.get("/api/v1/notifications/assigned", headers=headers(org, "technical")).json()["items"] == []

    # Admin can inspect any department member's queue; others cannot.
    as_admin = client.get("/api/v1/notifications/assigned", params={"user": "sales"}, headers=headers(org, "shashnam"))
    assert as_admin.status_code == 200
    assert len(as_admin.json()["items"]) == 1
    forbidden = client.get("/api/v1/notifications/assigned", params={"user": "sales"}, headers=headers(org, "technical"))
    assert forbidden.status_code == 403
"""Targeting semantics of the in-process real-time notification hub."""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.pop("app", None)

from app.config import get_settings  # noqa: E402
from app.services.notification_hub import NotificationHub, hub, notify_assignment, notify_stage_change  # noqa: E402


@pytest.fixture()
def granular_workflow(monkeypatch):
    monkeypatch.setenv("ENABLE_GRANULAR_WORKFLOW", "true")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("ENABLE_GRANULAR_WORKFLOW", raising=False)
    get_settings.cache_clear()


def test_publish_targets_roles_and_users_and_excludes_actor():
    async def scenario():
        local_hub = NotificationHub()
        estimation = local_hub.subscribe("org1", "meena", "estimation")
        technical = local_hub.subscribe("org1", "ravi", "technical")
        other_org = local_hub.subscribe("org2", "meena", "estimation")
        actor = local_hub.subscribe("org1", "actor", "estimation")

        delivered = local_hub.publish("org1", {"id": "n1"}, roles={"estimation"}, exclude_user_ids={"actor"})
        await asyncio.sleep(0)
        assert delivered == 1
        assert estimation.queue.get_nowait()["id"] == "n1"
        assert technical.queue.empty()
        assert other_org.queue.empty()
        assert actor.queue.empty()

        # Direct user targeting works regardless of role.
        local_hub.publish("org1", {"id": "n2"}, user_ids={"ravi"})
        await asyncio.sleep(0)
        assert technical.queue.get_nowait()["id"] == "n2"

        # An unsubscribed listener receives nothing further.
        local_hub.unsubscribe(estimation)
        assert local_hub.publish("org1", {"id": "n3"}, roles={"estimation"}, exclude_user_ids={"actor"}) == 0

    asyncio.run(scenario())


def test_notify_stage_change_reaches_destination_role(granular_workflow):
    async def scenario():
        subscriber = hub.subscribe("org1", "tech-user", "technical")
        try:
            actor = SimpleNamespace(org_id="org1", user_id="est-user", role="estimation", name="Meena", email="m@x.com")
            quote = SimpleNamespace(
                id="q1",
                customer="ACME",
                project_ref="REF-1",
                quote_no="Q-1",
                stage_meta={"workflow_stage": "technical_review_pending"},
            )
            notify_stage_change(actor, quote, "technical_review_pending")
            event = await asyncio.wait_for(subscriber.queue.get(), timeout=1)
            assert event["kind"] == "workflow"
            assert event["quote_id"] == "q1"
            assert event["stage"] == "technical_review_pending"
            assert event["stage_label"] == "Technical review pending"
            assert "ACME" in event["message"]
        finally:
            hub.unsubscribe(subscriber)

    asyncio.run(scenario())


def test_notify_assignment_targets_only_the_new_owner(granular_workflow):
    async def scenario():
        owner = hub.subscribe("org1", "sales-user", "sales")
        bystander = hub.subscribe("org1", "other-sales", "sales")
        try:
            actor = SimpleNamespace(org_id="org1", user_id="est-user", role="estimation", name="Meena", email="m@x.com")
            quote = SimpleNamespace(
                id="q2",
                customer="ACME",
                project_ref="",
                quote_no="Q-2",
                stage_meta={"workflow_stage": "enquiry_received", "owner_id": "sales-user"},
            )
            notify_assignment(actor, quote, "sales-user")
            event = await asyncio.wait_for(owner.queue.get(), timeout=1)
            assert event["kind"] == "assignment"
            assert "assigned" in event["message"]
            assert bystander.queue.empty()
            # Self-assignment is silent.
            notify_assignment(actor, quote, "est-user")
            await asyncio.sleep(0)
            assert owner.queue.empty()
        finally:
            hub.unsubscribe(owner)
            hub.unsubscribe(bystander)

    asyncio.run(scenario())
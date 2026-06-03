from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.deps import CurrentUser, get_current_user, require_capability


router = APIRouter(prefix="/api/v1/outlook", tags=["outlook"])


class OutlookMessageResolveRequest(BaseModel):
    mailbox_user: str = ""
    message_id: str = ""


class OutlookThreadRequest(BaseModel):
    mailbox_user: str = ""
    conversation_id: str = ""


class OutlookLinkedMessage(BaseModel):
    mailbox_user: str
    message_id: str
    conversation_id: str
    internet_message_id: str = ""
    web_link: str = ""
    subject: str = ""
    from_name: str = ""
    from_email: str = ""
    received_at: str = ""
    sent_at: str = ""
    has_attachments: bool = False
    linked_at: str = ""
    linked_by: str = ""


def _mailbox(payload_mailbox: str, settings: Settings) -> str:
    mailbox = (payload_mailbox or settings.outlook_default_mailbox or "").strip()
    if not mailbox:
        raise HTTPException(status_code=400, detail="Mailbox user is required")
    return mailbox


def _require_graph_settings(settings: Settings) -> None:
    if settings.microsoft_tenant_id and settings.microsoft_client_id and settings.microsoft_client_secret:
        return
    raise HTTPException(
        status_code=503,
        detail="Microsoft Graph is not configured. Set MICROSOFT_TENANT_ID, MICROSOFT_CLIENT_ID, and MICROSOFT_CLIENT_SECRET.",
    )


async def _graph_token(settings: Settings) -> str:
    _require_graph_settings(settings)
    token_url = f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": settings.microsoft_client_id,
        "client_secret": settings.microsoft_client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    async with httpx.AsyncClient(timeout=20) as client:
      response = await client.post(token_url, data=data)
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Microsoft Graph token request failed")
    token = response.json().get("access_token")
    if not token:
        raise HTTPException(status_code=502, detail="Microsoft Graph token response did not include an access token")
    return str(token)


def _message_from_graph(data: dict[str, Any], mailbox: str, user: CurrentUser) -> OutlookLinkedMessage:
    sender = data.get("from") or {}
    email = sender.get("emailAddress") if isinstance(sender, dict) else {}
    email = email if isinstance(email, dict) else {}
    return OutlookLinkedMessage(
        mailbox_user=mailbox,
        message_id=str(data.get("id") or ""),
        conversation_id=str(data.get("conversationId") or ""),
        internet_message_id=str(data.get("internetMessageId") or ""),
        web_link=str(data.get("webLink") or ""),
        subject=str(data.get("subject") or ""),
        from_name=str(email.get("name") or ""),
        from_email=str(email.get("address") or ""),
        received_at=str(data.get("receivedDateTime") or ""),
        sent_at=str(data.get("sentDateTime") or ""),
        has_attachments=bool(data.get("hasAttachments")),
        linked_at=datetime.now(timezone.utc).isoformat(),
        linked_by=user.user_id,
    )


@router.post("/messages/resolve", response_model=OutlookLinkedMessage)
async def resolve_message(
    payload: OutlookMessageResolveRequest,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> OutlookLinkedMessage:
    require_capability(user, "edit_sales_details")
    mailbox = _mailbox(payload.mailbox_user, settings)
    message_id = payload.message_id.strip()
    if not message_id:
        raise HTTPException(status_code=400, detail="Message id is required")
    token = await _graph_token(settings)
    select = "id,conversationId,internetMessageId,webLink,subject,from,receivedDateTime,sentDateTime,hasAttachments"
    url = f"https://graph.microsoft.com/v1.0/users/{quote(mailbox)}/messages/{quote(message_id, safe='')}"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, params={"$select": select}, headers={"Authorization": f"Bearer {token}"})
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Outlook message not found")
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Microsoft Graph message lookup failed")
    return _message_from_graph(response.json(), mailbox, user)


@router.post("/threads/messages", response_model=list[OutlookLinkedMessage])
async def thread_messages(
    payload: OutlookThreadRequest,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> list[OutlookLinkedMessage]:
    require_capability(user, "edit_sales_details")
    mailbox = _mailbox(payload.mailbox_user, settings)
    conversation_id = payload.conversation_id.strip()
    if not conversation_id:
        raise HTTPException(status_code=400, detail="Conversation id is required")
    token = await _graph_token(settings)
    conversation_filter = conversation_id.replace("'", "''")
    select = "id,conversationId,internetMessageId,webLink,subject,from,receivedDateTime,sentDateTime,hasAttachments"
    url = f"https://graph.microsoft.com/v1.0/users/{quote(mailbox)}/messages"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            url,
            params={"$select": select, "$filter": f"conversationId eq '{conversation_filter}'", "$top": "25"},
            headers={"Authorization": f"Bearer {token}"},
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Microsoft Graph thread lookup failed")
    values = response.json().get("value") or []
    if not isinstance(values, list):
        return []
    return [_message_from_graph(item, mailbox, user) for item in values if isinstance(item, dict)]

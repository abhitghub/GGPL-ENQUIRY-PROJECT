from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException

from app.deps import CurrentUser, get_current_user
from app.schemas.chat import ChatCompletionRequest, ChatCompletionResponse, ChatMessage

router = APIRouter(prefix="/api/v1", tags=["chat"])

GASKET_SYSTEM_PROMPT = (
    "You are a concise technical expert on industrial gaskets for Goodrich Gasket Pvt. Ltd. "
    "Specialise in soft cut, spiral wound, RTJ, Kammprofile, DJI, and ISK gaskets. "
    "Keep replies short and technical. Politely decline non-gasket topics."
)


@router.post("/chat/completions", response_model=ChatCompletionResponse)
def chat_completion(
    payload: ChatCompletionRequest,
    _user: CurrentUser = Depends(get_current_user),
) -> ChatCompletionResponse:
    key = (payload.api_key or os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY is required")
    from openai import OpenAI

    messages = [{"role": "system", "content": GASKET_SYSTEM_PROMPT}]
    messages.extend(message.model_dump() for message in payload.messages[-20:])
    response = OpenAI(api_key=key).chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        temperature=0.2,
        max_tokens=350,
    )
    return ChatCompletionResponse(
        message=ChatMessage(role="assistant", content=response.choices[0].message.content.strip())
    )

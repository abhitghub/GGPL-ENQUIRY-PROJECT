from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    messages: list[ChatMessage]
    api_key: str | None = None


class ChatCompletionResponse(BaseModel):
    message: ChatMessage


class DocAssistantSessionCreate(BaseModel):
    documents: dict[str, str] = Field(default_factory=dict)


class DocAssistantSessionRead(BaseModel):
    id: str
    document_names: list[str]


class DocAssistantMessageCreate(BaseModel):
    question: str
    api_key: str | None = None


class DocAssistantMessageRead(BaseModel):
    answer: str

from __future__ import annotations

import csv
import io
import os
from pathlib import Path

import pandas as pd
import pdfplumber
from docx import Document
from fastapi import APIRouter, Depends, HTTPException, Request

from app.db import repo
from app.deps import CurrentUser, get_current_user
from app.schemas.common import APIMessage
from app.schemas.chat import (
    DocAssistantMessageCreate,
    DocAssistantMessageRead,
    DocAssistantSessionCreate,
    DocAssistantSessionRead,
)

router = APIRouter(prefix="/api/v1/doc-assistant", tags=["doc-assistant"])

SYSTEM_PROMPT = (
    "You are a precise technical document assistant for Goodrich Gasket Pvt. Ltd. "
    "Answer based only on the supplied documents. If something is not in the documents, say so."
)
MAX_CONTEXT_CHARS = 120_000


def _extract_pdf(raw: bytes) -> str:
    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def _extract_docx(raw: bytes) -> str:
    doc = Document(io.BytesIO(raw))
    return "\n".join(p.text for p in doc.paragraphs if p.text).strip()


def _extract_spreadsheet(raw: bytes, ext: str) -> str:
    engine = "openpyxl" if ext in (".xlsx", ".xlsm") else None
    sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None, dtype=str, engine=engine)
    chunks: list[str] = []
    for name, frame in sheets.items():
        frame = frame.fillna("")
        chunks.append(f"=== Sheet: {name} ===")
        chunks.append(frame.to_csv(index=False))
    return "\n".join(chunks).strip()


def _extract_csv(raw: bytes) -> str:
    text = raw.decode("utf-8-sig", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    return "\n".join(",".join(cell.strip() for cell in row) for row in rows).strip()


def _extract_document_text(filename: str, raw: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(raw)
    if ext == ".docx":
        return _extract_docx(raw)
    if ext in (".xlsx", ".xls", ".xlsm"):
        return _extract_spreadsheet(raw, ext)
    if ext == ".csv":
        return _extract_csv(raw)
    if ext == ".txt":
        return raw.decode("utf-8", errors="replace").strip()
    if ext == ".doc":
        return "[.doc not supported - convert to .docx]"
    raise HTTPException(status_code=400, detail=f"Unsupported document type: {ext or filename}")


@router.post("/sessions", response_model=DocAssistantSessionRead, status_code=201)
def create_session(
    payload: DocAssistantSessionCreate,
    user: CurrentUser = Depends(get_current_user),
) -> DocAssistantSessionRead:
    session = repo.create_doc_session(user.org_id, payload.documents)
    return DocAssistantSessionRead(id=session["id"], document_names=list(session["documents"].keys()))


@router.post("/sessions/upload", response_model=DocAssistantSessionRead, status_code=201)
async def create_session_from_uploads(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> DocAssistantSessionRead:
    form = await request.form()
    documents: dict[str, str] = {}
    for _, value in form.multi_items():
        if not hasattr(value, "filename") or not value.filename:
            continue
        raw = await value.read()
        text = _extract_document_text(value.filename, raw)
        if text:
            documents[value.filename] = text
    if not documents:
        raise HTTPException(status_code=400, detail="Upload at least one supported document with extractable text")
    session = repo.create_doc_session(user.org_id, documents)
    return DocAssistantSessionRead(id=session["id"], document_names=list(session["documents"].keys()))


@router.post("/sessions/{session_id}/messages", response_model=DocAssistantMessageRead)
def create_message(
    session_id: str,
    payload: DocAssistantMessageCreate,
    user: CurrentUser = Depends(get_current_user),
) -> DocAssistantMessageRead:
    session = repo.get_doc_session(user.org_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Document session not found")
    key = (payload.api_key or os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY is required")

    from openai import OpenAI

    context = "\n\n---\n\n".join(
        f"[File: {name}]\n{text}" for name, text in session["documents"].items()
    )[:MAX_CONTEXT_CHARS]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Document content:\n\n<document>\n{context}\n</document>"},
        {"role": "assistant", "content": "Understood. I have read the document and am ready to answer."},
        *session["messages"],
        {"role": "user", "content": payload.question},
    ]
    response = OpenAI(api_key=key).chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        temperature=0.1,
        max_tokens=2048,
    )
    answer = response.choices[0].message.content.strip()
    repo.append_doc_message(user.org_id, session_id, "user", payload.question)
    repo.append_doc_message(user.org_id, session_id, "assistant", answer)
    return DocAssistantMessageRead(answer=answer)


@router.delete("/sessions/{session_id}/documents/{document_name}", response_model=DocAssistantSessionRead)
def remove_document(
    session_id: str,
    document_name: str,
    user: CurrentUser = Depends(get_current_user),
) -> DocAssistantSessionRead:
    session = repo.get_doc_session(user.org_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Document session not found")
    documents = dict(session["documents"])
    documents.pop(document_name, None)
    updated = repo.update_doc_session(user.org_id, session_id, documents=documents)
    if not updated:
        raise HTTPException(status_code=404, detail="Document session not found")
    return DocAssistantSessionRead(id=session_id, document_names=list(updated["documents"].keys()))


@router.delete("/sessions/{session_id}", response_model=APIMessage)
def clear_session(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> APIMessage:
    updated = repo.update_doc_session(user.org_id, session_id, documents={}, messages=[])
    if not updated:
        raise HTTPException(status_code=404, detail="Document session not found")
    return APIMessage(message="cleared")

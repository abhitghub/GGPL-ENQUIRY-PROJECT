from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.db import repo
from app.deps import CurrentUser, get_current_user, require_capability
from app.routers.quotes import _can_read_quote, _repo_visibility_kwargs
from app.schemas.jobs import ExtractionAccepted, ExtractionCreate, JobRead, JobStatusRead
from app.services.extraction_runner import run_extraction_job

router = APIRouter(prefix="/api/v1", tags=["extractions"])
ALLOWED_SOURCE_TYPES = {"email", "excel"}


def _job_or_404(user: CurrentUser, job_id: str) -> JobRead:
    job = repo.get_job(user.org_id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.quote_id:
        quote = repo.get_quote(user.org_id, job.quote_id, **_repo_visibility_kwargs(user))
        if not quote or not _can_read_quote(user, quote):
            raise HTTPException(status_code=404, detail="Job not found")
    elif user.role != "admin":
        stored_user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"ggpl-gasket-quote/{user.user_id}"))
        if job.created_by not in {user.user_id, stored_user_id}:
            raise HTTPException(status_code=404, detail="Job not found")
    return job


async def _parse_extraction_request(request: Request) -> tuple[ExtractionCreate, str | bytes | None]:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        uploaded = form.get("file")
        text = form.get("text")
        source = await uploaded.read() if hasattr(uploaded, "read") else text
        source_type = str(form.get("source_type") or ("excel" if getattr(uploaded, "filename", "").lower().endswith((".xls", ".xlsx")) else "email"))
        return ExtractionCreate(
            source_type=source_type,
            text=source.decode("utf-8", errors="replace") if isinstance(source, bytes) and source_type == "email" else str(text or ""),
            quote_id=form.get("quote_id") or None,
            customer=str(form.get("customer") or ""),
            project_ref=str(form.get("project_ref") or ""),
            api_key=form.get("api_key") or None,
        ), source
    body = await request.json()
    payload = ExtractionCreate(**body)
    return payload, payload.text


@router.post("/extractions", response_model=ExtractionAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_extraction(
    request: Request,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
) -> ExtractionAccepted:
    require_capability(user, "edit_line_items")
    payload, source = await _parse_extraction_request(request)
    if payload.source_type not in ALLOWED_SOURCE_TYPES:
        raise HTTPException(status_code=400, detail="Only email text and Excel upload extraction are supported.")
    if payload.quote_id and not repo.get_quote(user.org_id, payload.quote_id, **_repo_visibility_kwargs(user)):
        raise HTTPException(status_code=404, detail="Quote not found")
    if not source:
        raise HTTPException(status_code=400, detail="Extraction source is required")

    job = repo.create_job(user.org_id, payload.source_type, quote_id=payload.quote_id, created_by=user.user_id)
    background_tasks.add_task(
        run_extraction_job,
        org_id=user.org_id,
        job_id=job.id,
        source=source,
        source_type=payload.source_type,
        api_key=payload.api_key,
        quote_id=payload.quote_id,
    )
    return ExtractionAccepted(job_id=job.id, status=job.status)


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: str, user: CurrentUser = Depends(get_current_user)) -> JobRead:
    return _job_or_404(user, job_id)


@router.get("/jobs/{job_id}/status", response_model=JobStatusRead)
def get_job_status(job_id: str, user: CurrentUser = Depends(get_current_user)) -> JobStatusRead:
    job = _job_or_404(user, job_id)
    return JobStatusRead(
        id=job.id,
        status=job.status,
        source_type=job.source_type,
        quote_id=job.quote_id,
        progress=job.progress,
        message=job.message,
        parsed_count=len(job.items),
        skipped_count=job.skipped_count,
        error=job.error,
        updated_at=job.updated_at,
    )


@router.get("/jobs/{job_id}/stream")
def stream_job(job_id: str, user: CurrentUser = Depends(get_current_user)) -> StreamingResponse:
    _job_or_404(user, job_id)

    def events():
        current = _job_or_404(user, job_id)
        if current:
            yield f"event: status\ndata: {current.model_dump_json()}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")

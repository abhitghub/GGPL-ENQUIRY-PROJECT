"""Pipeline orchestration: document → extracted items → rules → formatted descriptions."""
from __future__ import annotations
import logging
from typing import Callable, Optional
from core.document_reader import read_document_smart, SmartParseError
from core.rules import apply_rules
from core.formatter import format_description
from core.parser import parse_excel_file

logger = logging.getLogger(__name__)


def _process_item(item: dict) -> dict:
    processed = apply_rules(dict(item))
    processed['ggpl_description'] = format_description(processed)
    return processed


def _needs_smart_parse_review(item: dict) -> bool:
    if item.get('status') == 'missing':
        return True
    flags = ' | '.join(str(flag) for flag in item.get('flags') or []).lower()
    return any(token in flags for token in (
        'ambiguous',
        'missing critical',
        'not identified',
        'not specified',
    ))


def _build_review_text(items: list[dict]) -> str:
    lines = [
        'Extract these Excel rows. Preserve source_index exactly for each returned item.',
    ]
    for fallback_index, item in enumerate(items, 1):
        source_index = item.get('source_index') or fallback_index
        line_no = item.get('line_no') or source_index
        quantity = item.get('quantity') or ''
        uom = item.get('uom') or 'NOS'
        description = item.get('raw_description') or item.get('description') or ''
        lines.append(
            f'source_index: {source_index} | line_no: {line_no} | '
            f'quantity: {quantity} | uom: {uom} | raw_description: {description}'
        )
    return '\n'.join(lines)


def _replace_reviewed_items(base_items: list[dict], review_indices: list[int], reviewed_items: list[dict]) -> list[dict]:
    result = [dict(item) for item in base_items]
    pending_indices = list(review_indices)
    by_source_index = {
        int(float(item['source_index'])): item
        for item in reviewed_items
        if str(item.get('source_index') or '').replace('.', '', 1).isdigit()
    }

    for index in review_indices:
        source_index = base_items[index].get('source_index')
        replacement = None
        if str(source_index or '').replace('.', '', 1).isdigit():
            replacement = by_source_index.get(int(float(source_index)))
        if replacement:
            result[index] = replacement
            if index in pending_indices:
                pending_indices.remove(index)

    sequential = [item for item in reviewed_items if item not in by_source_index.values()]
    for index, replacement in zip(pending_indices, sequential):
        result[index] = replacement

    return result


def process_document(
    source,
    source_type: str,
    openai_client,
    progress_cb: Optional[Callable] = None,
    on_chunk_items: Optional[Callable] = None,
) -> tuple[list[dict], int, str | None]:
    """
    Full pipeline: raw input → processed items with GGPL descriptions.

    Returns (items, skipped_count, error_message).
    error_message is None on success, a human-readable string on failure.
    """
    def _on_chunk(chunk_items):
        processed_chunk = [_process_item(item) for item in chunk_items]
        if on_chunk_items:
            on_chunk_items(processed_chunk)

    if source_type == 'excel':
        try:
            if progress_cb:
                progress_cb(1, 10)
            fast_raw = parse_excel_file(source)
            if fast_raw:
                fast_processed = [_process_item(item) for item in fast_raw]
                review_indices = [
                    index for index, item in enumerate(fast_processed)
                    if _needs_smart_parse_review(item)
                ]
                if fast_processed and on_chunk_items:
                    on_chunk_items(fast_processed)
                if progress_cb:
                    progress_cb(4 if review_indices else 10, 10)

                reviewed_processed: list[dict] = []
                reviewed_skipped = 0
                if review_indices:
                    review_raw = [fast_raw[index] for index in review_indices]
                    review_text = _build_review_text(review_raw)

                    def _review_progress(done, total):
                        if progress_cb:
                            progress_cb(4 + int(done / total * 5), 10)

                    try:
                        reviewed_raw, reviewed_skipped = read_document_smart(
                            review_text,
                            'email',
                            openai_client,
                            progress_cb=_review_progress,
                            on_chunk_items=None,
                        )
                    except SmartParseError as e:
                        logger.warning('Excel fast path review failed; keeping deterministic rows: %s', e)
                        reviewed_raw = []
                    reviewed_processed = [_process_item(item) for item in reviewed_raw]

                combined = _replace_reviewed_items(fast_processed, review_indices, reviewed_processed)
                if progress_cb:
                    progress_cb(10, 10)
                return combined, reviewed_skipped, None
        except Exception as e:
            logger.warning('Excel fast path failed; falling back to full Smart Parse: %s', e)

    try:
        raw_items, n_skipped = read_document_smart(
            source, source_type, openai_client,
            progress_cb=progress_cb,
            on_chunk_items=_on_chunk,
        )
    except SmartParseError as e:
        return [], 0, str(e)

    processed = [_process_item(item) for item in raw_items]

    return processed, n_skipped, None

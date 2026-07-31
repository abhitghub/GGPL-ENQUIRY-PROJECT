"""Description memory: the portal's learned corrections (Rule L).

The rules engine is deterministic, so a construction it gets wrong it gets wrong
every time. This module is the counterweight: when the team fixes a GGPL
description (or types one for a gasket the engine has no format for), the
correction is remembered against a fingerprint of the customer's wording, and
the next enquiry carrying that same wording is answered from memory instead of
being re-derived and re-broken.

Design notes:

* Pure data + pure functions — no DB, no I/O. The API layer owns storage and
  hands a list of entries to `DescriptionMemory.build`; the same index is used
  by extraction, recompute, and the curation screens.
* Exact fingerprint matches are APPLIED. Near matches (same significant token
  set, different order/punctuation) are only ever offered as a SUGGESTION —
  a near match is a good hint and a bad law.
* An entry can carry classified field values, not just the display string, so a
  learned row also prices and plans correctly. Nothing is applied over a field
  the operator set by hand on this row (`manual_fields`).
* Everything applied is stamped on the row (`learned_from`), so a reviewer can
  always see the description came from memory and who taught it.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

# Classified fields a learned entry is allowed to carry. Mirrors the portal's
# AUTO_UPDATE_FIELDS (apps/web/app/quotes/quotes-client.tsx): the fields the
# rules engine derives and an operator may override. Identity/commercial fields
# (quantity, line_no, customer_sl_no, prices) are deliberately absent — those
# are per-enquiry facts, never reusable knowledge.
LEARNABLE_FIELDS: tuple[str, ...] = (
    'gasket_type',
    'size',
    'size_norm',
    'size_type',
    'od_mm',
    'id_mm',
    'rating',
    'moc',
    'face_type',
    'thickness_mm',
    'standard',
    'series',
    'special',
    'ring_no',
    'rtj_groove_type',
    'rtj_hardness_bhn',
    'rtj_hardness_spec',
    'sw_winding_material',
    'sw_filler',
    'sw_outer_ring',
    'sw_inner_ring',
    'isk_style',
    'isk_type',
    'isk_gasket_material',
    'isk_core_material',
    'isk_sleeve_material',
    'isk_washer_material',
    'isk_primary_seal',
    'isk_secondary_seal',
    'isk_insulating_washer',
    'isk_fire_safety',
    'kamm_core_material',
    'kamm_surface_material',
    'kamm_covering_layer',
    'kamm_rib',
    'kamm_core_thk',
    'kamm_layer_thk',
    'kamm_geometry',
    'kamm_integral_outer_ring',
    'dji_filler',
    'dji_rib',
    'dji_face_type',
    'dji_id_first',
)

_LEARNABLE_SET = frozenset(LEARNABLE_FIELDS)

STATUS_APPROVED = 'approved'
STATUS_PENDING = 'pending'
STATUS_REJECTED = 'rejected'

#: Entry states that participate in matching. Rejected entries are kept as a
#: record of "we decided this is not a rule" and never applied again.
ACTIVE_STATUSES = frozenset({STATUS_APPROVED, STATUS_PENDING})

SOURCE_EDIT = 'edit'
SOURCE_MANUAL = 'manual'
SOURCE_IMPORT = 'import'

# Punctuation that separates tokens rather than belonging to them. `.` `/` `-`
# `#` `%` and `+` are kept: they carry meaning in sizes, ratings and grades
# (1-1/2", 150#, 2.5MM, SS316L+GRAPHITE, 2%MO).
_SEPARATORS = re.compile(r'[^A-Z0-9./\-#%+]+')
# `4.50MM` -> `4.5MM`, `150.00 NB` -> `150 NB`. The leading guard keeps standard
# citations intact: the `16` of `B16.20` is preceded by a letter, so B16.20 never
# collapses to B16.2.
_TRAILING_ZERO_DECIMAL = re.compile(r'(?<![A-Z0-9.])(\d+)\.(\d*?)0+(?!\d)')
_BARE_DECIMAL_POINT = re.compile(r'(?<![A-Z0-9.])(\d+)\.(?!\d)')
_UNICODE_FOLD = {
    '‘': "'", '’': "'", '“': '"', '”': '"',
    '–': '-', '—': '-', '−': '-',
    '×': ' X ', '″': '"', '′': "'",
    ' ': ' ',
}

# Tokens carrying no discriminating power. Dropped from the near-match
# signature only — the exact key keeps the wording verbatim.
_NOISE_TOKENS = frozenset({
    'AND', 'OR', 'OF', 'FOR', 'WITH', 'THE', 'A', 'AN', 'TO', 'AS', 'PER',
    'NOS', 'NO', 'QTY', 'SET', 'SETS', 'PC', 'PCS', 'PIECE', 'PIECES',
    'EA', 'EACH', 'ITEM', 'SL', 'SR', 'MAKE',
})


def normalize_source_text(raw: Any) -> str:
    """Canonical form of a customer's wording, used as the memory key.

    Absorbs the noise that makes the *same* request look different between
    enquiries — case, spacing, quote glyphs, `150.00` vs `150` — while keeping
    every token that changes what is being asked for.
    """
    text = str(raw or '')
    if not text.strip():
        return ''
    for source, target in _UNICODE_FOLD.items():
        text = text.replace(source, target)
    text = _SEPARATORS.sub(' ', text.upper())
    # 12.500 -> 12.5, 150.0 -> 150, 150. -> 150
    text = _TRAILING_ZERO_DECIMAL.sub(lambda m: f'{m.group(1)}.{m.group(2)}' if m.group(2) else m.group(1), text)
    text = _BARE_DECIMAL_POINT.sub(r'\1', text)
    return ' '.join(text.split())


def fingerprint(raw: Any) -> str:
    """Stable key for a customer wording. Empty string when there is no text."""
    normalized = normalize_source_text(raw)
    if not normalized:
        return ''
    return hashlib.sha1(normalized.encode('utf-8')).hexdigest()


def token_signature(raw: Any) -> str:
    """Order-insensitive signature used for near-match suggestions only."""
    normalized = normalize_source_text(raw)
    if not normalized:
        return ''
    tokens = sorted({token for token in normalized.split() if token not in _NOISE_TOKENS})
    if not tokens:
        return ''
    return hashlib.sha1(' '.join(tokens).encode('utf-8')).hexdigest()


def source_text_of(item: dict) -> str:
    """The wording a memory entry is keyed on: what the customer sent.

    `raw_description` is the customer's text; `description` is the LLM's cleaned
    echo of it and is only used when the raw text is absent (hand-keyed rows).
    """
    for key in ('raw_description', 'description'):
        value = str(item.get(key) or '').strip()
        if value:
            return value
    return ''


def learnable_fields_of(item: dict) -> dict[str, Any]:
    """The classified values of `item` that a memory entry may carry."""
    return {
        name: item[name]
        for name in LEARNABLE_FIELDS
        if name in item and item[name] not in (None, '')
    }


def changed_fields(before: dict, after: dict) -> dict[str, Any]:
    """Learnable fields whose value the operator actually changed.

    A field cleared back to empty is a change too — it hands the field back to
    the rules engine — but it is not knowledge worth storing, so it is skipped.
    """
    changes: dict[str, Any] = {}
    for name in LEARNABLE_FIELDS:
        new_value = after.get(name)
        if new_value in (None, ''):
            continue
        if _same_value(before.get(name), new_value):
            continue
        changes[name] = new_value
    return changes


def _same_value(left: Any, right: Any) -> bool:
    if left is None and right is None:
        return True
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) < 1e-9
    return str(left or '').strip().upper() == str(right or '').strip().upper()


def descriptions_differ(left: Any, right: Any) -> bool:
    """Whether two GGPL descriptions differ beyond case/spacing."""
    return normalize_source_text(left) != normalize_source_text(right)


@dataclass(frozen=True)
class LearnedEntry:
    """One thing the portal has been taught."""

    id: str
    fingerprint: str
    source_text: str
    ggpl_description: str
    fields: dict[str, Any] = field(default_factory=dict)
    #: Empty means the entry applies to every customer.
    customer: str = ''
    status: str = STATUS_PENDING
    source: str = SOURCE_EDIT
    created_by: str = ''
    approved_by: str = ''
    note: str = ''
    updated_at: str = ''

    @property
    def is_approved(self) -> bool:
        return self.status == STATUS_APPROVED

    @property
    def signature(self) -> str:
        return token_signature(self.source_text)

    def label(self) -> str:
        scope = self.customer or 'all customers'
        state = 'approved' if self.is_approved else self.status
        return f'{scope} / {state}'


@dataclass(frozen=True)
class LearnedMatch:
    entry: LearnedEntry
    #: 'exact' matches are applied; 'similar' matches are suggested only.
    kind: str

    @property
    def should_apply(self) -> bool:
        return self.kind == 'exact'


def _customer_key(value: Any) -> str:
    return ' '.join(str(value or '').strip().upper().split())


def _rank(entry: LearnedEntry) -> tuple:
    """Best entry within a bucket: approved first, then most recently taught."""
    return (1 if entry.is_approved else 0, entry.updated_at or '', entry.id)


class DescriptionMemory:
    """Immutable lookup index over an org's learned entries."""

    def __init__(self, entries: Iterable[LearnedEntry]) -> None:
        self._by_fingerprint: dict[tuple[str, str], list[LearnedEntry]] = {}
        self._by_signature: dict[tuple[str, str], list[LearnedEntry]] = {}
        self._count = 0
        for entry in entries:
            if entry.status not in ACTIVE_STATUSES or not entry.fingerprint:
                continue
            customer = _customer_key(entry.customer)
            self._by_fingerprint.setdefault((customer, entry.fingerprint), []).append(entry)
            signature = entry.signature
            if signature:
                self._by_signature.setdefault((customer, signature), []).append(entry)
            self._count += 1

    @classmethod
    def build(cls, entries: Iterable[LearnedEntry]) -> 'DescriptionMemory':
        return cls(entries)

    @classmethod
    def empty(cls) -> 'DescriptionMemory':
        return cls([])

    def __len__(self) -> int:
        return self._count

    def __bool__(self) -> bool:
        return self._count > 0

    def resolve(self, raw_description: Any, customer: Any = '') -> LearnedMatch | None:
        """Best entry for this wording, or None.

        Customer-scoped knowledge outranks org-wide knowledge, and an exact
        wording match outranks a near match — so a customer's own house
        convention wins over a general rule, and a general rule still wins over
        a vague resemblance.
        """
        key = fingerprint(raw_description)
        if not key:
            return None
        customer_key = _customer_key(customer)
        scopes = [customer_key, ''] if customer_key else ['']

        for scope in scopes:
            bucket = self._by_fingerprint.get((scope, key))
            if bucket:
                return LearnedMatch(entry=max(bucket, key=_rank), kind='exact')

        signature = token_signature(raw_description)
        if not signature:
            return None
        for scope in scopes:
            bucket = self._by_signature.get((scope, signature))
            if bucket:
                return LearnedMatch(entry=max(bucket, key=_rank), kind='similar')
        return None


def apply_match(item: dict, match: LearnedMatch) -> dict:
    """Apply a resolved memory entry to `item` in place and return it.

    An exact match writes the learned description and classified fields; a near
    match only records a suggestion for the reviewer. Neither ever overwrites a
    field this row's operator set by hand.
    """
    if not match.should_apply:
        return suggest_match(item, match)

    entry = match.entry
    manual = {str(name) for name in (item.get('manual_fields') or [])}
    applied: list[str] = []
    for name, value in (entry.fields or {}).items():
        if name not in _LEARNABLE_SET or name in manual:
            continue
        if _same_value(item.get(name), value):
            continue
        item[name] = value
        applied.append(name)

    description = str(entry.ggpl_description or '').strip()
    if description and 'ggpl_description' not in manual:
        item['ggpl_description'] = description

    item['learned_from'] = {
        'entry_id': entry.id,
        'status': entry.status,
        'scope': entry.customer or 'all',
        'match': match.kind,
        'fields': applied,
        'taught_by': entry.approved_by or entry.created_by,
    }
    item.pop('learned_suggestion', None)
    note = (
        f'DESCRIPTION FROM PORTAL MEMORY ({entry.label()})'
        if entry.is_approved
        else f'DESCRIPTION FROM PORTAL MEMORY — NOT YET APPROVED ({entry.label()})'
    )
    _append_flag(item, note)
    return item


def suggest_match(item: dict, match: LearnedMatch) -> dict:
    """Record a near match as a reviewer suggestion without changing the row."""
    entry = match.entry
    item['learned_suggestion'] = {
        'entry_id': entry.id,
        'status': entry.status,
        'scope': entry.customer or 'all',
        'source_text': entry.source_text,
        'ggpl_description': entry.ggpl_description,
        'fields': dict(entry.fields or {}),
    }
    _append_flag(item, 'SIMILAR WORDING PREVIOUSLY CORRECTED BY THE TEAM — REVIEW SUGGESTION')
    return item


def _append_flag(item: dict, note: str) -> None:
    flags = item.get('flags')
    if not isinstance(flags, list):
        flags = [flags] if flags else []
    if note not in flags:
        flags.append(note)
    item['flags'] = flags


def entry_from_item(
    item: dict,
    *,
    entry_id: str,
    customer: str = '',
    status: str = STATUS_PENDING,
    source: str = SOURCE_EDIT,
    created_by: str = '',
    approved_by: str = '',
    note: str = '',
    updated_at: str = '',
    fields: dict[str, Any] | None = None,
) -> LearnedEntry | None:
    """Build an entry from a portal row, or None when there is nothing to learn.

    Nothing to learn means: no customer wording to key on, or no GGPL
    description and no corrected fields to remember.
    """
    source_text = source_text_of(item)
    key = fingerprint(source_text)
    if not key:
        return None
    description = str(item.get('ggpl_description') or '').strip()
    payload = {
        name: value
        for name, value in (fields if fields is not None else learnable_fields_of(item)).items()
        if name in _LEARNABLE_SET and value not in (None, '')
    }
    if not description and not payload:
        return None
    return LearnedEntry(
        id=entry_id,
        fingerprint=key,
        source_text=' '.join(str(source_text).split()),
        ggpl_description=description,
        fields=payload,
        customer=' '.join(str(customer or '').split()),
        status=status,
        source=source,
        created_by=created_by,
        approved_by=approved_by,
        note=note,
        updated_at=updated_at,
    )

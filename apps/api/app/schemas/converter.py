from __future__ import annotations

from pydantic import BaseModel


class ConversionRequest(BaseModel):
    from_unit: str
    to_unit: str
    value: float


class ConversionResponse(BaseModel):
    from_unit: str
    to_unit: str
    value: float
    result: float
    display: str

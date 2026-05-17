from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core import unit_converter as uc

from app.schemas.converter import ConversionRequest, ConversionResponse

router = APIRouter(prefix="/api/v1", tags=["converter"])

_CONVERSIONS = {
    "length": {
        ("in", "mm"): uc.inches_to_mm,
        ("inch", "mm"): uc.inches_to_mm,
        ("mm", "in"): uc.mm_to_inches,
        ("mm", "inch"): uc.mm_to_inches,
    },
    "pressure": {
        ("psi", "bar"): uc.psi_to_bar,
        ("bar", "psi"): uc.bar_to_psi,
        ("psi", "mpa"): uc.psi_to_mpa,
        ("mpa", "psi"): uc.mpa_to_psi,
        ("bar", "mpa"): uc.bar_to_mpa,
        ("mpa", "bar"): uc.mpa_to_bar,
        ("kpa", "psi"): uc.kpa_to_psi,
        ("psi", "kpa"): uc.psi_to_kpa,
    },
    "temperature": {
        ("c", "f"): uc.c_to_f,
        ("f", "c"): uc.f_to_c,
        ("c", "k"): uc.c_to_k,
        ("k", "c"): uc.k_to_c,
    },
    "torque": {
        ("nm", "ftlb"): uc.nm_to_ftlb,
        ("ftlb", "nm"): uc.ftlb_to_nm,
        ("nm", "inlb"): uc.nm_to_inlb,
        ("inlb", "nm"): uc.inlb_to_nm,
    },
    "force": {
        ("kn", "kgf"): uc.kn_to_kgf,
        ("kgf", "kn"): uc.kgf_to_kn,
        ("n", "lbf"): uc.n_to_lbf,
        ("lbf", "n"): uc.lbf_to_n,
    },
}


@router.post("/converter/{conversion_type}", response_model=ConversionResponse)
def convert(conversion_type: str, payload: ConversionRequest) -> ConversionResponse:
    kind = conversion_type.lower()
    from_unit = payload.from_unit.lower()
    to_unit = payload.to_unit.lower()
    if kind == "pipe-size":
        if from_unit == "dn" and to_unit == "nps":
            result = uc.dn_to_nps(int(payload.value))
            if result is None:
                raise HTTPException(status_code=400, detail="DN value is not in the lookup table")
            return ConversionResponse(**payload.model_dump(), result=payload.value, display=result)
        if from_unit == "nps" and to_unit == "dn":
            result = uc.nps_val_to_dn(payload.value)
            if result is None:
                raise HTTPException(status_code=400, detail="NPS value is not in the lookup table")
            return ConversionResponse(**payload.model_dump(), result=float(result), display=str(result))
    if kind == "rating":
        if from_unit in ("class", "asme") and to_unit == "pn":
            result = uc.CLASS_PN.get(int(payload.value))
            if result is None:
                raise HTTPException(status_code=400, detail="ASME Class value is not in the lookup table")
            return ConversionResponse(**payload.model_dump(), result=float(result), display=f"PN {result}")
        if from_unit == "pn" and to_unit in ("class", "asme"):
            result = uc.PN_CLASS.get(int(payload.value))
            if result is None:
                raise HTTPException(status_code=400, detail="PN value is not in the lookup table")
            return ConversionResponse(**payload.model_dump(), result=float(result), display=f"Class {result}")
    func = _CONVERSIONS.get(kind, {}).get((from_unit, to_unit))
    if not func:
        raise HTTPException(status_code=400, detail="Unsupported conversion")
    result = float(func(payload.value))
    return ConversionResponse(**payload.model_dump(), result=result, display=uc.fmt(result))

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.material_planning import (
    DEFAULT_NESTING_EFFICIENCY,
    DEFAULT_SHEET_LENGTH_MM,
    DEFAULT_SHEET_WIDTH_MM,
    build_material_plan,
)


def render_material_plan_section(items: list[dict]) -> None:
    """Render material planning controls and generated review tables."""
    st.markdown("""
    <div class="gq-step" style="border-left-color:#9a6418">
      <div class="gq-step-label">
        <span class="gq-step-badge" style="background:#9a6418">3</span>
        <p class="gq-step-title">Material Planning</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    cfg = st.session_state.setdefault(
        "_material_plan_config",
        {
            "sheet_width_mm": DEFAULT_SHEET_WIDTH_MM,
            "sheet_length_mm": DEFAULT_SHEET_LENGTH_MM,
            "nesting_efficiency": DEFAULT_NESTING_EFFICIENCY,
        },
    )

    c1, c2, c3, c4 = st.columns([1.4, 1.4, 1.4, 2])
    cfg["sheet_width_mm"] = c1.number_input(
        "Sheet width (mm)",
        min_value=100.0,
        value=float(cfg.get("sheet_width_mm") or DEFAULT_SHEET_WIDTH_MM),
        step=50.0,
        key="mp_sheet_width",
    )
    cfg["sheet_length_mm"] = c2.number_input(
        "Sheet length (mm)",
        min_value=100.0,
        value=float(cfg.get("sheet_length_mm") or DEFAULT_SHEET_LENGTH_MM),
        step=50.0,
        key="mp_sheet_length",
    )
    cfg["nesting_efficiency"] = c3.number_input(
        "Nesting efficiency",
        min_value=0.10,
        max_value=1.00,
        value=float(cfg.get("nesting_efficiency") or DEFAULT_NESTING_EFFICIENCY),
        step=0.01,
        format="%.2f",
        key="mp_nesting_efficiency",
    )
    with c4:
        st.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
        if st.button("Create Material Plan", type="secondary", key="mp_create_btn"):
            st.session_state["_material_plan"] = build_material_plan(
                items,
                sheet_width_mm=cfg["sheet_width_mm"],
                sheet_length_mm=cfg["sheet_length_mm"],
                nesting_efficiency=cfg["nesting_efficiency"],
            )
            st.session_state.pop("_material_plan_review_df", None)
            st.rerun()

    plan = st.session_state.get("_material_plan")
    if not plan:
        st.caption("Create a material plan from the current working list when the draft is ready for production review.")
        return

    totals = plan.get("totals", {})
    m1, m2, m3 = st.columns(3)
    m1.metric("Components", int(totals.get("component_count") or 0))
    m2.metric("Sheet Demand", f"{float(totals.get('sheet_count') or 0):,.2f}")
    m3.metric("Estimated Weight", f"{float(totals.get('total_weight_kg') or 0):,.3f} kg")

    warnings = plan.get("warnings") or []
    if warnings:
        with st.expander(f"Review flags ({len(warnings)})", expanded=True):
            for warning in warnings:
                st.write(f"- {warning}")

    with st.expander("Planning assumptions", expanded=False):
        for assumption in plan.get("assumptions") or []:
            st.write(f"- {assumption}")

    summary_df = pd.DataFrame(plan.get("summary") or [])
    if not summary_df.empty:
        st.markdown("**Material Summary**")
        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "material": st.column_config.TextColumn("Material", width="medium"),
                "stock_form": st.column_config.TextColumn("Stock Form", width="medium"),
                "components": st.column_config.NumberColumn("Rows", width="small"),
                "sheets_required": st.column_config.NumberColumn("Sheets", format="%.2f", width="small"),
                "total_weight_kg": st.column_config.NumberColumn("Weight kg", format="%.3f", width="small"),
                "stock_qty": st.column_config.NumberColumn("Stock Qty", format="%.2f", width="small"),
            },
        )

    rows_df = pd.DataFrame(plan.get("rows") or [])
    if rows_df.empty:
        st.info("No plannable items found in this draft.")
        return

    display_cols = [
        "reviewed",
        "line_no",
        "gasket_type",
        "component",
        "material",
        "stock_form",
        "quote_qty",
        "quote_uom",
        "stock_qty",
        "stock_uom",
        "od_mm",
        "id_mm",
        "thickness_mm",
        "blank_area_m2",
        "sheets_required",
        "unit_weight_kg",
        "total_weight_kg",
        "density_g_cm3",
        "basis",
        "calculation_notes",
        "planner_notes",
        "description",
    ]
    rows_df = rows_df[[col for col in display_cols if col in rows_df.columns]]

    if "_material_plan_review_df" in st.session_state:
        saved = st.session_state["_material_plan_review_df"]
        if len(saved) == len(rows_df):
            rows_df["reviewed"] = saved.get("reviewed", rows_df["reviewed"])
            rows_df["planner_notes"] = saved.get("planner_notes", rows_df["planner_notes"])

    edited = st.data_editor(
        rows_df,
        use_container_width=True,
        hide_index=True,
        height=min(120 + 35 * len(rows_df), 620),
        column_config={
            "reviewed": st.column_config.CheckboxColumn("Reviewed", width="small"),
            "line_no": st.column_config.NumberColumn("#", width="small", disabled=True),
            "gasket_type": st.column_config.TextColumn("Type", width="small", disabled=True),
            "component": st.column_config.TextColumn("Component", width="medium", disabled=True),
            "material": st.column_config.TextColumn("Material", width="medium", disabled=True),
            "stock_form": st.column_config.TextColumn("Stock Form", width="medium", disabled=True),
            "quote_qty": st.column_config.NumberColumn("Quote Qty", width="small", disabled=True),
            "quote_uom": st.column_config.TextColumn("UoM", width="small", disabled=True),
            "stock_qty": st.column_config.NumberColumn("Stock Qty", format="%.2f", width="small", disabled=True),
            "stock_uom": st.column_config.TextColumn("Stock UoM", width="small", disabled=True),
            "od_mm": st.column_config.NumberColumn("OD mm", format="%.2f", width="small", disabled=True),
            "id_mm": st.column_config.NumberColumn("ID mm", format="%.2f", width="small", disabled=True),
            "thickness_mm": st.column_config.NumberColumn("Thk mm", format="%.2f", width="small", disabled=True),
            "blank_area_m2": st.column_config.NumberColumn("Blank m2", format="%.4f", width="small", disabled=True),
            "sheets_required": st.column_config.NumberColumn("Sheets", format="%.2f", width="small", disabled=True),
            "unit_weight_kg": st.column_config.NumberColumn("Unit kg", format="%.4f", width="small", disabled=True),
            "total_weight_kg": st.column_config.NumberColumn("Total kg", format="%.4f", width="small", disabled=True),
            "density_g_cm3": st.column_config.NumberColumn("Density", format="%.2f", width="small", disabled=True),
            "basis": st.column_config.TextColumn("Basis", width="medium", disabled=True),
            "calculation_notes": st.column_config.TextColumn("Calc Notes", width="large", disabled=True),
            "planner_notes": st.column_config.TextColumn("Planner Notes", width="large"),
            "description": st.column_config.TextColumn("Description", width="large", disabled=True),
        },
        key="mp_review_editor",
    )
    st.session_state["_material_plan_review_df"] = edited

    csv_bytes = edited.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Material Plan CSV",
        data=csv_bytes,
        file_name="material_plan.csv",
        mime="text/csv",
        key="mp_download_csv",
    )

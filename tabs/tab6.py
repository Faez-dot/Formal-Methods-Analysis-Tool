"""Tab 6 — Full Report with Export."""
import streamlit as st
from datetime import datetime


def render():
    st.subheader("📊 Full Analysis Report")

    model = st.session_state.get("feature_model")
    formulas = st.session_state.get("formulas", [])
    mwps = st.session_state.get("mwp_results")
    mapping = st.session_state.get("feature_file_mapping", {})
    deps = st.session_state.get("file_dependencies", [])
    inferred = st.session_state.get("inferred_feature_deps", [])
    inconsistencies = st.session_state.get("inconsistencies", [])

    # ── Generate report text ───────────────────────────────────────────────
    report_lines = [
        "=" * 70,
        "      FORMAL METHODS ANALYSIS TOOL — FULL REPORT",
        f"      Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 70,
        "",
    ]

    # Section 1: Feature Model
    report_lines += ["── SECTION 1: FEATURE MODEL ──", ""]
    if model:
        report_lines += [
            f"Root Feature : {model['root']['name'] if model['root'] else 'N/A'}",
            f"Total Features: {len(model['all_features'])}",
            f"Features: {', '.join(model['all_features'])}",
            "",
            "Cross-Tree Constraints:",
        ]
        for c in model.get("constraints", []):
            if c["type"] == "requires":
                report_lines.append(f"  REQUIRES : {c['from']} → {c['to']}")
            elif c["type"] == "excludes":
                report_lines.append(f"  EXCLUDES : ¬({c['from']} ∧ {c['to']})")
            elif c["type"] == "english":
                report_lines.append(f"  ENGLISH  : {c['text']}")
    else:
        report_lines.append("No feature model loaded.")
    report_lines.append("")

    # Section 2: Propositional Logic Formulas
    report_lines += ["── SECTION 2: PROPOSITIONAL LOGIC FORMULAS ──", ""]
    if formulas:
        for f in formulas:
            if "english" not in f:
                report_lines.append(f"  [{f['label']}]  {f['formula']}")
    else:
        report_lines.append("No formulas generated.")
    report_lines.append("")

    # Section 3: MWPs
    report_lines += ["── SECTION 3: MINIMUM WORKING PRODUCTS (MWPs) ──", ""]
    if mwps is None:
        report_lines.append("MWPs not computed yet.")
    elif len(mwps) == 0:
        report_lines.append("No valid configuration found (UNSAT).")
    else:
        report_lines.append(f"Total MWPs found: {len(mwps)}")
        for i, mwp in enumerate(mwps, 1):
            report_lines.append(f"  MWP #{i} ({len(mwp)} features): {', '.join(mwp)}")
    report_lines.append("")

    # Section 4: Feature-to-File Mapping
    report_lines += ["── SECTION 4: FEATURE-TO-FILE MAPPING ──", ""]
    n_mapped = 0
    for feat, files in mapping.items():
        if files:
            report_lines.append(f"  {feat} → {', '.join(files)}")
            n_mapped += 1
    if n_mapped == 0:
        report_lines.append("No mappings defined.")
    report_lines.append("")

    # Section 5: File Dependencies
    report_lines += ["── SECTION 5: FILE-LEVEL DEPENDENCIES ──", ""]
    internal = [d for d in deps if not d.get("external")]
    if internal:
        for d in internal:
            report_lines.append(f"  {d['from']} → {d['to']}  (import: {d['raw_import']})")
    else:
        report_lines.append("No internal file dependencies detected.")
    report_lines.append("")

    # Section 6: Feature-Level Dependencies
    report_lines += ["── SECTION 6: INFERRED FEATURE-LEVEL DEPENDENCIES ──", ""]
    if inferred:
        for d in inferred:
            report_lines.append(
                f"  {d['feature_from']} → {d['feature_to']}  "
                f"(via {d['via_file_from']} → {d['via_file_to']})"
            )
    else:
        report_lines.append("No feature-level dependencies inferred.")
    report_lines.append("")

    # Section 7: Inconsistencies
    report_lines += ["── SECTION 7: INCONSISTENCIES ──", ""]
    if inconsistencies:
        for inc in inconsistencies:
            report_lines += [
                f"  TYPE       : {inc['type']}",
                f"  Features   : {inc['feature_a']} ↔ {inc['feature_b']}",
                f"  Evidence   : {inc['evidence']}",
                f"  Explanation: {inc['explanation']}",
                f"  Fix        : {inc['fix']}",
                "",
            ]
    else:
        report_lines.append("No inconsistencies found.")
    report_lines.append("")
    report_lines.append("=" * 70)
    report_lines.append("END OF REPORT")

    report_text = "\n".join(report_lines)

    # ── Display in UI ───────────────────────────────────────────────────────
    col1, col2 = st.columns([3, 1])
    with col2:
        st.download_button(
            label="⬇️ Export as .txt",
            data=report_text,
            file_name=f"fm_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True,
        )
        if st.button("📋 Copy to Clipboard", use_container_width=True):
            st.code(report_text)

    # Sections preview
    with st.expander("📌 Feature Model Summary", expanded=True):
        if model:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Features", len(model["all_features"]))
            c2.metric("Constraints", len(model.get("constraints", [])))
            c3.metric("MWPs Found", len(mwps) if mwps else "—")
        else:
            st.info("No feature model loaded.")

    with st.expander("🧮 Propositional Logic Formulas", expanded=False):
        for f in formulas:
            if "english" not in f:
                st.markdown(
                    f'<div class="formula-box"><b>{f["label"]}</b><br>{f["formula"]}</div>',
                    unsafe_allow_html=True,
                )

    with st.expander("⚡ MWP Results", expanded=False):
        if mwps:
            for i, mwp in enumerate(mwps, 1):
                badges = " ".join(f'<span class="badge">{f}</span>' for f in mwp)
                st.markdown(
                    f'<div class="mwp-card"><b>MWP #{i}</b>  {badges}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No MWPs computed.")

    with st.expander("🗺️ Feature-to-File Mapping", expanded=False):
        import pandas as pd
        rows = [{"Feature": k, "Mapped Files": ", ".join(v)} for k, v in mapping.items() if v]
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("No mappings defined.")

    with st.expander("⚠️ Inconsistencies", expanded=True):
        type_colors = {
            "MISSING": ("inc-missing", "🟡"),
            "INCORRECT": ("inc-incorrect", "🔴"),
            "HIDDEN": ("inc-hidden", "🟣"),
        }
        if inconsistencies:
            for inc in inconsistencies:
                css, icon = type_colors.get(inc["type"], ("inc-missing", "⚪"))
                st.markdown(
                    f'<div class="inc-card {css}">'
                    f'<b>{icon} {inc["type"]}</b>: '
                    f'<code>{inc["feature_a"]} ↔ {inc["feature_b"]}</code><br>'
                    f'{inc["explanation"]}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No inconsistencies detected.")

    st.markdown("---")
    st.markdown("**Full report text:**")
    st.text_area("Report", value=report_text, height=400, label_visibility="collapsed")

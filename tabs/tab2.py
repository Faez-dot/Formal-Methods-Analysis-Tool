"""Tab 2 — MWP (Minimum Working Product) Results."""
import streamlit as st
from utils.sat_solver import compute_mwps


def render():
    st.subheader("⚡ Minimum Working Products (MWPs)")

    model = st.session_state.get("feature_model")
    clauses = st.session_state.get("clauses", [])
    var_map = st.session_state.get("var_map", {})

    if not model:
        st.info("👈 Go to **XML Input & Logic** tab first to load a feature model.")
        return

    if not clauses:
        st.warning("No logic clauses generated yet. Re-visit Tab 1.")
        return

    all_features = model.get("all_features", [])
    root_name = model["root"]["name"] if model["root"] else ""

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(
            f"Feature model loaded with **{len(all_features)}** features. "
            f"Click below to compute all minimal valid configurations."
        )
    with col2:
        compute_btn = st.button("🔍 Compute MWPs", use_container_width=True, type="primary")

    if compute_btn:
        with st.spinner("Running SAT solver — finding all MWPs..."):
            try:
                mwps = compute_mwps(clauses, var_map, all_features, root_name)
                st.session_state["mwp_results"] = mwps
            except Exception as e:
                st.error(f"SAT solver error: {e}")
                return

    mwps = st.session_state.get("mwp_results")

    if mwps is None:
        st.info("Click **Compute MWPs** to start analysis.")
        return

    if len(mwps) == 0:
        st.error("❌ No valid configuration found. The feature model may be unsatisfiable.")
        return

    st.success(f"✅ Found **{len(mwps)}** Minimum Working Product(s).")

    # Summary table
    import pandas as pd
    table_data = []
    for i, mwp in enumerate(mwps, 1):
        table_data.append({"MWP #": i, "# Features": len(mwp), "Features": ", ".join(mwp)})
    st.dataframe(pd.DataFrame(table_data), use_container_width=True)

    st.markdown("---")
    st.markdown("### Detailed MWP Cards")

    for i, mwp in enumerate(mwps, 1):
        with st.expander(f"MWP #{i} — {len(mwp)} features selected", expanded=(i <= 3)):
            badges = ""
            for feat in mwp:
                fnode = _find_feature_node(model["root"], feat)
                ftype = fnode["type"] if fnode else "optional"
                css = "badge-mandatory" if ftype == "mandatory" else "badge-optional"
                badges += f'<span class="badge {css}">{feat}</span> '
            st.markdown(f'<div class="mwp-card">{badges}</div>', unsafe_allow_html=True)


def _find_feature_node(node, name):
    if node is None:
        return None
    if node["name"] == name:
        return node
    for c in node.get("children", []):
        r = _find_feature_node(c, name)
        if r:
            return r
    for g in node.get("groups", []):
        for m in g["members"]:
            r = _find_feature_node(m, name)
            if r:
                return r
    return None

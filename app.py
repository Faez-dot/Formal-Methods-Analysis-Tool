"""
app.py — Main Streamlit entry point for the Formal Methods Analysis Tool.
Run with: streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Formal Methods Analysis Tool",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
body { background: #0f1117; }
.block-container { padding-top: 1.5rem; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] {
    background: #1e2130; border-radius: 8px 8px 0 0;
    padding: 8px 18px; font-weight: 600; color: #aab;
}
.stTabs [aria-selected="true"] {
    background: #3b5bdb !important; color: #fff !important;
}
.formula-box {
    background: #1a1d2e; border-left: 4px solid #4c6ef5;
    border-radius: 6px; padding: 10px 14px; margin: 4px 0;
    font-family: 'Courier New', monospace; font-size: 0.92rem; color: #c8d0ff;
}
.mwp-card {
    background: #1c2340; border: 1px solid #3b5bdb;
    border-radius: 10px; padding: 12px 16px; margin: 6px 0;
}
.badge {
    display: inline-block; background: #364fc7; color: #fff;
    border-radius: 12px; padding: 2px 10px; margin: 2px;
    font-size: 0.82rem;
}
.badge-mandatory { background: #2f9e44; }
.badge-optional  { background: #1864ab; }
.inc-missing   { border-left: 4px solid #f59f00; background: #1f1a0e; }
.inc-incorrect { border-left: 4px solid #e03131; background: #1f0e0e; }
.inc-hidden    { border-left: 4px solid #9775fa; background: #140e1f; }
.inc-card { border-radius: 8px; padding: 12px 16px; margin: 8px 0; }
.valid-box   { background:#0b3d1a; border:1px solid #2f9e44;
               border-radius:8px; padding:12px; color:#69db7c; font-weight:700; }
.invalid-box { background:#3d0b0b; border:1px solid #e03131;
               border-radius:8px; padding:12px; color:#ff6b6b; font-weight:700; }
.tree-node { padding: 3px 0; }
.tree-mandatory::before { content:"● "; color:#2f9e44; font-weight:900; }
.tree-optional::before  { content:"○ "; color:#74c0fc; }
.tree-xor::before       { content:"⊕ "; color:#f08c00; font-weight:900; }
.tree-or::before        { content:"⊙ "; color:#9775fa; font-weight:900; }
</style>
""", unsafe_allow_html=True)

# ── Session state defaults ─────────────────────────────────────────────────
for key, default in {
    "feature_model": None,
    "formulas": [],
    "clauses": [],
    "var_map": {},
    "mwp_results": None,
    "selected_features": set(),
    "verify_result": None,
    "english_constraints_confirmed": {},
    "codebase_files": {},
    "feature_file_mapping": {},
    "file_dependencies": [],
    "inferred_feature_deps": [],
    "inconsistencies": [],
    "impact_result": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Header ─────────────────────────────────────────────────────────────────
st.markdown("## 🔬 Formal Methods Analysis Tool")
st.markdown("*Feature Model Analysis + Feature-to-Code Impact Analysis*")
st.divider()

# ── Sidebar Impact Analysis ────────────────────────────────────────────────
with st.sidebar:
    st.header("💥 Impact Analysis")
    selected = list(st.session_state.get("selected_features", set()))
    
    if selected:
        st.markdown(f"**Selected Features:**\n" + ", ".join(f"`{f}`" for f in selected))
        
        mapping = st.session_state.get("feature_file_mapping", {})
        closure = st.session_state.get("dep_closure", {})
        
        from utils.consistency_checker import compute_impact_analysis
        impact = compute_impact_analysis(selected, mapping, closure)
        
        st.markdown("---")
        if impact["direct_files"]:
            st.markdown("**Directly affected files:**")
            for f in impact["direct_files"]:
                st.markdown(f"- 📄 `{f}`")
        else:
            st.info("No direct files mapped to selected features.")
            
        st.markdown("---")
        if impact["indirect_files"]:
            st.markdown("**Indirectly triggered files:**")
            for f in impact["indirect_files"]:
                st.markdown(f"- 🔗 `{f}`")
        else:
            st.info("No indirect dependencies.")
    else:
        st.info("Select features in the **Feature Tree** tab to see their impact on the codebase.")

# ── Tabs ───────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "📄 XML Input & Logic",
    "⚡ MWP Results",
    "🌳 Feature Tree",
    "💻 Codebase & Mapping",
    "🔗 Dependencies & Analysis",
    "📊 Report",
])

from tabs import tab1, tab2, tab3, tab4, tab5, tab6

with tabs[0]: tab1.render()
with tabs[1]: tab2.render()
with tabs[2]: tab3.render()
with tabs[3]: tab4.render()
with tabs[4]: tab5.render()
with tabs[5]: tab6.render()

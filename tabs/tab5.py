"""Tab 5 — Dependencies & Consistency Analysis."""
import streamlit as st
from utils.dependency_extractor import extract_dependencies, build_transitive_closure
from utils.consistency_checker import (
    infer_feature_dependencies,
    check_consistency,
    compute_impact_analysis,
)


def render():
    st.subheader("🔗 Dependency Analysis & Inconsistency Detection")

    code_files = st.session_state.get("codebase_files", {})
    mapping = st.session_state.get("feature_file_mapping", {})
    model = st.session_state.get("feature_model")

    if not code_files:
        st.info("👈 Upload code files in the **Codebase & Mapping** tab first.")
        return

    analyze_btn = st.button("🚀 Run Full Analysis", type="primary", use_container_width=False)

    if analyze_btn:
        with st.spinner("Extracting dependencies..."):
            deps = extract_dependencies(code_files)
            st.session_state["file_dependencies"] = deps

            closure = build_transitive_closure(deps)

            inferred = infer_feature_dependencies(mapping, deps)
            st.session_state["inferred_feature_deps"] = inferred

            constraints = model.get("constraints", []) if model else []
            inconsistencies = check_consistency(inferred, constraints)
            st.session_state["inconsistencies"] = inconsistencies

            # Impact analysis with currently selected features
            selected = list(st.session_state.get("selected_features", set()))
            impact = compute_impact_analysis(selected, mapping, closure)
            st.session_state["impact_result"] = impact
            st.session_state["dep_closure"] = closure

    deps = st.session_state.get("file_dependencies", [])
    inferred = st.session_state.get("inferred_feature_deps", [])
    inconsistencies = st.session_state.get("inconsistencies", [])
    impact = st.session_state.get("impact_result")
    closure = st.session_state.get("dep_closure", {})

    # ── Section 1: File-level dependencies ─────────────────────────────────
    st.markdown("---")
    st.markdown("### 📁 File-Level Dependencies")
    internal_deps = [d for d in deps if not d.get("external")]
    external_deps = [d for d in deps if d.get("external")]

    if internal_deps:
        for d in internal_deps:
            st.markdown(
                f'<div class="formula-box">📄 <b>{d["from"]}</b> → <b>{d["to"]}</b>'
                f' &nbsp; <span style="color:#888;font-size:0.8rem">via `{d["raw_import"]}`</span></div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No internal file dependencies detected yet. Click **Run Full Analysis**.")

    if external_deps:
        with st.expander(f"External imports ({len(external_deps)})"):
            for d in external_deps:
                st.markdown(f"- `{d['from']}` → `{d['to']}`")

    # ── Section 2: Dependency Graph (SVG via pyvis) ─────────────────────────
    st.markdown("---")
    st.markdown("### 🕸️ Dependency Graph")
    if internal_deps:
        _render_graph(internal_deps)
    else:
        st.info("Graph will appear after analysis.")

    # ── Section 3: Feature-level inferred dependencies ──────────────────────
    st.markdown("---")
    st.markdown("### 🔮 Inferred Feature-Level Dependencies")
    if inferred:
        for d in inferred:
            st.markdown(
                f'<div class="formula-box">'
                f'🧩 <b>{d["feature_from"]}</b> → <b>{d["feature_to"]}</b>'
                f' &nbsp;<span style="color:#888;font-size:0.8rem">'
                f'(via {d["via_file_from"]} → {d["via_file_to"]})</span></div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No feature-level dependencies inferred yet.")

    # ── Section 4: Inconsistencies ──────────────────────────────────────────
    st.markdown("---")
    st.markdown("### ⚠️ Inconsistency Detection")
    if inconsistencies:
        type_colors = {
            "MISSING": ("inc-missing", "🟡", "Missing Constraint"),
            "INCORRECT": ("inc-incorrect", "🔴", "Incorrect Constraint"),
            "HIDDEN": ("inc-hidden", "🟣", "Hidden/Unverified Constraint"),
        }
        for inc in inconsistencies:
            css, icon, label = type_colors.get(inc["type"], ("inc-missing", "⚪", inc["type"]))
            st.markdown(
                f'<div class="inc-card {css}">'
                f'<b>{icon} {label}</b> &nbsp; '
                f'<code>{inc["feature_a"]} ↔ {inc["feature_b"]}</code><br>'
                f'<b>Evidence:</b> {inc["evidence"]}<br>'
                f'<b>Explanation:</b> {inc["explanation"]}<br>'
                f'<b>Fix:</b> <i>{inc["fix"]}</i>'
                f'</div>',
                unsafe_allow_html=True,
            )
    elif not deps:
        st.info("Run analysis to detect inconsistencies.")
    else:
        st.success("✅ No inconsistencies detected!")

    # ── Section 5: Impact Analysis ──────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 💥 Impact Analysis")
    selected = list(st.session_state.get("selected_features", set()))

    if selected and impact:
        st.markdown(f"**Selected features:** {', '.join(f'`{f}`' for f in selected)}")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Directly affected files:**")
            for f in impact["direct_files"]:
                st.markdown(f"- 📄 `{f}`")
            if not impact["direct_files"]:
                st.info("No direct file mappings found.")
        with col2:
            st.markdown("**Indirectly triggered files (transitive):**")
            for f in impact["indirect_files"]:
                st.markdown(f"- 🔗 `{f}`")
            if not impact["indirect_files"]:
                st.info("No indirect dependencies.")
    else:
        st.info("Select features in **Feature Tree** tab and run analysis to see impact.")


def _render_graph(deps):
    """Render dependency graph using pyvis embedded as HTML."""
    try:
        from pyvis.network import Network
        import tempfile, os

        net = Network(height="400px", width="100%", bgcolor="#1a1d2e",
                      font_color="#c8d0ff", directed=True)
        net.set_options("""
        {
          "nodes": { "color": { "background": "#364fc7", "border": "#4c6ef5" },
                     "font": { "size": 14 } },
          "edges": { "color": "#74c0fc", "arrows": { "to": { "enabled": true } } },
          "physics": { "stabilization": true }
        }
        """)

        nodes_added = set()
        for d in deps:
            if d["from"] not in nodes_added:
                net.add_node(d["from"], label=d["from"], title=d["from"])
                nodes_added.add(d["from"])
            if d["to"] not in nodes_added:
                net.add_node(d["to"], label=d["to"], title=d["to"])
                nodes_added.add(d["to"])
            net.add_edge(d["from"], d["to"], title=d.get("raw_import", ""))

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w") as f:
            net.save_graph(f.name)
            html_path = f.name

        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        os.unlink(html_path)

        st.components.v1.html(html_content, height=430, scrolling=False)

    except ImportError:
        # Fallback: simple SVG
        _render_simple_svg(deps)


def _render_simple_svg(deps):
    """Minimal SVG fallback graph."""
    nodes = list({d["from"] for d in deps} | {d["to"] for d in deps})
    n = len(nodes)
    if n == 0:
        return
    import math
    cx, cy, r = 300, 200, 140
    positions = {
        node: (
            cx + r * math.cos(2 * math.pi * i / n),
            cy + r * math.sin(2 * math.pi * i / n),
        )
        for i, node in enumerate(nodes)
    }
    svg_lines = ['<svg width="600" height="400" style="background:#1a1d2e;border-radius:10px">']
    for d in deps:
        x1, y1 = positions[d["from"]]
        x2, y2 = positions[d["to"]]
        svg_lines.append(
            f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
            f'stroke="#4c6ef5" stroke-width="1.5" marker-end="url(#arrow)"/>'
        )
    for node, (x, y) in positions.items():
        label = node[:12] + ".." if len(node) > 14 else node
        svg_lines.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="22" fill="#364fc7" stroke="#4c6ef5" stroke-width="2"/>'
        )
        svg_lines.append(
            f'<text x="{x:.0f}" y="{y+5:.0f}" text-anchor="middle" fill="#c8d0ff" font-size="9">{label}</text>'
        )
    svg_lines.append(
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" '
        'refX="6" refY="3" orient="auto">'
        '<path d="M0,0 L0,6 L9,3 z" fill="#4c6ef5"/></marker></defs>'
    )
    svg_lines.append("</svg>")
    st.markdown("".join(svg_lines), unsafe_allow_html=True)

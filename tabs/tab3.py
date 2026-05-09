"""Tab 3 — Interactive Feature Tree & Configuration Verification."""
import streamlit as st
from utils.sat_solver import verify_config


def render():
    st.subheader("🌳 Feature Tree — Interactive Configuration")

    model = st.session_state.get("feature_model")
    if not model or not model.get("root"):
        st.info("👈 Load a feature model in **XML Input & Logic** tab first.")
        return

    st.markdown(
        "**Legend:** "
        '<span style="color:#2f9e44">● Mandatory</span> &nbsp;'
        '<span style="color:#74c0fc">○ Optional</span> &nbsp;'
        '<span style="color:#f08c00">⊕ XOR group</span> &nbsp;'
        '<span style="color:#9775fa">⊙ OR group</span>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # Initialize selected features from root (mandatory auto-selected)
    if "selected_features" not in st.session_state or not st.session_state["selected_features"]:
        mandatory = _collect_mandatory(model["root"])
        st.session_state["selected_features"] = set(mandatory)

    selected = st.session_state["selected_features"]

    # Render tree recursively
    _render_node(model["root"], selected, depth=0, parent_selected=True)

    st.session_state["selected_features"] = selected

    st.markdown("---")
    col1, col2 = st.columns([1, 2])
    with col1:
        verify_btn = st.button("✅ Verify Configuration", type="primary", use_container_width=True)
    with col2:
        if st.button("🔄 Reset Selection", use_container_width=True):
            mandatory = _collect_mandatory(model["root"])
            st.session_state["selected_features"] = set(mandatory)
            st.session_state["verify_result"] = None
            st.rerun()

    if verify_btn:
        clauses = st.session_state.get("clauses", [])
        var_map = st.session_state.get("var_map", {})
        constraints = model.get("constraints", [])
        if not clauses:
            st.warning("No logic clauses found. Parse the XML first.")
        else:
            result = verify_config(
                list(selected),
                clauses,
                var_map,
                model["all_features"],
                constraints,
            )
            st.session_state["verify_result"] = result

    result = st.session_state.get("verify_result")
    if result:
        if result["valid"]:
            st.markdown(
                '<div class="valid-box">✅ Valid Configuration — All constraints satisfied!</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="invalid-box">❌ Invalid Configuration — Constraints violated!</div>',
                unsafe_allow_html=True,
            )
            st.markdown("**Violations:**")
            for v in result["violations"]:
                st.error(f"🔴 **{v['constraint']}** — {v['explanation']}")

    # Show currently selected features
    st.markdown("---")
    st.markdown(f"**Currently selected ({len(selected)}):** " +
                ", ".join(f"`{f}`" for f in sorted(selected)) if selected else "*None selected*")


def _render_node(node, selected: set, depth: int, parent_selected: bool):
    """Recursively render a feature node as a checkbox."""
    name = node["name"]
    ftype = node.get("type", "optional")
    indent = "&nbsp;" * (depth * 6)

    is_root = ftype == "root"
    is_mandatory = ftype == "mandatory"
    is_disabled = is_mandatory and parent_selected

    if is_root:
        icon = "🌱"
        # Root always selected
        selected.add(name)
        st.markdown(f'{indent}<span class="tree-node">{icon} <b>{name}</b> <i style="color:#aaa;font-size:0.8rem">(root)</i></span>',
                    unsafe_allow_html=True)
        node_selected = True
    else:
        if ftype == "mandatory":
            icon = "●"
            color = "#2f9e44"
        else:
            icon = "○"
            color = "#74c0fc"

        label = f"{name} {'[mandatory]' if is_mandatory else '[optional]'}"
        default_val = name in selected

        if is_disabled:
            selected.add(name)
            st.markdown(
                f'{indent}<span style="color:{color}">{icon}</span> '
                f'<b>{name}</b> <i style="color:#888;font-size:0.8rem">(auto-selected, mandatory)</i>',
                unsafe_allow_html=True,
            )
            node_selected = True
        else:
            cb_val = st.checkbox(
                f"{icon} {name}",
                value=default_val,
                key=f"feat_{name}_{depth}",
                disabled=(not parent_selected and not is_root),
            )
            if cb_val:
                selected.add(name)
            else:
                selected.discard(name)
            node_selected = cb_val and parent_selected

    # Render direct children
    for child in node.get("children", []):
        _render_node(child, selected, depth + 1, node_selected)

    # Render groups
    for group in node.get("groups", []):
        gtype = group["type"]
        members = group["members"]
        g_indent = "&nbsp;" * ((depth + 1) * 6)

        if gtype == "xor":
            st.markdown(
                f'{g_indent}<span style="color:#f08c00;font-weight:700">⊕ XOR Group</span>'
                f' <i style="color:#888;font-size:0.78rem">(select exactly one)</i>',
                unsafe_allow_html=True,
            )
            member_names = [m["name"] for m in members]
            # Find currently selected member
            current = [m for m in member_names if m in selected]
            chosen = st.radio(
                "Select one:",
                options=["(none)"] + member_names,
                index=(member_names.index(current[0]) + 1) if current else 0,
                key=f"xor_{name}_{depth}",
                disabled=not node_selected,
                horizontal=True,
                label_visibility="collapsed",
            ) if node_selected else "(none)"
            for m in members:
                if m["name"] == chosen:
                    selected.add(m["name"])
                    _render_node(m, selected, depth + 2, node_selected)
                else:
                    selected.discard(m["name"])

        elif gtype == "or":
            st.markdown(
                f'{g_indent}<span style="color:#9775fa;font-weight:700">⊙ OR Group</span>'
                f' <i style="color:#888;font-size:0.78rem">(select at least one)</i>',
                unsafe_allow_html=True,
            )
            for member in members:
                _render_node(member, selected, depth + 2, node_selected)


def _collect_mandatory(node) -> list:
    """Collect all mandatory features that must always be selected."""
    result = [node["name"]]
    for child in node.get("children", []):
        if child.get("type") == "mandatory":
            result += _collect_mandatory(child)
    return result

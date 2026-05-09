"""Tab 4 — Codebase Input & Feature-to-File Mapping."""
import streamlit as st
import os


def render():
    st.subheader("💻 Codebase Input")

    model = st.session_state.get("feature_model")
    if not model:
        st.info("👈 Load a feature model first (Tab 1).")
        return

    st.markdown(
        "Upload your source files below. For a folder, select all files inside it "
        "(or use Ctrl+A in the file dialog). Git URLs are not directly fetchable "
        "in the browser — paste file contents manually if needed."
    )

    st.text_input("🔗 Or paste a Git repo URL", placeholder="https://github.com/...", help="Note: For Git URL, files will need to be manually pasted or fetched.")

    uploaded_files = st.file_uploader(
        "Upload source files (select multiple)",
        accept_multiple_files=True,
        type=None,
        key="code_files_upload",
    )

    if uploaded_files:
        files_dict = {}
        for uf in uploaded_files:
            try:
                content = uf.read().decode("utf-8", errors="replace")
                files_dict[uf.name] = content
            except Exception:
                files_dict[uf.name] = ""
        st.session_state["codebase_files"] = files_dict
        st.success(f"✅ Loaded **{len(files_dict)}** file(s).")

    code_files = st.session_state.get("codebase_files", {})

    if not code_files:
        st.info("No files loaded yet.")
        return

    # File tree display
    st.markdown("### 📁 Loaded Files")
    for fname in sorted(code_files.keys()):
        size = len(code_files[fname])
        with st.expander(f"📄 {fname}  ({size} chars)"):
            lang = _detect_lang(fname)
            st.code(code_files[fname][:2000] + ("..." if size > 2000 else ""), language=lang)

    # Feature-to-file mapping table
    st.markdown("---")
    st.subheader("🗺️ Feature → File Mapping")
    st.markdown(
        "For each feature, select which files implement it. "
        "At least **5 mappings** are required for dependency analysis."
    )

    features = model.get("all_features", [])
    file_names = sorted(code_files.keys())
    mapping = st.session_state.get("feature_file_mapping", {})

    for feat in features:
        default = mapping.get(feat, [])
        chosen = st.multiselect(
            f"**{feat}**",
            options=file_names,
            default=[d for d in default if d in file_names],
            key=f"map_{feat}",
        )
        mapping[feat] = chosen

    st.session_state["feature_file_mapping"] = mapping

    # Count non-empty mappings
    n_mapped = sum(1 for v in mapping.values() if v)
    if n_mapped >= 5:
        st.success(f"✅ {n_mapped} feature(s) mapped to files.")
    else:
        st.warning(f"⚠️ {n_mapped}/5 mappings done. Please map at least 5 features.")


def _detect_lang(fname):
    ext = os.path.splitext(fname)[1].lower()
    return {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".java": "java", ".c": "c", ".cpp": "cpp", ".h": "c",
        ".jsx": "javascript", ".tsx": "typescript",
    }.get(ext, "text")

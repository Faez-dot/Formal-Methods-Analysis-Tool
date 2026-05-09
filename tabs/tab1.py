"""Tab 1 — XML Input & Logic Translation."""
import streamlit as st
from utils.xml_parser import parse_feature_model_xml
from utils.logic_translator import translate_feature_model, add_english_constraint_as_clause

SAMPLE_XML = """<featureModel>
  <feature name="Root" type="root">
    <feature name="FeatureA" type="mandatory">
      <feature name="FeatureA1" type="optional"/>
      <feature name="FeatureA2" type="optional"/>
    </feature>
    <feature name="FeatureB" type="optional">
      <group type="xor">
        <feature name="FeatureB1"/>
        <feature name="FeatureB2"/>
      </group>
    </feature>
    <feature name="FeatureC" type="optional">
      <group type="or">
        <feature name="FeatureC1"/>
        <feature name="FeatureC2"/>
      </group>
    </feature>
  </feature>
  <constraints>
    <constraint type="requires" from="FeatureA1" to="FeatureB1"/>
    <constraint type="excludes" from="FeatureA2" to="FeatureC1"/>
    <constraint type="english">FeatureC1 requires FeatureB</constraint>
  </constraints>
</featureModel>"""


def render():
    st.subheader("📄 Step 1: Upload Feature Model XML")

    col1, col2 = st.columns([1, 1])
    with col1:
        uploaded = st.file_uploader("Upload XML file", type=["xml"], key="xml_upload")
    with col2:
        use_sample = st.button("📋 Load Sample XML", use_container_width=True)

    xml_text = ""
    if uploaded:
        xml_text = uploaded.read().decode("utf-8")
    elif use_sample:
        xml_text = SAMPLE_XML
        st.session_state["_sample_loaded"] = True

    if st.session_state.get("_sample_loaded") and not uploaded:
        xml_text = SAMPLE_XML

    if xml_text:
        with st.expander("📜 Raw XML", expanded=False):
            st.code(xml_text, language="xml")

        # Parse
        model = parse_feature_model_xml(xml_text)
        if model["error"]:
            st.error(f"❌ Parse error: {model['error']}")
            return

        st.session_state["feature_model"] = model
        st.success(f"✅ Parsed **{len(model['all_features'])}** features, "
                   f"**{len(model['constraints'])}** constraints.")

        # Translate to logic
        result = translate_feature_model(model)
        st.session_state["formulas"] = result["formulas"]
        st.session_state["clauses"] = result["clauses"]
        st.session_state["var_map"] = result["var_map"].mapping

        # Show formulas
        st.subheader("🧮 Propositional Logic Formulas")
        english_pending = []
        for f in result["formulas"]:
            if "english" in f:
                english_pending.append(f)
            else:
                st.markdown(
                    f'<div class="formula-box"><b>{f["label"]}</b><br>{f["formula"]}</div>',
                    unsafe_allow_html=True,
                )

        # English constraint modal
        if english_pending:
            st.subheader("🗣️ English Constraints — Manual Translation Required")
            for ef in english_pending:
                txt = ef["english"]
                st.warning(f'**English constraint detected:** "{txt}"')
                confirmed = st.session_state["english_constraints_confirmed"]
                suggestion = _suggest_translation(txt, model["all_features"])
                key = f"eng_{hash(txt)}"
                user_formula = st.text_input(
                    f'Suggested formula (edit if needed):',
                    value=confirmed.get(key, suggestion),
                    key=key + "_input",
                )
                if st.button(f"✅ Confirm", key=key + "_btn"):
                    ok, msg = add_english_constraint_as_clause(
                        user_formula,
                        result["var_map"],
                        st.session_state["clauses"],
                        st.session_state["formulas"],
                    )
                    if ok:
                        st.success(msg)
                        st.session_state["english_constraints_confirmed"][key] = user_formula
                    else:
                        st.error(msg)

        # Constraints panel
        st.subheader("📌 Constraints Panel")
        raw_constraints = model["constraints"]
        if raw_constraints:
            for c in raw_constraints:
                if c["type"] == "requires":
                    st.markdown(f'<div class="formula-box">🔗 <b>Requires:</b> {c["from"]} → {c["to"]}</div>',
                                unsafe_allow_html=True)
                elif c["type"] == "excludes":
                    st.markdown(f'<div class="formula-box">🚫 <b>Excludes:</b> ¬({c["from"]} ∧ {c["to"]})</div>',
                                unsafe_allow_html=True)
                elif c["type"] == "english":
                    st.markdown(f'<div class="formula-box">💬 <b>English:</b> {c["text"]}</div>',
                                unsafe_allow_html=True)
        else:
            st.info("No cross-tree constraints found.")
    else:
        st.info("👆 Upload an XML file or click 'Load Sample XML' to begin.")


def _suggest_translation(text: str, features: list) -> str:
    """Very simple heuristic: find 'X requires Y' pattern."""
    text_lower = text.lower()
    if "requires" in text_lower:
        parts = text_lower.split("requires")
        if len(parts) == 2:
            a = _best_match(parts[0].strip(), features)
            b = _best_match(parts[1].strip(), features)
            if a and b:
                return f"{a} → {b}"
    if "excludes" in text_lower or "exclude" in text_lower:
        sep = "excludes" if "excludes" in text_lower else "exclude"
        parts = text_lower.split(sep)
        if len(parts) == 2:
            a = _best_match(parts[0].strip(), features)
            b = _best_match(parts[1].strip(), features)
            if a and b:
                return f"¬({a} ∧ {b})"
    return "A → B"


def _best_match(token: str, features: list):
    token = token.strip().replace(" ", "").lower()
    for f in features:
        if f.lower().replace(" ", "") == token:
            return f
        if token in f.lower():
            return f
    return None

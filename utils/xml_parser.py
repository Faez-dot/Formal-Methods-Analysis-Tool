"""
xml_parser.py — Parse Feature Model XML into a structured Python dict.

Supports:
  <feature name="X" type="mandatory|optional|root">
    <feature .../>
    <group type="xor|or">
      <feature .../>
    </group>
  </feature>
  <constraints>
    <constraint type="requires|excludes" from="A" to="B"/>
    <constraint type="english">some text</constraint>
  </constraints>
"""

import xml.etree.ElementTree as ET


def _parse_feature_node(elem, parent_name=None):
    """Recursively parse a <feature> element into a dict."""
    name = elem.get("name", "Unknown")
    
    # Handle both 'type' attribute and 'mandatory' attribute
    ftype = elem.get("type", "").lower()
    mandatory_attr = elem.get("mandatory", "").lower()
    
    if not ftype:
        if mandatory_attr == "true":
            ftype = "mandatory"
        elif mandatory_attr == "false":
            ftype = "optional"
        elif parent_name is None:
            ftype = "root"
        else:
            ftype = "optional"

    node = {
        "name": name,
        "type": ftype,
        "parent": parent_name,
        "children": [],
        "groups": [],   # list of {"type": "xor"|"or", "members": [...names]}
    }

    for child in elem:
        tag = child.tag.lower()
        if tag == "feature":
            child_node = _parse_feature_node(child, parent_name=name)
            node["children"].append(child_node)
        elif tag == "group":
            group_type = child.get("type", "or").lower()
            group_members = []
            for gchild in child:
                if gchild.tag.lower() == "feature":
                    gnode = _parse_feature_node(gchild, parent_name=name)
                    group_members.append(gnode)
            node["groups"].append({"type": group_type, "members": group_members})

    return node


def _collect_all_features(node, result=None):
    """Flatten tree into a list of feature dicts."""
    if result is None:
        result = []
    result.append(node)
    for child in node["children"]:
        _collect_all_features(child, result)
    for group in node["groups"]:
        for member in group["members"]:
            _collect_all_features(member, result)
    return result


def parse_feature_model_xml(xml_string: str) -> dict:
    """
    Parse an XML string into a feature model dict.

    Returns:
        {
            "root": <feature node dict>,
            "all_features": [list of all feature names],
            "constraints": [
                {"type": "requires"|"excludes", "from": str, "to": str},
                {"type": "english", "text": str},
                ...
            ],
            "error": None | str
        }
    """
    try:
        root_elem = ET.fromstring(xml_string)
    except ET.ParseError as e:
        return {"root": None, "all_features": [], "constraints": [], "error": str(e)}

    # Find root feature element
    feature_root_elem = root_elem.find("feature")
    if feature_root_elem is None:
        if root_elem.tag.lower() == "feature":
            feature_root_elem = root_elem
        elif root_elem.tag.lower() == "featuremodel":
            feature_root_elem = root_elem.find("feature")

    if feature_root_elem is None:
        return {
            "root": None,
            "all_features": [],
            "constraints": [],
            "error": "No <feature> root element found in XML.",
        }

    feature_root = _parse_feature_node(feature_root_elem, parent_name=None)
    all_features = _collect_all_features(feature_root)
    all_feature_names = [f["name"] for f in all_features]

    # Parse constraints
    constraints = []
    constraints_elem = root_elem.find("constraints")
    if constraints_elem is not None:
        import re
        for c in constraints_elem:
            ctype = c.get("type", "").lower()
            
            # Check for nested tags (booleanExpression or englishStatement)
            bool_expr = c.find("booleanExpression")
            eng_stmt = c.find("englishStatement")
            
            if ctype in ("requires", "excludes"):
                constraints.append(
                    {
                        "type": ctype,
                        "from": c.get("from", ""),
                        "to": c.get("to", ""),
                    }
                )
            elif ctype == "english":
                constraints.append({"type": "english", "text": c.text or ""})
            elif bool_expr is not None:
                # Basic parsing for "A -> B" or "A implies B"
                expr = bool_expr.text or ""
                if "->" in expr:
                    parts = expr.split("->")
                    constraints.append({"type": "requires", "from": parts[0].strip(), "to": parts[1].strip()})
                elif "implies" in expr.lower():
                    parts = re.split(r"\s+implies\s+", expr, flags=re.IGNORECASE)
                    constraints.append({"type": "requires", "from": parts[0].strip(), "to": parts[1].strip()})
                else:
                    constraints.append({"type": "english", "text": expr})
            elif eng_stmt is not None:
                constraints.append({"type": "english", "text": eng_stmt.text or ""})

    return {
        "root": feature_root,
        "all_features": all_feature_names,
        "all_feature_nodes": all_features,
        "constraints": constraints,
        "error": None,
    }

    return {
        "root": feature_root,
        "all_features": all_feature_names,
        "all_feature_nodes": all_features,
        "constraints": constraints,
        "error": None,
    }

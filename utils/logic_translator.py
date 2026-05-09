"""
logic_translator.py — Translate a parsed feature model into propositional logic formulas
and CNF clauses suitable for the pysat SAT solver.

Formula semantics:
  - Root is always True
  - Mandatory child:  Parent → Child  AND  Child → Parent
  - Optional child:   Parent → (Child ∨ ¬Child)   [no constraint — always satisfied]
  - XOR group (A,B):  (A ∨ B) ∧ ¬(A ∧ B)  when parent active → Parent → (A ∨ B); ¬(A ∧ B)
  - OR group  (A,B):  Parent → (A ∨ B)
  - Requires A→B:     ¬A ∨ B
  - Excludes A,B:     ¬A ∨ ¬B
"""

from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Variable ID management
# ---------------------------------------------------------------------------

class VarMap:
    """Manages feature name ↔ integer variable mapping for pysat."""

    def __init__(self):
        self._name_to_id: Dict[str, int] = {}
        self._counter = 1

    def var(self, name: str) -> int:
        if name not in self._name_to_id:
            self._name_to_id[name] = self._counter
            self._counter += 1
        return self._name_to_id[name]

    @property
    def mapping(self) -> Dict[str, int]:
        return dict(self._name_to_id)


# ---------------------------------------------------------------------------
# Clause builders (CNF)
# ---------------------------------------------------------------------------

def _implies(a: int, b: int) -> List[int]:
    """A → B  ≡  ¬A ∨ B"""
    return [-a, b]


def _implies_or(a: int, disjuncts: List[int]) -> List[int]:
    """A → (B ∨ C ∨ …)  ≡  ¬A ∨ B ∨ C ∨ …"""
    return [-a] + disjuncts


def _not_and(a: int, b: int) -> List[int]:
    """¬(A ∧ B)  ≡  ¬A ∨ ¬B"""
    return [-a, -b]


# ---------------------------------------------------------------------------
# Main translator
# ---------------------------------------------------------------------------

def translate_feature_model(model: dict) -> dict:
    """
    Translate a parsed feature model into:
      - A list of human-readable formula strings
      - A list of CNF clauses (list of list of ints) for pysat
      - A VarMap for decoding SAT results

    Returns:
        {
            "formulas": [{"label": str, "formula": str}, ...],
            "clauses":  [[int, ...], ...],
            "var_map":  VarMap,
        }
    """
    var_map = VarMap()
    clauses: List[List[int]] = []
    formulas: List[dict] = []

    root_node = model.get("root")
    if root_node is None:
        return {"formulas": [], "clauses": [], "var_map": var_map}

    # --- Root is always True ---
    root_var = var_map.var(root_node["name"])
    clauses.append([root_var])
    formulas.append(
        {"label": "Root always selected", "formula": f"{root_node['name']} = True"}
    )

    # --- Walk tree recursively ---
    _walk(root_node, var_map, clauses, formulas)

    # --- Cross-tree constraints ---
    for c in model.get("constraints", []):
        if c["type"] == "requires":
            a, b = c["from"], c["to"]
            av, bv = var_map.var(a), var_map.var(b)
            clauses.append(_implies(av, bv))
            formulas.append(
                {"label": f"Requires ({a} → {b})", "formula": f"{a} → {b}"}
            )
        elif c["type"] == "excludes":
            a, b = c["from"], c["to"]
            av, bv = var_map.var(a), var_map.var(b)
            clauses.append(_not_and(av, bv))
            formulas.append(
                {"label": f"Excludes ({a}, {b})", "formula": f"¬({a} ∧ {b})"}
            )
        elif c["type"] == "english":
            # English constraints are shown to the user for manual translation
            formulas.append(
                {
                    "label": "English constraint (manual)",
                    "formula": f'[USER INPUT REQUIRED] "{c["text"]}"',
                    "english": c["text"],
                }
            )

    return {"formulas": formulas, "clauses": clauses, "var_map": var_map}


def _walk(node: dict, var_map: VarMap, clauses: List, formulas: List):
    """Recursively translate a feature node and its children/groups."""
    parent_name = node["name"]
    pv = var_map.var(parent_name)

    # Direct children
    for child in node.get("children", []):
        cname = child["name"]
        cv = var_map.var(cname)
        ctype = child.get("type", "optional")

        if ctype == "mandatory":
            # Parent → Child  AND  Child → Parent
            clauses.append(_implies(pv, cv))
            clauses.append(_implies(cv, pv))
            formulas.append(
                {
                    "label": f"Mandatory: {parent_name} ↔ {cname}",
                    "formula": f"({parent_name} → {cname}) ∧ ({cname} → {parent_name})",
                }
            )
        else:
            # Optional: Parent → (Child ∨ ¬Child)  — trivially true, but we add
            # Child → Parent so child can only be selected if parent is
            clauses.append(_implies(cv, pv))
            formulas.append(
                {
                    "label": f"Optional: {cname} requires parent {parent_name}",
                    "formula": f"{cname} → {parent_name}",
                }
            )

        # Recurse
        _walk(child, var_map, clauses, formulas)

    # Groups (XOR / OR)
    for group in node.get("groups", []):
        gtype = group["type"]
        members = group["members"]
        member_names = [m["name"] for m in members]
        member_vars = [var_map.var(n) for n in member_names]

        if gtype == "xor":
            # Parent → (A ∨ B ∨ …)   — at least one when parent active
            clauses.append(_implies_or(pv, member_vars))
            formulas.append(
                {
                    "label": f"XOR at-least-one under {parent_name}",
                    "formula": f"{parent_name} → ({'  ∨  '.join(member_names)})",
                }
            )
            # ¬(A ∧ B) for every pair — at most one
            for i in range(len(member_vars)):
                for j in range(i + 1, len(member_vars)):
                    clauses.append(_not_and(member_vars[i], member_vars[j]))
                    formulas.append(
                        {
                            "label": f"XOR at-most-one: {member_names[i]} ⊕ {member_names[j]}",
                            "formula": f"¬({member_names[i]} ∧ {member_names[j]})",
                        }
                    )
            # Each member → parent
            for mv, mn in zip(member_vars, member_names):
                clauses.append(_implies(mv, pv))
                formulas.append(
                    {
                        "label": f"XOR member {mn} requires parent {parent_name}",
                        "formula": f"{mn} → {parent_name}",
                    }
                )

        elif gtype == "or":
            # Parent → (A ∨ B ∨ …)
            clauses.append(_implies_or(pv, member_vars))
            formulas.append(
                {
                    "label": f"OR at-least-one under {parent_name}",
                    "formula": f"{parent_name} → ({'  ∨  '.join(member_names)})",
                }
            )
            # Each member → parent
            for mv, mn in zip(member_vars, member_names):
                clauses.append(_implies(mv, pv))
                formulas.append(
                    {
                        "label": f"OR member {mn} requires parent {parent_name}",
                        "formula": f"{mn} → {parent_name}",
                    }
                )

        # Recurse into group members
        for member in members:
            _walk(member, var_map, clauses, formulas)


def add_english_constraint_as_clause(
    formula_str: str, var_map: VarMap, clauses: List[List[int]], formulas: List[dict]
) -> Tuple[bool, str]:
    """
    Parse a user-confirmed formula like 'A → B' or '¬(A ∧ B)' and add clauses.
    Supported simple forms:
      A → B         (requires)
      ¬(A ∧ B)      (excludes)
    Returns (success, message).
    """
    formula_str = formula_str.strip()
    # Try A → B
    if "→" in formula_str:
        parts = formula_str.split("→")
        if len(parts) == 2:
            a = parts[0].strip()
            b = parts[1].strip()
            av = var_map.var(a)
            bv = var_map.var(b)
            clauses.append(_implies(av, bv))
            formulas.append(
                {"label": f"English (user-confirmed): {a} → {b}", "formula": f"{a} → {b}"}
            )
            return True, f"Added: {a} → {b}"
    # Try ¬(A ∧ B)
    if "¬(" in formula_str and "∧" in formula_str:
        inner = formula_str.replace("¬(", "").replace(")", "")
        parts = inner.split("∧")
        if len(parts) == 2:
            a = parts[0].strip()
            b = parts[1].strip()
            av = var_map.var(a)
            bv = var_map.var(b)
            clauses.append(_not_and(av, bv))
            formulas.append(
                {
                    "label": f"English (user-confirmed): ¬({a} ∧ {b})",
                    "formula": f"¬({a} ∧ {b})",
                }
            )
            return True, f"Added: ¬({a} ∧ {b})"
    return False, "Could not parse formula. Use 'A → B' or '¬(A ∧ B)' format."

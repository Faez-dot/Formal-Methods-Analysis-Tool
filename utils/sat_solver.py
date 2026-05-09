"""
sat_solver.py — SAT-based feature model analysis using python-sat (pysat).

Provides:
  - compute_mwps(): find ALL minimal valid configurations
  - verify_config(): check if a user selection satisfies all constraints
"""

from typing import Dict, List, Optional, Tuple
from pysat.solvers import Glucose3
from pysat.formula import CNF


# ---------------------------------------------------------------------------
# MWP Computation
# ---------------------------------------------------------------------------

def compute_mwps(
    clauses: List[List[int]],
    var_map: Dict[str, int],   # name → int
    all_features: List[str],
    root_name: str,
) -> List[List[str]]:
    """
    Find ALL Minimal Working Products (MWPs).

    A valid configuration satisfies all CNF clauses.
    Minimal = no proper subset of selected optional features is also valid.

    Algorithm:
      1. Enumerate all satisfying assignments using pysat + blocking clauses.
      2. For each solution, check whether any strict subset (varying optional
         features only) is also satisfying; if not, it's minimal.

    Returns list of MWPs, each MWP is a sorted list of selected feature names.
    """
    rev_map = {v: k for k, v in var_map.items()}
    all_vars = set(var_map.values())

    cnf = CNF(from_clauses=clauses)
    solver = Glucose3(bootstrap_with=cnf.clauses)

    solutions = []
    MAX_SOLUTIONS = 200  # guard against combinatorial explosion

    while solver.solve() and len(solutions) < MAX_SOLUTIONS:
        model = solver.get_model()
        # Collect true features
        true_features = {
            rev_map[v]
            for v in model
            if v > 0 and v in rev_map
        }
        solutions.append(frozenset(true_features))
        # Block this solution
        blocking = [-v for v in model if v in all_vars]
        solver.add_clause(blocking)

    solver.delete()

    if not solutions:
        return []

    # Filter to minimal solutions
    mwps = []
    for sol in solutions:
        is_minimal = True
        for other in solutions:
            if other < sol:  # other is a proper subset
                is_minimal = False
                break
        if is_minimal:
            mwps.append(sorted(sol))

    # Deduplicate
    seen = set()
    unique_mwps = []
    for mwp in mwps:
        key = tuple(mwp)
        if key not in seen:
            seen.add(key)
            unique_mwps.append(mwp)

    return unique_mwps


# ---------------------------------------------------------------------------
# Configuration Verification
# ---------------------------------------------------------------------------

def verify_config(
    selected_features: List[str],
    clauses: List[List[int]],
    var_map: Dict[str, int],
    all_features: List[str],
    constraints_raw: List[dict],   # original parsed constraint dicts
) -> dict:
    """
    Verify whether a user-selected set of features satisfies all constraints.

    Returns:
        {
            "valid": bool,
            "violations": [
                {"constraint": str, "explanation": str},
                ...
            ]
        }
    """
    selected_set = set(selected_features)
    violations = []

    # Build assumption list: selected → positive literal, not selected → negative
    assumptions = []
    for name, vid in var_map.items():
        if name in selected_set:
            assumptions.append(vid)
        else:
            assumptions.append(-vid)

    # Global SAT check
    cnf = CNF(from_clauses=clauses)
    solver = Glucose3(bootstrap_with=cnf.clauses)
    is_sat = solver.solve(assumptions=assumptions)
    solver.delete()

    if is_sat:
        return {"valid": True, "violations": []}

    # --- Identify which constraints are violated ---
    for c in constraints_raw:
        ctype = c.get("type", "")

        if ctype == "requires":
            a, b = c["from"], c["to"]
            if a in selected_set and b not in selected_set:
                violations.append(
                    {
                        "constraint": f"{a} → {b}",
                        "explanation": (
                            f"'{a}' is selected but '{b}' is not — "
                            f"violated requires constraint: {a} → {b}"
                        ),
                    }
                )

        elif ctype == "excludes":
            a, b = c["from"], c["to"]
            if a in selected_set and b in selected_set:
                violations.append(
                    {
                        "constraint": f"¬({a} ∧ {b})",
                        "explanation": (
                            f"Both '{a}' and '{b}' are selected — "
                            f"violated excludes constraint: ¬({a} ∧ {b})"
                        ),
                    }
                )

    # Also check structural violations
    violations += _check_structural_violations(selected_set, var_map, clauses)

    # If no specific violation identified but SAT says unsat, add generic message
    if not violations:
        violations.append(
            {
                "constraint": "Unknown",
                "explanation": (
                    "The selected configuration is unsatisfiable. "
                    "Check mandatory features and group constraints."
                ),
            }
        )

    return {"valid": False, "violations": violations}


def _check_structural_violations(
    selected_set: set,
    var_map: Dict[str, int],
    clauses: List[List[int]],
) -> List[dict]:
    """Check each clause individually to find structural violations."""
    rev_map = {v: k for k, v in var_map.items()}
    violations = []

    for clause in clauses:
        # Evaluate clause under selected_set
        satisfied = False
        for lit in clause:
            name = rev_map.get(abs(lit))
            if name is None:
                continue
            if lit > 0 and name in selected_set:
                satisfied = True
                break
            if lit < 0 and name not in selected_set:
                satisfied = True
                break
        if not satisfied:
            # Translate clause back to readable form
            parts = []
            for lit in clause:
                name = rev_map.get(abs(lit), f"var_{abs(lit)}")
                parts.append(name if lit > 0 else f"¬{name}")
            readable = " ∨ ".join(parts)
            violations.append(
                {
                    "constraint": readable,
                    "explanation": f"Clause ({readable}) is not satisfied by the current selection.",
                }
            )

    return violations

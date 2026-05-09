"""
consistency_checker.py — Compare inferred code-level feature dependencies
against the feature model constraints to detect inconsistencies.

Inconsistency types:
  MISSING   — Code implies A depends on B, but no 'requires' constraint exists
  INCORRECT — Code implies A depends on B, but model says A EXCLUDES B
  HIDDEN    — Model says A requires B, but no code dependency found
"""

from typing import Dict, List, Tuple


def infer_feature_dependencies(
    feature_file_mapping: Dict[str, List[str]],   # feature → [files]
    file_dependencies: List[dict],                  # [{from, to, raw_import, ...}]
) -> List[dict]:
    """
    Derive feature-level dependencies from code.

    Logic: If Feature A maps to file X, and file X imports file Y,
           and file Y is mapped to Feature B → Feature A → Feature B.

    Returns list of:
        {
            "feature_from": str,
            "feature_to": str,
            "via_file_from": str,
            "via_file_to": str,
            "raw_import": str,
        }
    """
    # Reverse mapping: file → features
    file_to_features: Dict[str, List[str]] = {}
    for feature, files in feature_file_mapping.items():
        for f in files:
            file_to_features.setdefault(f, []).append(feature)

    inferred = []
    seen = set()

    for dep in file_dependencies:
        if dep.get("external"):
            continue
        file_from = dep["from"]
        file_to = dep["to"]
        raw_import = dep.get("raw_import", "")

        features_from = file_to_features.get(file_from, [])
        features_to = file_to_features.get(file_to, [])

        for fa in features_from:
            for fb in features_to:
                if fa == fb:
                    continue
                key = (fa, fb)
                if key not in seen:
                    seen.add(key)
                    inferred.append(
                        {
                            "feature_from": fa,
                            "feature_to": fb,
                            "via_file_from": file_from,
                            "via_file_to": file_to,
                            "raw_import": raw_import,
                        }
                    )

    return inferred


def check_consistency(
    inferred_feature_deps: List[dict],
    model_constraints: List[dict],   # parsed XML constraints
) -> List[dict]:
    """
    Compare inferred feature deps against model constraints.

    Returns list of inconsistency dicts:
        {
            "type": "MISSING" | "INCORRECT" | "HIDDEN",
            "feature_a": str,
            "feature_b": str,
            "evidence": str,
            "explanation": str,
            "fix": str,
        }
    """
    inconsistencies = []

    # Index model constraints for quick lookup
    requires_set = set()    # (from, to)
    excludes_set = set()    # (from, to) OR (to, from)

    for c in model_constraints:
        if c["type"] == "requires":
            requires_set.add((c["from"], c["to"]))
        elif c["type"] == "excludes":
            excludes_set.add((c["from"], c["to"]))
            excludes_set.add((c["to"], c["from"]))

    # Check each inferred dep
    for dep in inferred_feature_deps:
        fa = dep["feature_from"]
        fb = dep["feature_to"]
        evidence = (
            f"File '{dep['via_file_from']}' imports '{dep['raw_import']}' "
            f"(resolved to '{dep['via_file_to']}')"
        )

        if (fa, fb) in excludes_set:
            # Incorrect: model says EXCLUDES but code implies dependency
            inconsistencies.append(
                {
                    "type": "INCORRECT",
                    "feature_a": fa,
                    "feature_b": fb,
                    "evidence": evidence,
                    "explanation": (
                        f"The feature model says '{fa}' EXCLUDES '{fb}', but the code "
                        f"shows '{fa}' depends on '{fb}'. This is a contradiction."
                    ),
                    "fix": (
                        f"Either change the model constraint from 'excludes' to 'requires' "
                        f"for ({fa}, {fb}), or remove the code dependency."
                    ),
                }
            )
        elif (fa, fb) not in requires_set:
            # Missing: no requires constraint for this inferred dep
            inconsistencies.append(
                {
                    "type": "MISSING",
                    "feature_a": fa,
                    "feature_b": fb,
                    "evidence": evidence,
                    "explanation": (
                        f"The code implies '{fa}' depends on '{fb}', but the feature model "
                        f"has no 'requires' constraint from '{fa}' to '{fb}'."
                    ),
                    "fix": (
                        f"Add a 'requires' constraint: {fa} → {fb}  "
                        f"to the feature model."
                    ),
                }
            )

    # Check HIDDEN: model requires A→B but no code dependency found
    inferred_pairs = {(d["feature_from"], d["feature_to"]) for d in inferred_feature_deps}
    for c in model_constraints:
        if c["type"] == "requires":
            fa, fb = c["from"], c["to"]
            if (fa, fb) not in inferred_pairs:
                inconsistencies.append(
                    {
                        "type": "HIDDEN",
                        "feature_a": fa,
                        "feature_b": fb,
                        "evidence": f"Model constraint: {fa} → {fb}",
                        "explanation": (
                            f"The feature model specifies that '{fa}' requires '{fb}', "
                            f"but no corresponding code dependency was found. "
                            f"This constraint may be unverified or dead code."
                        ),
                        "fix": (
                            f"Verify that the code for '{fa}' actually uses '{fb}', "
                            f"or remove the constraint if it's outdated."
                        ),
                    }
                )

    return inconsistencies


def compute_impact_analysis(
    selected_features: List[str],
    feature_file_mapping: Dict[str, List[str]],
    file_dep_closure: Dict[str, List[str]],   # from build_transitive_closure()
) -> dict:
    """
    Given selected features, determine which files are directly and
    indirectly affected.

    Returns:
        {
            "direct_files": [str, ...],
            "indirect_files": [str, ...],
        }
    """
    direct_files = set()
    for feat in selected_features:
        for f in feature_file_mapping.get(feat, []):
            direct_files.add(f)

    indirect_files = set()
    for f in direct_files:
        for dep in file_dep_closure.get(f, []):
            if dep not in direct_files:
                indirect_files.add(dep)

    return {
        "direct_files": sorted(direct_files),
        "indirect_files": sorted(indirect_files),
    }

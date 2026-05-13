"""
dependency_extractor.py — Scan uploaded source files for import/include statements
and build a file-level dependency graph.

Supports:
  Python:  import X, from X import Y
  JS/TS:   import ... from '...', require('...')
  Java:    import com.example.X;
  C/C++:   #include <X>, #include "X"
"""

import re
import os
from typing import Dict, List, Tuple, Optional


# ---------------------------------------------------------------------------
# Regex patterns per language
# ---------------------------------------------------------------------------

PATTERNS = {
    "python": [
        re.compile(r"^\s*import\s+([\w\.]+)", re.MULTILINE),
        re.compile(r"^\s*from\s+([\w\.]+)\s+import", re.MULTILINE),
    ],
    "javascript": [
        re.compile(r"""import\s+.*?from\s+['"]([^'"]+)['"]""", re.MULTILINE),
        re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""", re.MULTILINE),
    ],
    "java": [
        re.compile(r"^\s*import\s+([\w\.]+);", re.MULTILINE),
    ],
    "c_cpp": [
        re.compile(r"""#include\s+[<"]([^>"]+)[>"]""", re.MULTILINE),
    ],
    "xml": [
        re.compile(r"""module\s*=\s*['"]([^'"]+)['"]""", re.MULTILINE),
    ],
}

EXTENSION_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "javascript",
    ".jsx": "javascript",
    ".tsx": "javascript",
    ".java": "java",
    ".c": "c_cpp",
    ".cpp": "c_cpp",
    ".cc": "c_cpp",
    ".h": "c_cpp",
    ".hpp": "c_cpp",
    ".xml": "xml",
}


def detect_language(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return EXTENSION_MAP.get(ext, "unknown")


def extract_raw_imports(filename: str, content: str) -> List[str]:
    """Extract all import targets from a file's content."""
    lang = detect_language(filename)
    raw_imports = []
    patterns = PATTERNS.get(lang, [])
    for pattern in patterns:
        for match in pattern.finditer(content):
            raw_imports.append(match.group(1).strip())
    return raw_imports


def resolve_import_to_file(
    raw_import: str,
    all_filenames: List[str],
    current_file: str,
) -> Optional[str]:
    """
    Try to resolve a raw import string to an actual uploaded filename.
    Heuristic: match by base name or module name component.
    """
    import_base = raw_import.split(".")[-1]  # last component of dotted path
    import_base = import_base.split("/")[-1]  # last path segment

    for fname in all_filenames:
        base = os.path.splitext(os.path.basename(fname))[0]
        if base.lower() == import_base.lower() and fname != current_file:
            return fname

    return None


def extract_dependencies(
    files: Dict[str, str],  # filename → content
) -> List[dict]:
    """
    Extract file-level dependencies from a set of files.

    Returns list of:
        {
            "from": filename,
            "to": filename,
            "raw_import": str,
            "language": str,
        }
    """
    all_filenames = list(files.keys())
    dependencies = []

    for fname, content in files.items():
        lang = detect_language(fname)
        raw_imports = extract_raw_imports(fname, content)

        for raw in raw_imports:
            resolved = resolve_import_to_file(raw, all_filenames, fname)
            if resolved:
                dependencies.append(
                    {
                        "from": fname,
                        "to": resolved,
                        "raw_import": raw,
                        "language": lang,
                    }
                )
            else:
                # Still record external/unresolved imports for display
                dependencies.append(
                    {
                        "from": fname,
                        "to": f"[external] {raw}",
                        "raw_import": raw,
                        "language": lang,
                        "external": True,
                    }
                )

    return dependencies


def build_transitive_closure(
    direct_deps: List[dict],
) -> Dict[str, List[str]]:
    """
    Build a transitive dependency map: file → all files it (directly or
    indirectly) depends on.
    """
    # Build adjacency
    graph: Dict[str, List[str]] = {}
    for dep in direct_deps:
        if dep.get("external"):
            continue
        graph.setdefault(dep["from"], [])
        graph[dep["from"]].append(dep["to"])

    def _dfs(node, visited):
        for neighbour in graph.get(node, []):
            if neighbour not in visited:
                visited.add(neighbour)
                _dfs(neighbour, visited)

    closure = {}
    for node in graph:
        visited = set()
        _dfs(node, visited)
        closure[node] = sorted(visited)

    return closure



"""Dependency analysis for parsed code.

Builds a call graph between components, topologically sorts them for
teaching order, and detects programming concepts present in each piece.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .languages._base import LanguageProfile, ParseResult


@dataclass
class Component:
    """A named code component (function or class) with its dependency info."""

    name: str
    kind: str  # "function" or "class"
    body: str
    calls: list[str] = field(default_factory=list)
    called_by: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    source_line: int = 0


@dataclass
class ProgramAnalysis:
    """Complete dependency and concept analysis of a parsed program."""

    components: list[Component]
    dependency_order: list[str]
    concepts: list[str]
    call_graph: dict[str, list[str]]
    reverse_graph: dict[str, list[str]]

    def get_component(self, name: str) -> Optional[Component]:
        for c in self.components:
            if c.name == name:
                return c
        return None

    @property
    def dependency_edge_count(self) -> int:
        return sum(len(deps) for deps in self.call_graph.values())

    @property
    def has_dependencies(self) -> bool:
        return self.dependency_edge_count > 0


def analyze(parsed: ParseResult, profile: LanguageProfile) -> ProgramAnalysis:
    """Analyze parsed code to build a dependency graph and detect concepts."""
    defined_names: set[str] = set()
    components: list[Component] = []
    ordered_items = _ordered_components(parsed)

    for _, _, _, item in ordered_items:
        defined_names.add(item["name"])

    for source_line, _, kind, item in ordered_items:
        calls = _find_calls(item["body"], item["name"], defined_names)
        concepts = _detect_concepts(item["body"], item["name"], profile)
        components.append(Component(
            name=item["name"],
            kind=kind,
            body=item["body"],
            calls=calls,
            concepts=concepts,
            source_line=source_line,
        ))

    # Build forward and reverse call graphs
    call_graph: dict[str, list[str]] = {c.name: c.calls for c in components}
    reverse_graph: dict[str, list[str]] = {c.name: [] for c in components}
    for name, deps in call_graph.items():
        for dep in deps:
            if dep in reverse_graph:
                reverse_graph[dep].append(name)

    # Populate called_by on each component
    for c in components:
        c.called_by = reverse_graph.get(c.name, [])

    order = _topological_sort(components, call_graph)

    # Program-level concepts (union of all component concepts + main code)
    all_concepts: set[str] = set()
    for c in components:
        all_concepts.update(c.concepts)
    if parsed.get("main_code"):
        all_concepts.update(_detect_concepts(parsed["main_code"], "", profile))

    return ProgramAnalysis(
        components=components,
        dependency_order=order,
        concepts=sorted(all_concepts),
        call_graph=call_graph,
        reverse_graph=reverse_graph,
    )


def _find_calls(
    body: str,
    own_name: str,
    defined: set[str],
) -> list[str]:
    """Find references to other defined components in a code body."""
    search_text = _analysis_text(body, skip_signature=True)

    refs: set[str] = set()
    for name in defined:
        if name == own_name:
            continue
        if re.search(rf"\b{re.escape(name)}\s*\(", search_text):
            refs.add(name)

    return sorted(refs)


def _detect_concepts(
    body: str,
    name: str,
    profile: LanguageProfile,
) -> list[str]:
    """Detect programming concepts present in a code body."""
    concepts: list[str] = []

    # Recursion
    if name:
        search_text = _analysis_text(body, skip_signature=True)
        if re.search(rf"\b{re.escape(name)}\s*\(", search_text):
            concepts.append("recursion")

    sanitized_body = _analysis_text(body)

    # Iteration
    kw = "|".join(re.escape(k) for k in profile.iteration_keywords)
    if re.search(rf"\b({kw})\b", sanitized_body):
        concepts.append("iteration")

    # Control flow
    kw = "|".join(re.escape(k) for k in profile.branch_keywords)
    if re.search(rf"\b({kw})\b", sanitized_body):
        concepts.append("control flow")

    # Error handling
    kw = "|".join(re.escape(k) for k in profile.error_keywords)
    if re.search(rf"\b({kw})\b", sanitized_body):
        concepts.append("error handling")

    # State management
    if profile.state_tokens and any(tok in sanitized_body for tok in profile.state_tokens):
        concepts.append("state management")

    return concepts


_NON_CODE_RE = re.compile(
    r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:\\.|[^"\\])*"|'
    r"'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|//[^\n]*|/\*[\s\S]*?\*/|"
    r"#!?\[[^\n]*\]|#(?!\[|!\[)[^\n]*)"
)


def _analysis_text(body: str, *, skip_signature: bool = False) -> str:
    lines = body.split("\n")
    text = "\n".join(lines[1:]) if skip_signature and len(lines) > 1 else body
    return _NON_CODE_RE.sub(" ", text)


def _ordered_components(
    parsed: ParseResult,
) -> list[tuple[int, int, str, dict[str, Any]]]:
    ordered: list[tuple[int, int, str, dict[str, Any]]] = []
    fallback_line = 10**9

    for index, func in enumerate(parsed.get("functions", [])):
        ordered.append(
            (
                func.get("source_line", fallback_line + index),
                index,
                "function",
                func,
            )
        )

    function_count = len(parsed.get("functions", []))
    for index, cls in enumerate(parsed.get("classes", [])):
        ordered.append(
            (
                cls.get("source_line", fallback_line + function_count + index),
                function_count + index,
                "class",
                cls,
            )
        )

    ordered.sort(key=lambda item: (item[0], item[1]))
    return ordered


def _topological_sort(
    components: list[Component],
    call_graph: dict[str, list[str]],
) -> list[str]:
    """Topological sort: dependencies first so each step builds on the last.

    Falls back to original order for components involved in cycles.
    """
    names = [c.name for c in components]
    name_set = set(names)
    name_index = {n: i for i, n in enumerate(names)}

    # Filter graph to only include defined names
    graph = {
        n: [dep for dep in deps if dep in name_set]
        for n, deps in call_graph.items()
    }

    # Build "must come before" adjacency: if A calls B, B -> A
    adj: dict[str, list[str]] = {n: [] for n in names}
    in_degree: dict[str, int] = {n: 0 for n in names}
    for n, deps in graph.items():
        for dep in deps:
            adj[dep].append(n)
            in_degree[n] += 1

    # Kahn's algorithm with stable ordering
    queue = sorted(
        [n for n in names if in_degree[n] == 0],
        key=lambda n: name_index[n],
    )
    result: list[str] = []

    while queue:
        node = queue.pop(0)
        result.append(node)
        for neighbor in sorted(adj[node], key=lambda n: name_index[n]):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
        queue.sort(key=lambda n: name_index[n])

    # Cycle fallback: append remaining in original order
    for n in names:
        if n not in result:
            result.append(n)

    return result

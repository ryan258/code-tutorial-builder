"""Dependency analysis for parsed code.

Builds a call graph between components, topologically sorts them for
teaching order, and detects programming concepts present in each piece.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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


def analyze(parsed: ParseResult, profile: LanguageProfile) -> ProgramAnalysis:
    """Analyze parsed code to build a dependency graph and detect concepts."""
    defined_names: set[str] = set()
    components: list[Component] = []
    component_map: dict[str, dict[str, Any]] = {}

    for func in parsed.get("functions", []):
        defined_names.add(func["name"])
        component_map[func["name"]] = func
    for cls in parsed.get("classes", []):
        defined_names.add(cls["name"])
        component_map[cls["name"]] = cls

    for func in parsed.get("functions", []):
        calls = _find_calls(func["body"], func["name"], defined_names, profile)
        concepts = _detect_concepts(func["body"], func["name"], profile)
        components.append(Component(
            name=func["name"],
            kind="function",
            body=func["body"],
            calls=calls,
            concepts=concepts,
        ))

    for cls in parsed.get("classes", []):
        calls = _find_calls(cls["body"], cls["name"], defined_names, profile)
        concepts = _detect_concepts(cls["body"], cls["name"], profile)
        components.append(Component(
            name=cls["name"],
            kind="class",
            body=cls["body"],
            calls=calls,
            concepts=concepts,
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
    profile: LanguageProfile,
) -> list[str]:
    """Find references to other defined components in a code body."""
    lines = body.split("\n")
    search_text = "\n".join(lines[1:]) if len(lines) > 1 else ""

    refs: set[str] = set()
    for name in defined:
        if name == own_name:
            continue
        if re.search(rf"\b{re.escape(name)}\b", search_text):
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
        lines = body.split("\n")
        search_text = "\n".join(lines[1:]) if len(lines) > 1 else ""
        if re.search(rf"\b{re.escape(name)}\s*\(", search_text):
            concepts.append("recursion")

    # Iteration
    kw = "|".join(re.escape(k) for k in profile.iteration_keywords)
    if re.search(rf"\b({kw})\b", body):
        concepts.append("iteration")

    # Control flow
    kw = "|".join(re.escape(k) for k in profile.branch_keywords)
    if re.search(rf"\b({kw})\b", body):
        concepts.append("control flow")

    # Error handling
    kw = "|".join(re.escape(k) for k in profile.error_keywords)
    if re.search(rf"\b({kw})\b", body):
        concepts.append("error handling")

    # State management
    if profile.state_tokens and any(tok in body for tok in profile.state_tokens):
        concepts.append("state management")

    return concepts


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

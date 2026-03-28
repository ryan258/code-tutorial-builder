"""Project scanner — walks a codebase and identifies learning opportunities.

Scans a project directory, parses supported files, runs dependency and concept
analysis, and scores each file for "teaching potential."  Returns a ranked list
of LearningOpportunity objects that a teacher can browse, discuss, and select.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .analysis import ProgramAnalysis, analyze
from .languages._base import LanguageProfile, ParseResult
from .languages._registry import (
    LANGUAGES,
    _EXTENSION_MAP,
    detect_language,
    get_parser,
    get_profile,
)

logger = logging.getLogger(__name__)

# Directories that should never be scanned
_SKIP_DIRS: set[str] = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "vendor",
    "target",
    "build",
    "dist",
    ".next",
    ".nuxt",
    "out",
    ".gitnexus",
    ".egg-info",
}

# ──────────────────────────────────────────────────────────────────────
# Data types
# ──────────────────────────────────────────────────────────────────────


@dataclass
class FileAnalysis:
    """Analysis results for a single source file."""

    path: Path
    language: str
    parsed: ParseResult
    graph: ProgramAnalysis
    profile: LanguageProfile


@dataclass
class LearningOpportunity:
    """A ranked opportunity for building a tutorial lesson."""

    title: str
    file_path: str
    components: list[str]
    concepts: list[str]
    difficulty: str
    score: float
    rationale: str
    component_count: int = 0
    dependency_depth: int = 0
    gitnexus_context: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "title": self.title,
            "file_path": self.file_path,
            "components": self.components,
            "concepts": self.concepts,
            "difficulty": self.difficulty,
            "score": round(self.score, 2),
            "rationale": self.rationale,
            "component_count": self.component_count,
            "dependency_depth": self.dependency_depth,
        }
        if self.gitnexus_context:
            d["gitnexus_context"] = self.gitnexus_context
        return d


@dataclass
class ScanResult:
    """Complete results from scanning a project directory."""

    root: str
    files_scanned: int
    files_skipped: int
    opportunities: list[LearningOpportunity]
    gitnexus_available: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "files_scanned": self.files_scanned,
            "files_skipped": self.files_skipped,
            "gitnexus_available": self.gitnexus_available,
            "opportunities": [o.to_dict() for o in self.opportunities],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ──────────────────────────────────────────────────────────────────────
# Scanning
# ──────────────────────────────────────────────────────────────────────


def scan_project(
    root: str | Path,
    *,
    max_opportunities: int = 10,
    max_file_lines: int = 500,
) -> ScanResult:
    """Scan a project directory and return ranked learning opportunities.

    Parameters
    ----------
    root:
        Path to the project directory.
    max_opportunities:
        Maximum number of opportunities to return (1-10).
    max_file_lines:
        Skip files longer than this — they're usually too complex for a
        single lesson.
    """
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")

    max_opportunities = max(1, min(max_opportunities, 10))
    supported_extensions = set(_EXTENSION_MAP.keys())

    analyses: list[FileAnalysis] = []
    skipped = 0

    for source_file in _walk_source_files(root, supported_extensions):
        language = detect_language(str(source_file))
        if language is None:
            skipped += 1
            continue

        try:
            code = source_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            skipped += 1
            continue

        if len(code.split("\n")) > max_file_lines:
            skipped += 1
            continue

        try:
            parser = get_parser(language)
            parsed = parser.parse(code)
            profile = get_profile(language)
            graph = analyze(parsed, profile)
        except Exception as exc:
            logger.debug("Skipping %s: %s", source_file, exc)
            skipped += 1
            continue

        analyses.append(FileAnalysis(
            path=source_file,
            language=language,
            parsed=parsed,
            graph=graph,
            profile=profile,
        ))

    # Score and rank
    opportunities = [_score_file(a, root) for a in analyses]
    opportunities.sort(key=lambda o: o.score, reverse=True)
    opportunities = opportunities[:max_opportunities]

    # Enrich with GitNexus if available
    gitnexus_available = _gitnexus_index_exists(root)
    if gitnexus_available:
        _enrich_with_gitnexus(root, opportunities)

    return ScanResult(
        root=str(root),
        files_scanned=len(analyses),
        files_skipped=skipped,
        opportunities=opportunities,
        gitnexus_available=gitnexus_available,
    )


# ──────────────────────────────────────────────────────────────────────
# File discovery
# ──────────────────────────────────────────────────────────────────────


def _walk_source_files(
    root: Path,
    extensions: set[str],
    _visited: set[int] | None = None,
) -> list[Path]:
    """Walk root recursively, yielding source files with supported extensions.

    Tracks visited directories by device+inode to avoid symlink loops and
    skips symlinked directories entirely to stay within the project root.
    """
    if _visited is None:
        _visited = set()

    try:
        stat = root.stat()
    except OSError:
        return []
    ident = (stat.st_dev, stat.st_ino)
    if ident in _visited:
        return []
    _visited.add(ident)

    results: list[Path] = []
    for item in sorted(root.iterdir()):
        if item.is_dir():
            if item.is_symlink():
                continue
            if item.name in _SKIP_DIRS or item.name.endswith(".egg-info"):
                continue
            results.extend(_walk_source_files(item, extensions, _visited))
        elif item.is_file() and item.suffix.lower() in extensions:
            results.append(item)
    return results


# ──────────────────────────────────────────────────────────────────────
# Scoring
# ──────────────────────────────────────────────────────────────────────

# Weights for each scoring dimension (must sum to ~1.0)
_W_CONCEPTS = 0.30
_W_DEPENDENCIES = 0.25
_W_SIZE = 0.20
_W_SELF_CONTAINED = 0.15
_W_PROGRESSIVE = 0.10


def _score_file(analysis: FileAnalysis, root: Path) -> LearningOpportunity:
    """Score a single file for teaching potential and build an opportunity."""
    graph = analysis.graph
    components = graph.components
    concepts = graph.concepts

    # --- Concept diversity (0-1): more distinct concepts = better ---
    # Diminishing returns past 4 concepts
    concept_score = min(len(concepts) / 4.0, 1.0)

    # --- Dependency richness (0-1): interesting call graph ---
    dep_depth = _max_dependency_depth(graph)
    dep_score = min(dep_depth / 3.0, 1.0) if components else 0.0

    # --- Size sweet spot (0-1): 2-8 components is ideal ---
    n = len(components)
    if n == 0:
        size_score = 0.1  # main-code only files still have some value
    elif 2 <= n <= 8:
        size_score = 1.0
    elif n == 1:
        size_score = 0.5
    else:
        # Gentle penalty past 8
        size_score = max(0.2, 1.0 - (n - 8) * 0.1)

    # --- Self-containedness (0-1): fewer imports = more self-contained ---
    import_count = len(analysis.parsed.get("imports", []))
    self_contained_score = max(0.0, 1.0 - import_count * 0.1)

    # --- Progressive complexity (0-1): components build on each other ---
    if n >= 2 and graph.has_dependencies:
        # Ratio of components that participate in at least one edge
        connected = sum(
            1 for c in components if c.calls or c.called_by
        )
        progressive_score = connected / n
    else:
        progressive_score = 0.0

    score = (
        _W_CONCEPTS * concept_score
        + _W_DEPENDENCIES * dep_score
        + _W_SIZE * size_score
        + _W_SELF_CONTAINED * self_contained_score
        + _W_PROGRESSIVE * progressive_score
    )

    # Build the opportunity
    rel_path = str(analysis.path.relative_to(root))
    comp_names = [c.name for c in components]
    difficulty = _estimate_difficulty(concepts, n, dep_depth)
    title = _generate_title(analysis, concepts)
    rationale = _generate_rationale(concepts, n, dep_depth, graph.has_dependencies)

    return LearningOpportunity(
        title=title,
        file_path=rel_path,
        components=comp_names,
        concepts=concepts,
        difficulty=difficulty,
        score=score,
        rationale=rationale,
        component_count=n,
        dependency_depth=dep_depth,
    )


def _max_dependency_depth(graph: ProgramAnalysis) -> int:
    """Find the longest dependency chain in the call graph."""
    if not graph.has_dependencies:
        return 0

    memo: dict[str, int] = {}

    def _depth(name: str, visiting: set[str]) -> int:
        if name in memo:
            return memo[name]
        if name in visiting:
            return 0  # cycle
        visiting.add(name)
        deps = graph.call_graph.get(name, [])
        d = 1 + max((_depth(dep, visiting) for dep in deps), default=0) if deps else 0
        visiting.discard(name)
        memo[name] = d
        return d

    return max(_depth(c.name, set()) for c in graph.components)


def _estimate_difficulty(
    concepts: list[str],
    component_count: int,
    dep_depth: int,
) -> str:
    """Estimate lesson difficulty from analysis metrics."""
    advanced_concepts = {"recursion", "error handling", "state management"}
    advanced_count = sum(1 for c in concepts if c in advanced_concepts)

    complexity = component_count + dep_depth * 2 + advanced_count * 2

    if complexity <= 3:
        return "beginner"
    elif complexity <= 8:
        return "intermediate"
    else:
        return "advanced"


def _generate_title(analysis: FileAnalysis, concepts: list[str]) -> str:
    """Generate a descriptive title for the learning opportunity."""
    components = analysis.graph.components
    profile = analysis.profile

    if not components:
        stem = analysis.path.stem.replace("_", " ").replace("-", " ").title()
        return f"{stem} ({profile.display_name})"

    # Name the primary component(s)
    primary = components[0].name
    if len(components) == 1:
        focus = f"`{primary}`"
    elif len(components) <= 3:
        focus = ", ".join(f"`{c.name}`" for c in components)
    else:
        focus = f"`{primary}` and {len(components) - 1} more"

    # Add concept flavor
    if concepts:
        concept_text = " & ".join(concepts[:2])
        return f"{focus} — {concept_text}"

    return f"{focus} ({profile.display_name})"


def _generate_rationale(
    concepts: list[str],
    component_count: int,
    dep_depth: int,
    has_deps: bool,
) -> str:
    """Generate a short explanation of why this file is a good learning opportunity."""
    reasons: list[str] = []

    if len(concepts) >= 3:
        reasons.append(f"rich concept diversity ({', '.join(concepts)})")
    elif concepts:
        reasons.append(f"demonstrates {', '.join(concepts)}")

    if has_deps and dep_depth >= 2:
        reasons.append(f"dependency chain {dep_depth} levels deep shows composition")
    elif has_deps:
        reasons.append("components build on each other")

    if 2 <= component_count <= 6:
        reasons.append(f"{component_count} components — right size for a lesson")
    elif component_count == 1:
        reasons.append("focused single-component lesson")

    if not reasons:
        reasons.append("parseable source file with teachable content")

    return reasons[0][0].upper() + reasons[0][1:] + (
        "; " + "; ".join(reasons[1:]) if len(reasons) > 1 else ""
    ) + "."


# ──────────────────────────────────────────────────────────────────────
# GitNexus enrichment
# ──────────────────────────────────────────────────────────────────────


def _gitnexus_index_exists(root: Path) -> bool:
    """Check if a GitNexus index exists for this project."""
    meta = root / ".gitnexus" / "meta.json"
    return meta.is_file()


def read_gitnexus_meta(root: Path) -> Optional[dict[str, Any]]:
    """Read the GitNexus meta.json if available."""
    meta_path = root / ".gitnexus" / "meta.json"
    if not meta_path.is_file():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _enrich_with_gitnexus(
    root: Path,
    opportunities: list[LearningOpportunity],
) -> None:
    """Add GitNexus metadata to opportunities when the index is available.

    This reads the meta.json for project-level stats.  The deeper enrichment
    (execution flows, clusters, symbol context) happens at the Claude Code
    skill layer where MCP tools are available.
    """
    meta = read_gitnexus_meta(root)
    if meta is None:
        return

    stats = meta.get("stats", {})
    for opp in opportunities:
        opp.gitnexus_context = {
            "index_available": True,
            "project_stats": {
                "files": stats.get("files", 0),
                "symbols": stats.get("nodes", 0),
                "relationships": stats.get("edges", 0),
                "execution_flows": stats.get("processes", 0),
                "functional_areas": stats.get("communities", 0),
            },
            "note": (
                "Use GitNexus MCP tools (gitnexus_query, gitnexus_context) "
                "for deeper analysis of this opportunity's components."
            ),
        }

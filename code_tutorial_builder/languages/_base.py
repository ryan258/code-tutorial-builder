from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, TypedDict


class _ParseResultBase(TypedDict):
    """Normalized structure returned by every language parser."""

    functions: List[Dict[str, Any]]
    classes: List[Dict[str, Any]]
    imports: List[str]
    main_code: str
    language: str


class ParseResult(_ParseResultBase, total=False):
    """Normalized structure returned by every language parser."""

    source: str


@dataclass(frozen=True)
class LanguageProfile:
    """Everything the system needs to know about a programming language."""

    # Identity
    name: str
    display_name: str
    extensions: tuple[str, ...]
    tree_sitter_name: str
    code_fence_lang: str

    # Vocabulary for the generator
    function_noun: str
    class_noun: str
    method_noun: str
    import_noun: str
    import_step_title: str
    main_code_title: str
    main_code_description: str

    # Language-aware heuristics for the generator
    builtin_calls: tuple[str, ...] = ()
    state_tokens: tuple[str, ...] = ()
    iteration_keywords: tuple[str, ...] = ("for", "while")
    branch_keywords: tuple[str, ...] = ("if", "switch", "match")
    error_keywords: tuple[str, ...] = ("try", "catch", "except")

    # Tree-sitter node types for parsing (empty for Python which uses ast)
    function_node_types: tuple[str, ...] = ()
    class_node_types: tuple[str, ...] = ()
    import_node_types: tuple[str, ...] = ()
    method_node_types: tuple[str, ...] = ()
    non_code_node_types: tuple[str, ...] = ()


class BaseParser(Protocol):
    def parse(self, code: str) -> ParseResult:
        """Parse source code into a normalized structure.

        Returns dict with keys:
            functions: list of {name, body, args, docstring, source_line}
            classes: list of {name, body, methods, docstring, kind, source_line}
            imports: list of str
            main_code: str
            language: str
        """
        ...

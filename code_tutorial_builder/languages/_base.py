from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, TypedDict


class ParseResult(TypedDict):
    """Normalized structure returned by every language parser."""

    functions: List[Dict[str, Any]]
    classes: List[Dict[str, Any]]
    imports: List[str]
    main_code: str
    language: str


@dataclass(frozen=True)
class LanguageProfile:
    """Everything the system needs to know about a programming language."""

    # Identity
    name: str
    display_name: str
    extensions: tuple
    tree_sitter_name: str
    code_fence_lang: str

    # Vocabulary for the generator
    function_noun: str
    class_noun: str
    method_noun: str
    import_noun: str
    import_step_title: str
    import_step_description: str
    main_code_title: str
    main_code_description: str

    # Tree-sitter node types for parsing (empty for Python which uses ast)
    function_node_types: tuple = ()
    class_node_types: tuple = ()
    import_node_types: tuple = ()
    method_node_types: tuple = ()


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

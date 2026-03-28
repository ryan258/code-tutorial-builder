"""Tree-sitter based parser for non-Python languages.

This module is only imported when a non-Python file is parsed.
tree-sitter and tree-sitter-language-pack must be installed.
"""

from typing import Dict, Any, List, Optional

from ._base import LanguageProfile, ParseResult

# Map node types to kind labels for the generator.
_KIND_MAP = {
    "class_declaration": "class",
    "class_definition": "class",
    "interface_declaration": "interface",
    "type_declaration": "type",
    "struct_item": "struct",
    "enum_item": "enum",
}


class TreeSitterParser:
    """Parse source code using tree-sitter grammars."""

    def __init__(self, profile: LanguageProfile):
        import tree_sitter_language_pack as tslp

        self.profile = profile
        self._parser = tslp.get_parser(profile.tree_sitter_name)

    def parse(self, code: str) -> ParseResult:
        source = code.encode("utf-8")
        tree = self._parser.parse(source)

        functions: List[Dict[str, Any]] = []
        classes: List[Dict[str, Any]] = []
        imports: List[str] = []
        occupied: set = set()

        func_types = set(self.profile.function_node_types)
        class_types = set(self.profile.class_node_types)
        import_types = set(self.profile.import_node_types)
        non_code_types = set(self.profile.non_code_node_types)

        for node, source_node in self._iter_toplevel_nodes(tree.root_node):
            if node.type in func_types:
                functions.append(self._parse_function(node, source, source_node))
                self._mark_occupied(source_node, occupied)

            elif node.type in class_types:
                classes.append(self._parse_class(node, source, source_node))
                self._mark_occupied(source_node, occupied)

            elif node.type in import_types:
                imports.append(self._node_text(source_node, source))
                self._mark_occupied(source_node, occupied)

            elif node.type in non_code_types:
                self._mark_occupied(source_node, occupied)

        # Main code: lines not inside any extracted node
        lines = code.split("\n")
        main_lines = []
        for i, line in enumerate(lines):
            if i in occupied:
                continue
            stripped = line.strip()
            if stripped and not stripped.startswith("//") and not stripped.startswith("#"):
                main_lines.append(line)

        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "main_code": "\n".join(main_lines),
            "language": self.profile.name,
            "source": code,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _node_text(node, source: bytes) -> str:
        return source[node.start_byte : node.end_byte].decode("utf-8")

    @staticmethod
    def _mark_occupied(node, occupied: set) -> None:
        start_line = node.start_point.row
        end_line = node.end_point.row
        for line_no in range(start_line, end_line + 1):
            occupied.add(line_no)

    def _iter_toplevel_nodes(self, root):
        """Yield (semantic_node, source_node) for top-level declarations."""
        for node in root.children:
            if not node.is_named:
                continue
            yield from self._unwrap_toplevel_node(node, node)

    def _unwrap_toplevel_node(self, node, source_node):
        if node.type == "export_statement":
            for child in node.named_children:
                yield from self._unwrap_toplevel_node(child, source_node)
            return
        yield node, source_node

    def _extract_doc_comment(self, node, source: bytes) -> Optional[str]:
        """Extract a doc comment from the previous sibling, if any."""
        prev = node.prev_named_sibling
        if prev is None:
            return None
        if prev.type not in ("comment", "line_comment", "block_comment"):
            return None

        text = self._node_text(prev, source).strip()

        # Strip block comment delimiters first
        if text.startswith("/*") and text.endswith("*/"):
            text = text[2:-2].strip()
        elif text.startswith("/*"):
            text = text[2:].strip()

        # Strip line comment prefixes (longest match first)
        for prefix in ("///", "//!", "//", "#"):
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                break

        return text or None

    def _parse_function(self, node, source: bytes, source_node=None) -> Dict[str, Any]:
        source_node = source_node or node
        name_node = node.child_by_field_name("name")
        name = self._node_text(name_node, source) if name_node else "anonymous"

        params_node = (
            node.child_by_field_name("parameters")
            or node.child_by_field_name("formal_parameters")
        )
        args = self._extract_param_names(params_node, source) if params_node else []

        return {
            "name": name,
            "body": self._node_text(source_node, source),
            "args": args,
            "docstring": self._extract_doc_comment(source_node, source),
            "source_line": source_node.start_point.row + 1,
        }

    def _parse_class(self, node, source: bytes, source_node=None) -> Dict[str, Any]:
        source_node = source_node or node
        name_node = node.child_by_field_name("name")
        # For Go type_declaration, name is nested: type_declaration > type_spec > name
        if name_node is None:
            for child in node.named_children:
                name_node = child.child_by_field_name("name")
                if name_node:
                    break

        name = self._node_text(name_node, source) if name_node else "unknown"

        # Find methods inside the class body
        method_types = set(self.profile.method_node_types)
        methods = []
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.named_children:
                if child.type in method_types:
                    mname = child.child_by_field_name("name")
                    if mname:
                        methods.append(self._node_text(mname, source))

        kind = _KIND_MAP.get(node.type, "class")

        return {
            "name": name,
            "body": self._node_text(source_node, source),
            "methods": methods,
            "docstring": self._extract_doc_comment(source_node, source),
            "kind": kind,
            "source_line": source_node.start_point.row + 1,
        }

    def _extract_param_names(self, params_node, source: bytes) -> List[str]:
        """Extract parameter names from a parameters node."""
        names = []
        for child in params_node.named_children:
            # Languages use different field names for the parameter identifier:
            # "name" (JS, Go, Java), "pattern" (Rust, TypeScript)
            name_node = (
                child.child_by_field_name("name")
                or child.child_by_field_name("pattern")
            )
            if name_node:
                names.append(self._node_text(name_node, source))
            elif child.type == "identifier":
                names.append(self._node_text(child, source))
        return names

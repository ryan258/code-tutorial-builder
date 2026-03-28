import pytest

pytest.importorskip(
    "tree_sitter_language_pack",
    reason="tree-sitter language pack not installed",
)


from code_tutorial_builder.languages import get_parser


class TestJavaScriptParser:
    def setup_method(self):
        self.parser = get_parser("javascript")

    def test_parse_function(self):
        code = "function greet(name) {\n  console.log('Hello ' + name);\n}\n"
        result = self.parser.parse(code)
        assert len(result["functions"]) == 1
        assert result["functions"][0]["name"] == "greet"
        assert result["functions"][0]["args"] == ["name"]

    def test_parse_class(self):
        code = (
            "class Animal {\n"
            "  constructor(name) { this.name = name; }\n"
            "  speak() { return this.name; }\n"
            "}\n"
        )
        result = self.parser.parse(code)
        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "Animal"
        assert "constructor" in result["classes"][0]["methods"]
        assert "speak" in result["classes"][0]["methods"]
        assert result["classes"][0]["kind"] == "class"

    def test_parse_imports(self):
        code = "import { readFile } from 'fs';\n"
        result = self.parser.parse(code)
        assert len(result["imports"]) == 1
        assert "readFile" in result["imports"][0]

    def test_main_code(self):
        code = "function greet() {}\n\nconst x = greet();\n"
        result = self.parser.parse(code)
        assert "const x" in result["main_code"]
        assert "function greet" not in result["main_code"]

    def test_language_field(self):
        result = self.parser.parse("const x = 1;\n")
        assert result["language"] == "javascript"

    def test_parse_exported_declarations(self):
        code = (
            "export function greet(name) {\n"
            "  return name;\n"
            "}\n"
            "export class Animal {\n"
            "  speak() { return 'hi'; }\n"
            "}\n"
        )
        result = self.parser.parse(code)
        assert len(result["functions"]) == 1
        assert result["functions"][0]["name"] == "greet"
        assert result["functions"][0]["body"].startswith("export function")
        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "Animal"
        assert result["classes"][0]["body"].startswith("export class")
        assert result["main_code"] == ""

    def test_source_line_metadata(self):
        code = (
            "class Animal {\n"
            "  speak() { return 'hi'; }\n"
            "}\n"
            "\n"
            "function greet(name) {\n"
            "  return name;\n"
            "}\n"
        )
        result = self.parser.parse(code)
        assert result["classes"][0]["source_line"] == 1
        assert result["functions"][0]["source_line"] == 5


class TestGoParser:
    def setup_method(self):
        self.parser = get_parser("go")

    def test_parse_function(self):
        code = "package main\n\nfunc greet(name string) {\n}\n"
        result = self.parser.parse(code)
        assert len(result["functions"]) == 1
        assert result["functions"][0]["name"] == "greet"
        assert result["functions"][0]["args"] == ["name"]

    def test_parse_struct(self):
        code = "package main\n\ntype Server struct {\n\tHost string\n}\n"
        result = self.parser.parse(code)
        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "Server"
        assert result["classes"][0]["kind"] == "type"

    def test_parse_import(self):
        code = 'package main\n\nimport "fmt"\n'
        result = self.parser.parse(code)
        assert len(result["imports"]) == 1
        assert "fmt" in result["imports"][0]

    def test_package_clause_excluded_from_main_code(self):
        code = "package main\n\nfunc greet() {}\n"
        result = self.parser.parse(code)
        assert "package main" not in result["main_code"]


class TestRustParser:
    def setup_method(self):
        self.parser = get_parser("rust")

    def test_parse_function(self):
        code = "fn greet(name: &str) {\n    println!(\"Hello {}\", name);\n}\n"
        result = self.parser.parse(code)
        assert len(result["functions"]) == 1
        assert result["functions"][0]["name"] == "greet"
        assert result["functions"][0]["args"] == ["name"]

    def test_parse_struct(self):
        code = "struct Point {\n    x: f64,\n    y: f64,\n}\n"
        result = self.parser.parse(code)
        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "Point"
        assert result["classes"][0]["kind"] == "struct"

    def test_parse_enum(self):
        code = "enum Color {\n    Red,\n    Green,\n}\n"
        result = self.parser.parse(code)
        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "Color"
        assert result["classes"][0]["kind"] == "enum"

    def test_parse_impl_block(self):
        code = (
            "struct Point {\n"
            "    x: f64,\n"
            "    y: f64,\n"
            "}\n"
            "\n"
            "impl Point {\n"
            "    fn new(x: f64, y: f64) -> Self {\n"
            "        Point { x, y }\n"
            "    }\n"
            "    fn distance(&self) -> f64 {\n"
            "        (self.x * self.x + self.y * self.y).sqrt()\n"
            "    }\n"
            "}\n"
        )
        result = self.parser.parse(code)
        impl_entries = [c for c in result["classes"] if c["kind"] == "impl"]
        assert len(impl_entries) == 1
        impl_block = impl_entries[0]
        assert impl_block["name"] == "impl Point"
        assert "new" in impl_block["methods"]
        assert "distance" in impl_block["methods"]
        assert "impl Point" not in result["main_code"]


class TestTypeScriptParser:
    def setup_method(self):
        self.parser = get_parser("typescript")

    def test_parse_interface(self):
        code = "interface User {\n    name: string;\n    age: number;\n}\n"
        result = self.parser.parse(code)
        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "User"
        assert result["classes"][0]["kind"] == "interface"

    def test_parse_function_with_types(self):
        code = "function greet(user: User): string {\n    return 'Hello';\n}\n"
        result = self.parser.parse(code)
        assert result["functions"][0]["name"] == "greet"
        assert result["functions"][0]["args"] == ["user"]

    def test_class_fields_not_treated_as_methods(self):
        code = (
            "class User {\n"
            "    name: string;\n"
            "    age: number = 0;\n"
            "    greet() { return this.name; }\n"
            "}\n"
        )
        result = self.parser.parse(code)
        assert len(result["classes"]) == 1
        cls = result["classes"][0]
        assert "greet" in cls["methods"]
        assert "name" not in cls["methods"]
        assert "age" not in cls["methods"]

    def test_parse_exported_interface_and_function(self):
        code = (
            "export interface User {\n"
            "    name: string;\n"
            "}\n"
            "export function greet(user: User): string {\n"
            "    return user.name;\n"
            "}\n"
        )
        result = self.parser.parse(code)
        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "User"
        assert result["classes"][0]["body"].startswith("export interface")
        assert len(result["functions"]) == 1
        assert result["functions"][0]["name"] == "greet"
        assert result["functions"][0]["body"].startswith("export function")
        assert result["main_code"] == ""


class TestJavaParser:
    def setup_method(self):
        self.parser = get_parser("java")

    def test_parse_class_with_methods(self):
        code = (
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            '        System.out.println("Hello");\n'
            "    }\n"
            "    public int add(int a, int b) {\n"
            "        return a + b;\n"
            "    }\n"
            "}\n"
        )
        result = self.parser.parse(code)
        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "Main"
        assert "main" in result["classes"][0]["methods"]
        assert "add" in result["classes"][0]["methods"]

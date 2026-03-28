import pytest
from code_tutorial_builder.analysis import (
    Component,
    ProgramAnalysis,
    analyze,
    _find_calls,
    _detect_concepts,
    _topological_sort,
)
from code_tutorial_builder.languages import PythonParser, get_profile


class TestFindCalls:
    def test_finds_call_to_defined_function(self):
        profile = get_profile("python")
        defined = {"helper", "process"}
        body = "def process(data):\n    return helper(data)"
        calls = _find_calls(body, "process", defined, profile)
        assert calls == ["helper"]

    def test_ignores_self_calls(self):
        profile = get_profile("python")
        defined = {"factorial"}
        body = "def factorial(n):\n    return n * factorial(n - 1)"
        calls = _find_calls(body, "factorial", defined, profile)
        assert calls == []

    def test_ignores_undefined_names(self):
        profile = get_profile("python")
        defined = {"helper"}
        body = "def process():\n    return unknown() + helper()"
        calls = _find_calls(body, "process", defined, profile)
        assert calls == ["helper"]

    def test_empty_body(self):
        profile = get_profile("python")
        calls = _find_calls("def f():\n    pass", "f", set(), profile)
        assert calls == []


class TestDetectConcepts:
    def test_detects_recursion(self):
        profile = get_profile("python")
        body = "def f(n):\n    return f(n - 1)"
        concepts = _detect_concepts(body, "f", profile)
        assert "recursion" in concepts

    def test_detects_iteration(self):
        profile = get_profile("python")
        body = "def f():\n    for i in range(10): pass"
        concepts = _detect_concepts(body, "f", profile)
        assert "iteration" in concepts

    def test_detects_control_flow(self):
        profile = get_profile("python")
        body = "def f(x):\n    if x > 0: return x"
        concepts = _detect_concepts(body, "f", profile)
        assert "control flow" in concepts

    def test_detects_error_handling(self):
        profile = get_profile("python")
        body = "def f():\n    try:\n        pass\n    except:\n        pass"
        concepts = _detect_concepts(body, "f", profile)
        assert "error handling" in concepts

    def test_detects_state_management(self):
        profile = get_profile("python")
        body = "class C:\n    def f(self):\n        self.x = 1"
        concepts = _detect_concepts(body, "C", profile)
        assert "state management" in concepts

    def test_no_false_positive_recursion_from_signature(self):
        """Function name in the signature line should not count as recursion."""
        profile = get_profile("python")
        body = "def factorial(n):\n    return 1"
        concepts = _detect_concepts(body, "factorial", profile)
        assert "recursion" not in concepts


class TestTopologicalSort:
    def test_simple_chain(self):
        components = [
            Component(name="a", kind="function", body="", calls=["b"]),
            Component(name="b", kind="function", body="", calls=[]),
        ]
        call_graph = {"a": ["b"], "b": []}
        order = _topological_sort(components, call_graph)
        assert order == ["b", "a"]

    def test_independent_components(self):
        components = [
            Component(name="a", kind="function", body="", calls=[]),
            Component(name="b", kind="function", body="", calls=[]),
        ]
        call_graph = {"a": [], "b": []}
        order = _topological_sort(components, call_graph)
        # Independent: preserve original order
        assert order == ["a", "b"]

    def test_diamond_dependency(self):
        components = [
            Component(name="top", kind="function", body="", calls=["left", "right"]),
            Component(name="left", kind="function", body="", calls=["bottom"]),
            Component(name="right", kind="function", body="", calls=["bottom"]),
            Component(name="bottom", kind="function", body="", calls=[]),
        ]
        call_graph = {
            "top": ["left", "right"],
            "left": ["bottom"],
            "right": ["bottom"],
            "bottom": [],
        }
        order = _topological_sort(components, call_graph)
        assert order.index("bottom") < order.index("left")
        assert order.index("bottom") < order.index("right")
        assert order.index("left") < order.index("top")
        assert order.index("right") < order.index("top")

    def test_cycle_fallback(self):
        """Mutual recursion: both should still appear."""
        components = [
            Component(name="a", kind="function", body="", calls=["b"]),
            Component(name="b", kind="function", body="", calls=["a"]),
        ]
        call_graph = {"a": ["b"], "b": ["a"]}
        order = _topological_sort(components, call_graph)
        assert set(order) == {"a", "b"}


class TestAnalyze:
    def setup_method(self):
        self.parser = PythonParser()
        self.profile = get_profile("python")

    def test_basic_analysis(self):
        code = (
            "def helper():\n"
            "    return 1\n"
            "\n"
            "def caller():\n"
            "    return helper()\n"
        )
        parsed = self.parser.parse(code)
        result = analyze(parsed, self.profile)

        assert isinstance(result, ProgramAnalysis)
        assert len(result.components) == 2
        assert result.dependency_order == ["helper", "caller"]
        assert result.call_graph["caller"] == ["helper"]
        assert result.reverse_graph["helper"] == ["caller"]

    def test_component_concepts(self):
        code = (
            "def factorial(n):\n"
            "    if n == 0:\n"
            "        return 1\n"
            "    return n * factorial(n - 1)\n"
        )
        parsed = self.parser.parse(code)
        result = analyze(parsed, self.profile)

        comp = result.get_component("factorial")
        assert comp is not None
        assert "recursion" in comp.concepts
        assert "control flow" in comp.concepts

    def test_program_level_concepts(self):
        code = (
            "class Foo:\n"
            "    def bar(self):\n"
            "        self.x = 1\n"
        )
        parsed = self.parser.parse(code)
        result = analyze(parsed, self.profile)
        assert "state management" in result.concepts

    def test_get_component_returns_none_for_missing(self):
        parsed = self.parser.parse("x = 1\n")
        result = analyze(parsed, self.profile)
        assert result.get_component("nonexistent") is None

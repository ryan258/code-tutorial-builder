import pytest
from code_tutorial_builder.languages import (
    LANGUAGES,
    PythonParser,
    detect_language,
    get_parser,
    get_profile,
)


class TestLanguageRegistry:
    def test_all_languages_registered(self):
        expected = {"python", "javascript", "typescript", "go", "rust", "java"}
        assert set(LANGUAGES.keys()) == expected

    def test_profiles_have_required_fields(self):
        for name, profile in LANGUAGES.items():
            assert profile.name == name
            assert profile.display_name
            assert profile.extensions
            assert profile.code_fence_lang
            assert profile.function_noun
            assert profile.class_noun

    def test_profiles_have_language_heuristics(self):
        """Every profile should have language-aware heuristic fields."""
        for name, profile in LANGUAGES.items():
            assert isinstance(profile.builtin_calls, tuple), f"{name} missing builtin_calls"
            assert isinstance(profile.state_tokens, tuple), f"{name} missing state_tokens"
            assert isinstance(profile.iteration_keywords, tuple), f"{name} missing iteration_keywords"
            assert isinstance(profile.branch_keywords, tuple), f"{name} missing branch_keywords"
            assert isinstance(profile.error_keywords, tuple), f"{name} missing error_keywords"

    def test_python_builtins_include_common_names(self):
        profile = get_profile("python")
        assert "print" in profile.builtin_calls
        assert "len" in profile.builtin_calls
        assert "range" in profile.builtin_calls

    def test_javascript_builtins_include_common_names(self):
        profile = get_profile("javascript")
        assert "console" in profile.builtin_calls
        assert "parseInt" in profile.builtin_calls

    def test_go_builtins_include_common_names(self):
        profile = get_profile("go")
        assert "fmt" in profile.builtin_calls
        assert "len" in profile.builtin_calls


class TestLanguageDetection:
    @pytest.mark.parametrize("path,expected", [
        ("app.py", "python"),
        ("app.js", "javascript"),
        ("app.mjs", "javascript"),
        ("app.ts", "typescript"),
        ("main.go", "go"),
        ("lib.rs", "rust"),
        ("Main.java", "java"),
    ])
    def test_detect_known_extensions(self, path, expected):
        assert detect_language(path) == expected

    def test_detect_unknown_extension(self):
        assert detect_language("file.xyz") is None

    def test_detect_no_extension(self):
        assert detect_language("Makefile") is None

    def test_detect_unsupported_tsx(self):
        assert detect_language("app.tsx") is None


class TestGetParser:
    def test_python_returns_builtin_parser(self):
        parser = get_parser("python")
        assert isinstance(parser, PythonParser)

    def test_unsupported_language_raises(self):
        with pytest.raises(ValueError, match="Unsupported language"):
            get_profile("brainfuck")


class TestGetProfile:
    def test_python_profile(self):
        profile = get_profile("python")
        assert profile.code_fence_lang == "python"
        assert profile.class_noun == "class"

    def test_go_profile(self):
        profile = get_profile("go")
        assert profile.code_fence_lang == "go"
        assert profile.class_noun == "type"

    def test_rust_profile(self):
        profile = get_profile("rust")
        assert profile.class_noun == "struct"
        assert profile.import_noun == "use"

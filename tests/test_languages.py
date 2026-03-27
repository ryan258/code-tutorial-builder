import pytest
from code_tutorial_builder.languages import (
    LANGUAGES,
    detect_language,
    get_parser,
    get_profile,
)
from code_tutorial_builder.parser import PythonParser


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

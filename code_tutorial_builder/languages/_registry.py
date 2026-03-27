from pathlib import Path
from typing import Optional

from ._base import LanguageProfile, BaseParser

LANGUAGES: dict = {}
_EXTENSION_MAP: dict = {}


def register(profile: LanguageProfile) -> None:
    """Register a language profile."""
    LANGUAGES[profile.name] = profile
    for ext in profile.extensions:
        _EXTENSION_MAP[ext] = profile.name


def detect_language(filepath: str) -> Optional[str]:
    """Detect language from file extension. Returns language name or None."""
    ext = Path(filepath).suffix.lower()
    return _EXTENSION_MAP.get(ext)


def get_profile(language: str) -> LanguageProfile:
    """Get the LanguageProfile for a language name."""
    profile = LANGUAGES.get(language)
    if profile is None:
        supported = ", ".join(sorted(LANGUAGES.keys()))
        raise ValueError(f"Unsupported language: {language}. Supported: {supported}")
    return profile


def get_parser(language: str) -> BaseParser:
    """Get the appropriate parser for a language.

    For Python: returns the built-in AST parser (no extra deps).
    For everything else: returns TreeSitterParser (requires optional dep).
    """
    if language == "python":
        from ..parser import PythonParser
        return PythonParser()

    try:
        from ._treesitter import TreeSitterParser
    except ImportError:
        raise ImportError(
            f"Parsing {language} files requires tree-sitter. "
            f"Install it with: pip install code-tutorial-builder[multilang]"
        )

    profile = get_profile(language)
    return TreeSitterParser(profile)

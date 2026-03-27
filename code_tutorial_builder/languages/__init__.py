from ._base import LanguageProfile, BaseParser, ParseResult
from ._registry import LANGUAGES, detect_language, get_parser, get_profile, register

# Import each language module to trigger registration
from . import python, javascript, typescript, go, rust, java

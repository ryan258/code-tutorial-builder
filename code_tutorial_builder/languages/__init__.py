# Import each language module to trigger registration
from . import go, java, javascript, python, rust, typescript
from ._base import BaseParser, LanguageProfile, ParseResult
from ._python_parser import PythonParser
from ._registry import LANGUAGES, detect_language, get_parser, get_profile, register

from ._base import LanguageProfile
from ._registry import register

profile = LanguageProfile(
    name="python",
    display_name="Python",
    extensions=(".py",),
    tree_sitter_name="python",
    code_fence_lang="python",
    function_noun="function",
    class_noun="class",
    method_noun="method",
    import_noun="import",
    import_step_title="Importing Required Modules",
    main_code_title="Main Execution",
    main_code_description="This is the main execution part of the code.",
    builtin_calls=(
        "abs", "all", "any", "bin", "bool", "bytes", "callable", "chr",
        "dict", "dir", "divmod", "enumerate", "eval", "filter", "float",
        "format", "frozenset", "getattr", "hasattr", "hash", "hex", "id",
        "input", "int", "isinstance", "issubclass", "iter", "len", "list",
        "map", "max", "min", "next", "object", "oct", "open", "ord", "pow",
        "print", "range", "repr", "reversed", "round", "set", "setattr",
        "slice", "sorted", "str", "sum", "super", "tuple", "type", "vars",
        "zip",
    ),
    state_tokens=("self.",),
    iteration_keywords=("for", "while"),
    branch_keywords=("if", "elif", "else", "match", "case"),
    error_keywords=("try", "except", "finally", "raise"),
    function_node_types=("function_definition",),
    class_node_types=("class_definition",),
    import_node_types=("import_statement", "import_from_statement"),
    method_node_types=("function_definition",),
)

register(profile)

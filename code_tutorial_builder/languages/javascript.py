from ._base import LanguageProfile
from ._registry import register

profile = LanguageProfile(
    name="javascript",
    display_name="JavaScript",
    extensions=(".js", ".mjs", ".cjs"),
    tree_sitter_name="javascript",
    code_fence_lang="javascript",
    function_noun="function",
    class_noun="class",
    method_noun="method",
    import_noun="import",
    import_step_title="Importing Dependencies",
    main_code_title="Main Execution",
    main_code_description="This is the main execution logic of the script.",
    builtin_calls=(
        "Array", "Boolean", "Date", "Error", "JSON", "Math", "Number",
        "Object", "Promise", "RegExp", "String", "Symbol", "TypeError",
        "console", "parseInt", "parseFloat", "isNaN", "isFinite",
        "setTimeout", "setInterval", "clearTimeout", "clearInterval",
        "fetch", "require",
    ),
    state_tokens=("this.",),
    iteration_keywords=("for", "while", "forEach", "map", "reduce"),
    branch_keywords=("if", "else", "switch", "case"),
    error_keywords=("try", "catch", "finally", "throw"),
    function_node_types=("function_declaration",),
    class_node_types=("class_declaration",),
    import_node_types=("import_statement",),
    method_node_types=("method_definition",),
)

register(profile)

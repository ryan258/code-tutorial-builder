from ._base import LanguageProfile
from ._registry import register

profile = LanguageProfile(
    name="rust",
    display_name="Rust",
    extensions=(".rs",),
    tree_sitter_name="rust",
    code_fence_lang="rust",
    function_noun="function",
    class_noun="struct",
    method_noun="method",
    import_noun="use",
    import_step_title="Importing Crates and Modules",
    main_code_title="Main Function",
    main_code_description="This is the entry point of the program.",
    builtin_calls=(
        "println", "eprintln", "format", "panic", "assert", "assert_eq",
        "assert_ne", "dbg", "todo", "unimplemented", "unreachable",
        "vec", "String", "Vec", "Box", "Rc", "Arc", "Option", "Result",
        "Ok", "Err", "Some", "None",
    ),
    state_tokens=("self.", "Self"),
    iteration_keywords=("for", "while", "loop", "iter", "into_iter"),
    branch_keywords=("if", "else", "match"),
    error_keywords=("Result", "Option", "unwrap", "expect", "panic", "?"),
    function_node_types=("function_item",),
    class_node_types=("struct_item", "enum_item"),
    import_node_types=("use_declaration",),
    method_node_types=(),  # Rust impl blocks are separate top-level items
)

register(profile)

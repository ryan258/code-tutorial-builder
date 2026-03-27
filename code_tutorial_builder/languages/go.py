from ._base import LanguageProfile
from ._registry import register

profile = LanguageProfile(
    name="go",
    display_name="Go",
    extensions=(".go",),
    tree_sitter_name="go",
    code_fence_lang="go",
    function_noun="function",
    class_noun="type",
    method_noun="method",
    import_noun="import",
    import_step_title="Importing Packages",
    import_step_description="First, we import the necessary Go packages.",
    main_code_title="Main Function and Execution",
    main_code_description="This is the main entry point of the program.",
    # Go method_declaration is top-level (receiver-based), not nested in types
    function_node_types=("function_declaration", "method_declaration"),
    class_node_types=("type_declaration",),
    import_node_types=("import_declaration",),
    method_node_types=(),
)

register(profile)

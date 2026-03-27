from ._base import LanguageProfile
from ._registry import register

profile = LanguageProfile(
    name="typescript",
    display_name="TypeScript",
    extensions=(".ts",),
    tree_sitter_name="typescript",
    code_fence_lang="typescript",
    function_noun="function",
    class_noun="class",
    method_noun="method",
    import_noun="import",
    import_step_title="Importing Dependencies",
    import_step_description="First, we import the required modules and types.",
    main_code_title="Main Execution",
    main_code_description="This is the main execution logic of the module.",
    function_node_types=("function_declaration",),
    class_node_types=("class_declaration", "interface_declaration"),
    import_node_types=("import_statement",),
    method_node_types=("method_definition", "public_field_definition"),
)

register(profile)

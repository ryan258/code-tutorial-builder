from ._base import LanguageProfile
from ._registry import register

profile = LanguageProfile(
    name="java",
    display_name="Java",
    extensions=(".java",),
    tree_sitter_name="java",
    code_fence_lang="java",
    function_noun="method",
    class_noun="class",
    method_noun="method",
    import_noun="import",
    import_step_title="Importing Packages",
    import_step_description="First, we import the necessary Java packages.",
    main_code_title="Main Method",
    main_code_description="This is the entry point of the application.",
    function_node_types=(),  # Java methods live inside classes
    class_node_types=("class_declaration", "interface_declaration"),
    import_node_types=("import_declaration",),
    method_node_types=("method_declaration", "constructor_declaration"),
)

register(profile)

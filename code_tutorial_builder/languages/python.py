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
    import_step_description="First, we import the necessary modules for our code.",
    main_code_title="Main Execution",
    main_code_description="This is the main execution part of the code.",
    function_node_types=("function_definition",),
    class_node_types=("class_definition",),
    import_node_types=("import_statement", "import_from_statement"),
    method_node_types=("function_definition",),
)

register(profile)

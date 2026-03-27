import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, Template

from .ai import OpenRouterClient, build_openrouter_client
from .config import Config
from .languages._base import LanguageProfile, ParseResult

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

logger = logging.getLogger(__name__)

_NON_TEACHING_CALLS = {
    "bool",
    "dict",
    "enumerate",
    "float",
    "int",
    "len",
    "list",
    "map",
    "max",
    "min",
    "print",
    "range",
    "set",
    "sorted",
    "str",
    "sum",
    "tuple",
}


class TutorialGenerator:
    """Generate tutorials from parsed code."""

    def __init__(self, config: Config, ai_client: Optional[OpenRouterClient] = None):
        self.config = config
        self.ai_client = ai_client
        self.env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))

    def generate(self, parsed_code: ParseResult, title: str = "Code Tutorial") -> str:
        """
        Generate a tutorial from parsed code.

        Returns:
            Markdown formatted tutorial string
        """
        language = parsed_code.get("language", "python")

        from .languages import get_profile
        profile = get_profile(language)

        steps = self._create_steps(parsed_code, profile)
        if self.config.use_ai:
            steps = self._enhance_steps_with_ai(language, steps)
        steps = [self._decorate_step(step, profile) for step in steps]

        overview = self._build_overview(parsed_code, profile, steps)
        warm_up = self._build_warm_up(parsed_code, profile)
        vocabulary = self._build_vocabulary(parsed_code, profile)
        learning_goals = self._build_learning_goals(parsed_code, profile)
        teaching_tips = self._build_teaching_tips(parsed_code)
        checks_for_understanding = self._build_checks_for_understanding(steps)
        extension_challenge = self._build_extension_challenge(parsed_code, profile)
        recap_points = self._build_recap_points(steps)
        lesson_stats = self._build_lesson_stats(parsed_code, profile, steps)

        if self.config.template:
            template = Template(Path(self.config.template).read_text(encoding="utf-8"))
        else:
            template = self.env.get_template("default.md.j2")

        return template.render(
            title=title,
            steps=steps,
            overview=overview,
            warm_up=warm_up,
            vocabulary=vocabulary,
            learning_goals=learning_goals,
            teaching_tips=teaching_tips,
            checks_for_understanding=checks_for_understanding,
            extension_challenge=extension_challenge,
            recap_points=recap_points,
            lesson_stats=lesson_stats,
            code_fence_lang=profile.code_fence_lang,
        )

    def _enhance_steps_with_ai(
        self,
        language: str,
        steps: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Use OpenRouter to improve step titles and descriptions."""
        if not steps:
            return steps

        client = self.ai_client or build_openrouter_client(
            search_path=self.config.env_search_path,
        )
        if client is None:
            raise ValueError(
                "AI mode requires OPENROUTER_API_KEY in a .env file or environment."
            )

        return client.rewrite_steps(language=language, steps=steps)

    def _create_steps(
        self,
        parsed_code: ParseResult,
        profile: LanguageProfile,
    ) -> List[Dict[str, Any]]:
        """Create tutorial steps from parsed code."""
        steps: List[Dict[str, Any]] = []

        if parsed_code.get("imports"):
            steps.append(
                {
                    "step_type": "imports",
                    "title": profile.import_step_title,
                    "description": self._default_import_description(
                        parsed_code["imports"],
                        profile,
                    ),
                    "code": "\n".join(parsed_code["imports"]),
                    "imports": list(parsed_code["imports"]),
                }
            )

        for item_type, item in self._ordered_definitions(parsed_code):
            if item_type == "function":
                steps.append(
                    {
                        "step_type": "function",
                        "name": item["name"],
                        "title": f"Understanding the {item['name']} {profile.function_noun}",
                        "description": item.get("docstring")
                        or self._default_function_description(item, profile),
                        "code": item["body"],
                        "args": list(item.get("args") or []),
                        "is_recursive": self._is_recursive(item),
                    }
                )
                continue

            kind = item.get("kind", profile.class_noun)
            steps.append(
                {
                    "step_type": "class",
                    "name": item["name"],
                    "kind_label": kind,
                    "title": f"Understanding the {item['name']} {kind}",
                    "description": item.get("docstring")
                    or self._default_class_description(item, profile),
                    "code": item["body"],
                    "methods": list(item.get("methods") or []),
                }
            )

        has_main = bool(parsed_code.get("main_code"))
        budget = self.config.steps - (1 if has_main else 0)

        if len(steps) > budget:
            logger.warning(
                "Truncating from %d to %d steps (--steps %d); "
                "increase --steps to include all components.",
                len(steps) + (1 if has_main else 0),
                self.config.steps,
                self.config.steps,
            )
            steps = steps[:budget]

        if has_main:
            steps.append(
                {
                    "step_type": "main",
                    "title": profile.main_code_title,
                    "description": self._default_main_description(
                        parsed_code["main_code"],
                        profile,
                    ),
                    "code": parsed_code["main_code"],
                }
            )

        return steps

    def _decorate_step(
        self,
        step: Dict[str, Any],
        profile: LanguageProfile,
    ) -> Dict[str, Any]:
        if step["step_type"] == "imports":
            return {
                **step,
                "spotlight": (
                    "These lines introduce the outside tools the program needs before any of the"
                    " core logic can make sense."
                ),
                "key_points": self._import_key_points(step["imports"], profile),
                "prompts": [
                    f"Which {profile.import_noun} is most important for the rest of the file?",
                    "What would break first if one of these imports disappeared?",
                ],
                "practice": (
                    f"Ask students to point to the first place each {profile.import_noun} becomes"
                    " useful later in the lesson."
                ),
            }

        if step["step_type"] == "function":
            return {
                **step,
                "spotlight": (
                    f"Focus on how `{step['name']}` turns its inputs into a clear result and"
                    " what mental model students need to trace it confidently."
                ),
                "key_points": self._function_key_points(step, profile),
                "prompts": self._function_prompts(step, profile),
                "practice": self._function_practice(step),
            }

        if step["step_type"] == "class":
            return {
                **step,
                "spotlight": (
                    f"This step shows how `{step['name']}` bundles related data and behavior into"
                    " one reusable abstraction."
                ),
                "key_points": self._class_key_points(step, profile),
                "prompts": self._class_prompts(step, profile),
                "practice": self._class_practice(step, profile),
            }

        return {
            **step,
            "spotlight": (
                "This is the orchestration step where students connect the earlier building blocks"
                " into one complete program run."
            ),
            "key_points": self._main_code_key_points(step["code"]),
            "prompts": self._main_code_prompts(step["code"]),
            "practice": (
                "Pause before running this section and ask students to predict the order of calls,"
                " outputs, or state changes."
            ),
        }

    def _build_overview(
        self,
        parsed_code: ParseResult,
        profile: LanguageProfile,
        steps: List[Dict[str, Any]],
    ) -> str:
        lesson_parts = []
        if parsed_code.get("imports"):
            lesson_parts.append(
                f"{len(parsed_code['imports'])} {self._pluralize(profile.import_noun, len(parsed_code['imports']))}"
            )
        if parsed_code.get("functions"):
            lesson_parts.append(
                f"{len(parsed_code['functions'])} {self._pluralize(profile.function_noun, len(parsed_code['functions']))}"
            )
        if parsed_code.get("classes"):
            lesson_parts.append(
                f"{len(parsed_code['classes'])} {self._pluralize(profile.class_noun, len(parsed_code['classes']))}"
            )
        if parsed_code.get("main_code"):
            lesson_parts.append("a final execution flow")

        concept_text = self._join_with_and(self._concepts(parsed_code))
        if lesson_parts:
            base = (
                f"This {profile.display_name} lesson breaks the program into {len(steps)}"
                f" teaching {'step' if len(steps) == 1 else 'steps'}, covering"
                f" {self._join_with_and(lesson_parts)}."
            )
        else:
            base = (
                f"This {profile.display_name} lesson focuses on reading the code carefully and"
                " explaining how each section contributes to the whole program."
            )

        if concept_text:
            return f"{base} Along the way, students will encounter {concept_text}."
        return base

    def _build_learning_goals(
        self,
        parsed_code: ParseResult,
        profile: LanguageProfile,
    ) -> List[str]:
        goals: List[str] = []
        if parsed_code.get("imports"):
            goals.append(
                f"Explain why each {profile.import_noun} appears before the main logic begins."
            )
        if parsed_code.get("functions"):
            goals.append(
                f"Trace how each {profile.function_noun} uses inputs, decisions, and return values."
            )
        if parsed_code.get("classes"):
            goals.append(
                f"Describe how each {profile.class_noun} groups responsibilities and manages state."
            )
        if parsed_code.get("main_code"):
            goals.append(
                "Connect the supporting definitions to the final execution flow."
            )
        if not goals:
            goals.append(
                "Read unfamiliar code methodically and explain what happens in each section."
            )
        return goals[:4]

    def _build_teaching_tips(self, parsed_code: ParseResult) -> List[str]:
        tips = [
            "Ask students to predict what the code will do before you reveal the explanation or run it.",
            "Have learners annotate where data enters, changes, and leaves the program.",
            "Pause after each step and connect it back to the overall goal of the program.",
        ]
        functions = parsed_code.get("functions", [])
        if any(self._is_recursive(func) for func in functions):
            tips.append(
                "For recursion, trace one concrete call stack on paper and mark the stopping case before running the code."
            )
        if parsed_code.get("classes"):
            tips.append(
                "Separate what the type knows (state) from what it does (methods) so object-oriented structure feels less abstract."
            )
        if parsed_code.get("main_code"):
            tips.append(
                "Use the final execution step as a recap: students should be able to explain every call it makes."
            )
        return tips[:5]

    def _build_recap_points(self, steps: List[Dict[str, Any]]) -> List[str]:
        return [self._step_takeaway(step) for step in steps[:4]]

    def _build_lesson_stats(
        self,
        parsed_code: ParseResult,
        profile: LanguageProfile,
        steps: List[Dict[str, Any]],
    ) -> List[str]:
        components = self._component_summary(parsed_code, profile)
        concepts = self._concepts(parsed_code)
        return [
            f"Language: {profile.display_name}",
            f"Suggested level: {self._estimate_difficulty(parsed_code, steps)}",
            f"Estimated pacing: {self._estimate_pacing(steps)}",
            f"Lesson steps: {len(steps)}",
            f"Components covered: {components}",
            f"Core concepts: {self._join_with_and(concepts) or 'program flow'}",
        ]

    def _build_warm_up(
        self,
        parsed_code: ParseResult,
        profile: LanguageProfile,
    ) -> str:
        functions = parsed_code.get("functions", [])
        if any(self._is_recursive(func) for func in functions):
            return (
                "Ask students what has to be true for a recursive call to stop, then have them"
                " predict where that stopping case appears in the code."
            )
        if parsed_code.get("classes"):
            return (
                f"Ask why someone might choose a {profile.class_noun} instead of scattered"
                " variables and helper code when solving this problem."
            )
        if parsed_code.get("imports"):
            return (
                f"Ask students what this program would have to build from scratch if these"
                f" {self._pluralize(profile.import_noun, len(parsed_code['imports']))} were missing."
            )
        if parsed_code.get("functions"):
            return (
                f"Ask students why breaking a problem into separate {self._pluralize(profile.function_noun, len(parsed_code['functions']))}"
                " can make a program easier to understand and debug."
            )
        return (
            "Ask students to scan the file for the first line that changes state or produces an output,"
            " then explain why that line matters."
        )

    def _build_vocabulary(
        self,
        parsed_code: ParseResult,
        profile: LanguageProfile,
    ) -> List[str]:
        vocabulary: List[str] = []
        if parsed_code.get("imports"):
            vocabulary.append(
                f"`{profile.import_noun}`: code this file pulls in before the main logic starts."
            )
        if parsed_code.get("functions"):
            vocabulary.append("`parameter`: a named input a function receives.")
            vocabulary.append("`return value`: the result a function gives back to its caller.")
        if parsed_code.get("classes"):
            vocabulary.append(
                f"`{profile.class_noun}`: a reusable unit that groups related data and behavior."
            )
            vocabulary.append(
                f"`{profile.method_noun}`: a behavior that belongs to a specific {profile.class_noun}."
            )
            vocabulary.append("`state`: information an object keeps track of between actions.")

        concepts = self._concepts(parsed_code)
        if "recursion" in concepts:
            vocabulary.append(
                "`recursion`: solving a problem by calling the same function on a smaller case."
            )
        if "iteration" in concepts:
            vocabulary.append("`iteration`: repeating work with a loop.")
        if "control flow" in concepts:
            vocabulary.append(
                "`control flow`: the decisions that determine which lines run next."
            )

        deduped: List[str] = []
        for item in vocabulary:
            if item not in deduped:
                deduped.append(item)
        return deduped[:6]

    def _build_checks_for_understanding(
        self,
        steps: List[Dict[str, Any]],
    ) -> List[str]:
        questions = [
            "Where does data enter the program, and where does it leave?",
            "Which step would you revisit first if the final output looked wrong?",
        ]
        first_named_step = next(
            (
                step
                for step in steps
                if step["step_type"] in {"function", "class"}
            ),
            None,
        )
        if first_named_step is not None:
            questions.insert(
                0,
                f"What essential job would disappear if `{first_named_step['name']}` were removed?",
            )
        if any(step["step_type"] == "main" for step in steps):
            questions.append(
                "Which earlier definition does the final execution step rely on first?"
            )
        return questions[:4]

    def _build_extension_challenge(
        self,
        parsed_code: ParseResult,
        profile: LanguageProfile,
    ) -> str:
        functions = parsed_code.get("functions", [])
        if any(self._is_recursive(func) for func in functions):
            return (
                "Rewrite the recursive logic in an iterative style, then compare which version is"
                " easier to explain and why."
            )
        if parsed_code.get("classes"):
            first_class = parsed_code["classes"][0]["name"]
            return (
                f"Add one new {profile.method_noun} to `{first_class}` that would make the type"
                " more useful, and justify why that behavior belongs there."
            )
        if functions:
            first_function = functions[0]["name"]
            return (
                f"Modify `{first_function}` to handle one new edge case, and have students predict"
                " which lines would need to change before they edit the code."
            )
        if parsed_code.get("imports"):
            return (
                f"Replace one imported helper with your own implementation and discuss what tradeoff"
                f" that creates for readability versus control."
            )
        return (
            "Change one input, constant, or branch condition in the program and ask students to"
            " predict the new behavior before running it."
        )

    def _default_import_description(
        self,
        imports: List[str],
        profile: LanguageProfile,
    ) -> str:
        preview = ", ".join(line.strip() for line in imports[:2])
        if len(imports) == 1:
            return (
                f"This {profile.import_noun} sets up an external dependency the rest of the program"
                f" expects to use: {preview}."
            )
        return (
            f"These {self._pluralize(profile.import_noun, len(imports))} prepare the outside tools"
            f" the program depends on, including {preview}."
        )

    def _default_function_description(
        self,
        func: Dict[str, Any],
        profile: LanguageProfile,
    ) -> str:
        args = func.get("args") or []
        parts = [f"`{func['name']}` gives students a focused {profile.function_noun} to trace."]
        if args:
            parts.append(
                f"It takes {self._join_with_and([f'`{arg}`' for arg in args])} as input."
            )
        if self._is_recursive(func):
            parts.append("The recursive self-call makes the stopping case especially important.")
        elif "return" in func["body"]:
            parts.append("Students should pay attention to how the returned value is produced.")
        if re.search(r"\bif\b|\bswitch\b|\bmatch\b", func["body"]):
            parts.append("There is a decision point here, so branch tracing matters.")
        return " ".join(parts)

    def _default_class_description(
        self,
        cls: Dict[str, Any],
        profile: LanguageProfile,
    ) -> str:
        kind = cls.get("kind", profile.class_noun)
        methods = cls.get("methods") or []
        if methods:
            method_list = self._join_with_and([f"`{method}`" for method in methods[:3]])
            return (
                f"`{cls['name']}` is a {kind} that groups related behavior together. Students can"
                f" use {method_list} to see how responsibilities are divided inside the type."
            )
        return (
            f"`{cls['name']}` is a {kind} that represents a reusable structure. Ask students what"
            " data or contract it is meant to capture."
        )

    def _default_main_description(
        self,
        code: str,
        profile: LanguageProfile,
    ) -> str:
        calls = self._top_level_calls(code)
        if calls:
            return (
                f"This final section turns the earlier definitions into a real program run by"
                f" calling {self._join_with_and([f'`{call}`' for call in calls[:3]])}."
            )
        return profile.main_code_description

    @staticmethod
    def _ordered_definitions(parsed_code: ParseResult) -> List[tuple[str, Dict[str, Any]]]:
        ordered: List[tuple[int, int, str, Dict[str, Any]]] = []
        fallback_line = 10**9

        for index, func in enumerate(parsed_code.get("functions", [])):
            ordered.append(
                (
                    func.get("source_line", fallback_line + index),
                    index,
                    "function",
                    func,
                )
            )

        function_count = len(parsed_code.get("functions", []))
        for index, cls in enumerate(parsed_code.get("classes", [])):
            ordered.append(
                (
                    cls.get("source_line", fallback_line + function_count + index),
                    function_count + index,
                    "class",
                    cls,
                )
            )

        ordered.sort(key=lambda item: (item[0], item[1]))
        return [(item_type, item) for _, _, item_type, item in ordered]

    def _component_summary(
        self,
        parsed_code: ParseResult,
        profile: LanguageProfile,
    ) -> str:
        parts = []
        if parsed_code.get("imports"):
            parts.append(
                f"{len(parsed_code['imports'])} {self._pluralize(profile.import_noun, len(parsed_code['imports']))}"
            )
        if parsed_code.get("functions"):
            parts.append(
                f"{len(parsed_code['functions'])} {self._pluralize(profile.function_noun, len(parsed_code['functions']))}"
            )
        if parsed_code.get("classes"):
            parts.append(
                f"{len(parsed_code['classes'])} {self._pluralize(profile.class_noun, len(parsed_code['classes']))}"
            )
        if parsed_code.get("main_code"):
            parts.append("a final execution flow")
        return self._join_with_and(parts) or "code-reading only"

    def _estimate_difficulty(
        self,
        parsed_code: ParseResult,
        steps: List[Dict[str, Any]],
    ) -> str:
        score = len(steps) + len(self._concepts(parsed_code))
        if any(self._is_recursive(func) for func in parsed_code.get("functions", [])):
            score += 2
        if parsed_code.get("classes"):
            score += 1
        if score <= 4:
            return "Introductory"
        if score <= 7:
            return "Intermediate"
        return "Advanced"

    @staticmethod
    def _estimate_pacing(steps: List[Dict[str, Any]]) -> str:
        if len(steps) <= 2:
            return "10-15 minutes"
        if len(steps) <= 4:
            return "20-30 minutes"
        return "35-45 minutes"

    def _step_takeaway(self, step: Dict[str, Any]) -> str:
        if step["step_type"] == "imports":
            return f"{step['title']}: students can explain what the program needs before it begins."
        if step["step_type"] == "function":
            return f"{step['title']}: trace the inputs, decisions, and outputs inside `{step['name']}`."
        if step["step_type"] == "class":
            return f"{step['title']}: explain what responsibility `{step['name']}` owns."
        return f"{step['title']}: connect the earlier building blocks into one full execution."

    def _import_key_points(
        self,
        imports: List[str],
        profile: LanguageProfile,
    ) -> List[str]:
        preview = ", ".join(line.strip() for line in imports[:3])
        points = [
            f"Students can identify the external building blocks introduced here: {preview}.",
            "Imports frame the rest of the lesson by naming the tools the program depends on.",
        ]
        if len(imports) > 1:
            points.append(
                "Compare the imports and ask which ones support computation versus input/output."
            )
        return points

    def _function_key_points(
        self,
        step: Dict[str, Any],
        profile: LanguageProfile,
    ) -> List[str]:
        args = step.get("args") or []
        points = []
        if args:
            points.append(f"Inputs to track: {', '.join(f'`{arg}`' for arg in args)}.")
        else:
            points.append(
                f"This {profile.function_noun} takes no explicit inputs, so students can focus on its internal flow."
            )
        if step.get("is_recursive"):
            points.append(
                "It is recursive, so students should trace both the stopping case and the self-call."
            )
        if "return" in step["code"]:
            points.append(
                "It produces a value, so learners can ask what gets returned and when."
            )
        if re.search(r"\bif\b|\bswitch\b|\bmatch\b", step["code"]):
            points.append(
                "There is a decision point here, which makes it a good place to practice branch tracing."
            )
        return points

    def _function_prompts(
        self,
        step: Dict[str, Any],
        profile: LanguageProfile,
    ) -> List[str]:
        args = step.get("args") or []
        prompts = [
            f"What single responsibility does `{step['name']}` have in the larger program?",
        ]
        if args:
            prompts.append(
                f"Which input changes the behavior of `{step['name']}` the most: {', '.join(f'`{arg}`' for arg in args)}?"
            )
        else:
            prompts.append(
                f"What hidden assumptions does `{step['name']}` make when it runs?"
            )
        return prompts

    def _function_practice(self, step: Dict[str, Any]) -> str:
        args = step.get("args") or []
        if args:
            return (
                f"Change one argument to `{step['name']}` and ask students to predict the new"
                " result before running the code."
            )
        return (
            f"Ask students how `{step['name']}` would need to change if it accepted one extra input."
        )

    def _class_key_points(
        self,
        step: Dict[str, Any],
        profile: LanguageProfile,
    ) -> List[str]:
        methods = step.get("methods") or []
        points = []
        if methods:
            points.append(
                f"Methods to track: {', '.join(f'`{method}`' for method in methods)}."
            )
        else:
            points.append(
                "This type is mostly about structure, so students should identify what data or contract it represents."
            )
        if any(token in step["code"] for token in ("self.", "this.", "Host ", "Port ")):
            points.append(
                "It carries state, which makes it useful for discussing how data persists across method calls."
            )
        points.append(
            "Ask what responsibilities belong inside this type and what should stay outside it."
        )
        return points

    def _class_prompts(
        self,
        step: Dict[str, Any],
        profile: LanguageProfile,
    ) -> List[str]:
        prompts = [
            f"What problem does `{step['name']}` solve better as a grouped {profile.class_noun} than as free-standing code?",
        ]
        methods = step.get("methods") or []
        if methods:
            prompts.append(
                f"Which {profile.method_noun} is the best entry point for explaining the behavior of `{step['name']}`?"
            )
        return prompts

    def _class_practice(
        self,
        step: Dict[str, Any],
        profile: LanguageProfile,
    ) -> str:
        return (
            f"Ask students to add one new {profile.method_noun} to `{step['name']}` and explain"
            " what behavior it should own."
        )

    def _main_code_key_points(self, code: str) -> List[str]:
        calls = self._top_level_calls(code)
        points = [
            "This is where the earlier pieces come together into a full program run.",
        ]
        if calls:
            points.append(
                f"Top-level calls worth tracing: {', '.join(f'`{call}`' for call in calls[:4])}."
            )
        points.append(
            "Students should be able to explain this section using the previous steps without rereading every line."
        )
        return points

    def _main_code_prompts(self, code: str) -> List[str]:
        calls = self._top_level_calls(code)
        prompts = ["What happens first, second, and third when this section runs?"]
        if calls:
            prompts.append(
                f"Which earlier definition explains the behavior of `{calls[0]}`?"
            )
        return prompts

    def _concepts(self, parsed_code: ParseResult) -> List[str]:
        concepts: List[str] = []
        functions = parsed_code.get("functions", [])
        if any(self._is_recursive(func) for func in functions):
            concepts.append("recursion")
        if parsed_code.get("classes"):
            concepts.append("state and abstraction")
        if parsed_code.get("imports"):
            concepts.append("dependencies")
        bodies = "\n".join(
            [func["body"] for func in functions]
            + [cls["body"] for cls in parsed_code.get("classes", [])]
            + [parsed_code.get("main_code", "")]
        )
        if re.search(r"\bfor\b|\bwhile\b", bodies):
            concepts.append("iteration")
        if re.search(r"\bif\b|\bswitch\b|\bmatch\b", bodies):
            concepts.append("control flow")
        deduped: List[str] = []
        for concept in concepts:
            if concept not in deduped:
                deduped.append(concept)
        return deduped[:3]

    @staticmethod
    def _is_recursive(func: Dict[str, Any]) -> bool:
        body = func["body"].split("\n", 1)[1] if "\n" in func["body"] else func["body"]
        return re.search(rf"\b{re.escape(func['name'])}\s*\(", body) is not None

    @staticmethod
    def _top_level_calls(code: str) -> List[str]:
        calls = re.findall(r"(?<!\.)\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", code)
        seen: List[str] = []
        for call in calls:
            if call in _NON_TEACHING_CALLS:
                continue
            if call not in seen and call not in {"if", "for", "while", "switch", "match"}:
                seen.append(call)
        return seen

    @staticmethod
    def _pluralize(word: str, count: int) -> str:
        if count == 1:
            return word
        if word.endswith("s"):
            return f"{word}es"
        return f"{word}s"

    @staticmethod
    def _join_with_and(items: List[str]) -> str:
        if not items:
            return ""
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return f"{items[0]} and {items[1]}"
        return ", ".join(items[:-1]) + f", and {items[-1]}"

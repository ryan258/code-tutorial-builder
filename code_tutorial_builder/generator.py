"""Tutorial generator — turns parsed code into pedagogically rich lessons.

The generator uses dependency analysis to order steps so each piece of code
only uses concepts already introduced.  Every step includes transition
narratives, cross-references, predict-the-output exercises, and modification
challenges drawn from the actual code.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader

from .ai import OpenRouterClient, build_openrouter_client
from .analysis import ProgramAnalysis, analyze
from .config import Config
from .languages import get_profile
from .languages._base import LanguageProfile, ParseResult

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

logger = logging.getLogger(__name__)


class TutorialGenerator:
    """Generate tutorials from parsed code."""

    def __init__(self, config: Config, ai_client: Optional[OpenRouterClient] = None):
        self.config = config
        self.ai_client = ai_client
        self.env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            keep_trailing_newline=True,
        )

    def generate(self, parsed_code: ParseResult, title: str = "Code Tutorial") -> str:
        language = parsed_code.get("language", "python")
        profile = get_profile(language)
        graph = analyze(
            parsed_code, profile,
            method_split_threshold=self.config.method_split_threshold,
        )

        steps = self._create_steps(parsed_code, profile, graph)
        if self.config.use_ai:
            steps = self._enhance_steps_with_ai(language, steps)
        steps = [self._decorate_step(step, profile, graph) for step in steps]

        complete_program = self._build_complete_program(parsed_code)
        overview = self._build_overview(parsed_code, profile, steps, graph)
        warm_up = self._build_warm_up(parsed_code, profile, graph)
        vocabulary = self._build_vocabulary(parsed_code, profile, graph)
        learning_goals = self._build_learning_goals(parsed_code, profile, graph)
        teaching_tips = self._build_teaching_tips(parsed_code, profile, graph)
        checks_for_understanding = self._build_checks_for_understanding(steps, graph)
        extension_challenge = self._build_extension_challenge(parsed_code, profile, graph)
        recap_points = self._build_recap_points(steps)
        lesson_stats = self._build_lesson_stats(parsed_code, profile, steps, graph)
        dependency_map = self._build_dependency_map(graph) if graph.has_dependencies else []

        template_name = {
            "handout": "handout.md.j2",
        }.get(self.config.output_format, "default.md.j2")

        if self.config.template:
            template = self.env.from_string(
                Path(self.config.template).read_text(encoding="utf-8")
            )
        else:
            template = self.env.get_template(template_name)

        return template.render(
            title=title,
            steps=steps,
            complete_program=complete_program,
            overview=overview,
            warm_up=warm_up,
            vocabulary=vocabulary,
            learning_goals=learning_goals,
            teaching_tips=teaching_tips,
            checks_for_understanding=checks_for_understanding,
            extension_challenge=extension_challenge,
            recap_points=recap_points,
            lesson_stats=lesson_stats,
            dependency_map=dependency_map,
            code_fence_lang=profile.code_fence_lang,
        )

    # ------------------------------------------------------------------
    # AI enhancement
    # ------------------------------------------------------------------

    def _enhance_steps_with_ai(
        self,
        language: str,
        steps: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
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

    # ------------------------------------------------------------------
    # Step creation — dependency-ordered, incremental
    # ------------------------------------------------------------------

    def _create_steps(
        self,
        parsed_code: ParseResult,
        profile: LanguageProfile,
        graph: ProgramAnalysis,
    ) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []

        # 1. Imports
        if parsed_code.get("imports"):
            steps.append({
                "step_type": "imports",
                "title": profile.import_step_title,
                "description": self._import_description(
                    parsed_code["imports"], profile,
                ),
                "code": "\n".join(parsed_code["imports"]),
                "imports": list(parsed_code["imports"]),
            })

        # 2. Functions and classes in dependency order
        components_by_name: dict[str, tuple[str, dict[str, Any]]] = {}
        for func in parsed_code.get("functions", []):
            components_by_name[func["name"]] = ("function", func)
        for cls in parsed_code.get("classes", []):
            components_by_name[cls["name"]] = ("class", cls)

        for name in graph.dependency_order:
            comp = graph.get_component(name)
            if comp is None:
                continue

            uses = comp.calls
            used_by = comp.called_by

            # --- Split class components (class_intro / method) ---
            if comp.kind == "class_intro":
                cls_name = comp.parent_class or name
                cls_dict = components_by_name.get(cls_name, (None, {}))[1]
                steps.append({
                    "step_type": "class_intro",
                    "name": name,
                    "parent_class": cls_name,
                    "kind_label": cls_dict.get("kind", profile.class_noun),
                    "title": f"Introduce the `{cls_name}` {cls_dict.get('kind', profile.class_noun)}",
                    "description": cls_dict.get("docstring")
                        or self._class_description(cls_dict, profile, uses),
                    "code": comp.body,
                    "methods": list(cls_dict.get("methods") or []),
                    "uses": uses,
                    "used_by": used_by,
                })
                continue

            if comp.kind == "method":
                cls_name = comp.parent_class or ""
                method_name = name.split(".", 1)[-1] if "." in name else name
                # Find the method detail dict for args/docstring
                cls_dict = components_by_name.get(cls_name, (None, {}))[1]
                method_detail = self._find_method_detail(cls_dict, method_name)
                args = [a for a in (method_detail.get("args") or []) if a not in ("self", "cls")]
                steps.append({
                    "step_type": "method",
                    "name": name,
                    "display_name": method_name,
                    "parent_class": cls_name,
                    "title": f"Define `{cls_name}.{method_name}`",
                    "description": method_detail.get("docstring")
                        or self._method_description(method_name, cls_name, args, profile, uses),
                    "code": comp.body,
                    "args": args,
                    "is_recursive": bool(re.search(
                        rf"self\.{re.escape(method_name)}\s*\(", comp.body,
                    )),
                    "uses": uses,
                    "used_by": used_by,
                })
                continue

            # --- Original function / class handling ---
            if name not in components_by_name:
                continue
            kind, item = components_by_name[name]

            if kind == "function":
                steps.append({
                    "step_type": "function",
                    "name": item["name"],
                    "title": f"Define `{item['name']}`",
                    "description": item.get("docstring")
                        or self._function_description(item, profile, uses),
                    "code": item["body"],
                    "args": list(item.get("args") or []),
                    "is_recursive": self._is_recursive(item),
                    "uses": uses,
                    "used_by": used_by,
                })
            else:
                kind_label = item.get("kind", profile.class_noun)
                steps.append({
                    "step_type": "class",
                    "name": item["name"],
                    "kind_label": kind_label,
                    "title": f"Define the `{item['name']}` {kind_label}",
                    "description": item.get("docstring")
                        or self._class_description(item, profile, uses),
                    "code": item["body"],
                    "methods": list(item.get("methods") or []),
                    "uses": uses,
                    "used_by": used_by,
                })

        # 3. Budget enforcement (keep room for main step)
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

        # 4. Main code
        if has_main:
            main_kind = self._classify_main_code(
                parsed_code["main_code"], profile, graph,
            )
            if main_kind == "setup":
                main_title = "Module Setup"
                main_desc = (
                    "These module-level statements configure the runtime"
                    " environment before the main logic runs."
                )
            else:
                main_title = profile.main_code_title
                main_desc = self._main_description(
                    parsed_code["main_code"], profile,
                )
            steps.append({
                "step_type": "main",
                "title": main_title,
                "description": main_desc,
                "code": parsed_code["main_code"],
            })

        return steps

    # ------------------------------------------------------------------
    # Step decoration — add pedagogy, transitions, exercises
    # ------------------------------------------------------------------

    def _decorate_step(
        self,
        step: dict[str, Any],
        profile: LanguageProfile,
        graph: ProgramAnalysis,
    ) -> dict[str, Any]:
        if step["step_type"] == "imports":
            return {
                **step,
                "transition": None,
                "spotlight": (
                    "These lines bring in the outside tools the program relies on"
                    " before any of the core logic begins."
                ),
                "key_points": self._import_key_points(step["imports"], profile),
                "prompts": [
                    f"Which {profile.import_noun} is most important for the rest of the file?",
                    "What would break first if one of these disappeared?",
                ],
                "predict_exercise": self._import_predict(step["imports"], profile),
                "modify_exercise": (
                    f"Remove one {profile.import_noun} and predict which line will"
                    " fail first."
                ),
                "practice": (
                    f"Ask students to find where each {profile.import_noun} is first"
                    " used later in the lesson."
                ),
            }

        if step["step_type"] == "function":
            return {
                **step,
                "transition": self._function_transition(step, profile),
                "spotlight": self._function_spotlight(step, profile),
                "key_points": self._function_key_points(step, profile),
                "prompts": self._function_prompts(step, profile),
                "predict_exercise": self._function_predict(step, profile),
                "modify_exercise": self._function_modify(step, profile),
                "practice": self._function_practice(step),
            }

        if step["step_type"] == "class":
            return {
                **step,
                "transition": self._class_transition(step, profile),
                "spotlight": (
                    f"`{step['name']}` bundles related data and behavior into one"
                    f" reusable {step['kind_label']}."
                ),
                "key_points": self._class_key_points(step, profile),
                "prompts": self._class_prompts(step, profile),
                "predict_exercise": self._class_predict(step, profile),
                "modify_exercise": self._class_modify(step, profile),
                "practice": self._class_practice(step, profile),
            }

        if step["step_type"] == "class_intro":
            cls_name = step.get("parent_class", step["name"])
            # Use parent class name for the transition text
            intro_step = {**step, "name": cls_name}
            return {
                **step,
                "transition": self._class_transition(intro_step, profile),
                "spotlight": (
                    f"`{cls_name}` bundles related data and behavior into one"
                    f" reusable {step.get('kind_label', profile.class_noun)}."
                    f" We start with its constructor."
                ),
                "key_points": self._class_intro_key_points(step, profile),
                "prompts": self._class_prompts(intro_step, profile),
                "predict_exercise": self._class_intro_predict(step, profile),
                "modify_exercise": (
                    f"Add or change one attribute in `{cls_name}.__init__`."
                    f" What other methods would need to change?"
                ),
                "practice": (
                    f"Ask students to create an instance of `{cls_name}`"
                    f" and inspect its initial attributes."
                ),
            }

        if step["step_type"] == "method":
            return {
                **step,
                "transition": self._method_transition(step, profile),
                "spotlight": self._method_spotlight(step, profile),
                "key_points": self._function_key_points(step, profile),
                "prompts": self._method_prompts(step, profile),
                "predict_exercise": self._method_predict(step, profile),
                "modify_exercise": self._method_modify(step, profile),
                "practice": self._function_practice(step),
            }

        # main step
        main_kind = self._classify_main_code(step["code"], profile, graph)
        if main_kind == "setup":
            return {
                **step,
                "transition": (
                    "Before the main logic runs, these module-level"
                    " statements configure the runtime environment."
                ),
                "spotlight": (
                    "This is setup code, not orchestration — it prepares"
                    " the environment so the classes and functions above"
                    " work correctly at runtime."
                ),
                "key_points": [
                    "This is configuration, not behavior — it prepares"
                    " the environment for the logic defined above.",
                    "Trace each assignment or call to understand what"
                    " state it creates.",
                ],
                "prompts": [
                    "What would go wrong if this setup code were missing?",
                    "Is this configuration or behavior?",
                ],
                "predict_exercise": (
                    "What state does this setup code create? Trace each"
                    " assignment or configuration call."
                ),
                "modify_exercise": (
                    "Change one configuration value and predict how the"
                    " program's behavior changes."
                ),
                "practice": (
                    "Ask students to identify which earlier components"
                    " depend on this setup being in place."
                ),
            }

        return {
            **step,
            "transition": self._main_transition(step, profile, graph),
            "spotlight": (
                "This is the orchestration step where the earlier building blocks"
                " run together as a complete program."
            ),
            "key_points": self._main_key_points(step["code"], profile),
            "prompts": self._main_prompts(step["code"], profile),
            "predict_exercise": self._main_predict(step["code"], profile),
            "modify_exercise": (
                "Change one input value and predict the new output before running it."
            ),
            "practice": (
                "Before running this section, ask students to predict the order"
                " of calls, outputs, or state changes."
            ),
        }

    # ------------------------------------------------------------------
    # Transition narratives
    # ------------------------------------------------------------------

    def _function_transition(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> str:
        uses = step.get("uses", [])
        if uses:
            deps = self._join_with_and([f"`{u}`" for u in uses])
            return (
                f"With {deps} available, we can now define `{step['name']}`"
                f" which builds on {'it' if len(uses) == 1 else 'them'}."
            )
        return (
            f"This {profile.function_noun} has no dependencies on other parts"
            f" of the program, so it is a natural starting point."
        )

    def _class_transition(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> str:
        uses = step.get("uses", [])
        if uses:
            deps = self._join_with_and([f"`{u}`" for u in uses])
            return (
                f"Now that {deps} {'is' if len(uses) == 1 else 'are'} defined,"
                f" we can build the `{step['name']}` {step['kind_label']}"
                f" that relies on {'it' if len(uses) == 1 else 'them'}."
            )
        return (
            f"This {step['kind_label']} is self-contained, making it a clean"
            f" building block to introduce next."
        )

    def _method_transition(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> str:
        cls_name = step.get("parent_class", "")
        method_name = step.get("display_name", step["name"])
        uses = step.get("uses", [])
        if uses:
            deps = self._join_with_and([
                f"`{u.split('.')[-1]}`" if "." in u else f"`{u}`"
                for u in uses
            ])
            return (
                f"Continuing to build out `{cls_name}`, we define"
                f" `{method_name}` which uses {deps}."
            )
        return (
            f"Next we add `{method_name}` to `{cls_name}`."
        )

    def _main_transition(
        self,
        step: dict[str, Any],
        profile: LanguageProfile,
        graph: ProgramAnalysis,
    ) -> str:
        names = [c.name for c in graph.components]
        if graph.has_dependencies and names:
            pieces = self._join_with_and([f"`{n}`" for n in names[:3]])
            return (
                f"Every piece is in place. This final section connects"
                f" {pieces} into a working program."
            )
        return "With all the definitions ready, we can now run the program."

    # ------------------------------------------------------------------
    # Descriptions
    # ------------------------------------------------------------------

    def _import_description(
        self, imports: list[str], profile: LanguageProfile,
    ) -> str:
        preview = ", ".join(line.strip() for line in imports[:2])
        if len(imports) == 1:
            return (
                f"This {profile.import_noun} brings in an external dependency"
                f" the rest of the program needs: {preview}."
            )
        return (
            f"These {self._pluralize(profile.import_noun, len(imports))} prepare"
            f" the outside tools the program depends on, including {preview}."
        )

    def _function_description(
        self,
        func: dict[str, Any],
        profile: LanguageProfile,
        uses: list[str],
    ) -> str:
        args = func.get("args") or []
        parts: list[str] = []
        if args:
            arg_list = self._join_with_and([f"`{a}`" for a in args])
            parts.append(
                f"`{func['name']}` takes {arg_list} as"
                f" {'input' if len(args) == 1 else 'inputs'}."
            )
        else:
            parts.append(
                f"`{func['name']}` takes no explicit inputs."
            )

        if self._is_recursive(func):
            parts.append(
                "It calls itself recursively, so the base case is critical."
            )
        elif "return" in func["body"]:
            parts.append("Pay attention to what it returns and when.")

        if uses:
            dep_list = self._join_with_and([f"`{u}`" for u in uses])
            parts.append(f"It relies on {dep_list} defined earlier.")

        return " ".join(parts)

    def _class_description(
        self,
        cls: dict[str, Any],
        profile: LanguageProfile,
        uses: list[str],
    ) -> str:
        kind = cls.get("kind", profile.class_noun)
        methods = cls.get("methods") or []
        if methods:
            method_list = self._join_with_and([f"`{m}`" for m in methods[:3]])
            base = (
                f"`{cls['name']}` is a {kind} with"
                f" {method_list} defining its behavior."
            )
        else:
            base = (
                f"`{cls['name']}` is a {kind} that captures a reusable structure."
            )
        if uses:
            dep_list = self._join_with_and([f"`{u}`" for u in uses])
            base += f" Internally it uses {dep_list}."
        return base

    def _method_description(
        self,
        method_name: str,
        class_name: str,
        args: list[str],
        profile: LanguageProfile,
        uses: list[str],
    ) -> str:
        parts: list[str] = []
        if args:
            arg_list = self._join_with_and([f"`{a}`" for a in args])
            parts.append(
                f"`{class_name}.{method_name}` takes {arg_list} as"
                f" {'input' if len(args) == 1 else 'inputs'}."
            )
        else:
            parts.append(
                f"`{class_name}.{method_name}` takes no explicit inputs"
                f" beyond the instance."
            )
        if uses:
            dep_names = [u.split(".")[-1] if "." in u else u for u in uses]
            dep_list = self._join_with_and([f"`{d}`" for d in dep_names])
            parts.append(f"It relies on {dep_list}.")
        return " ".join(parts)

    def _main_description(self, code: str, profile: LanguageProfile) -> str:
        calls = self._top_level_calls(code, profile)
        if calls:
            return (
                f"The program runs by calling"
                f" {self._join_with_and([f'`{c}`' for c in calls[:3]])},"
                f" connecting the earlier definitions into a real result."
            )
        return profile.main_code_description

    # ------------------------------------------------------------------
    # Spotlight
    # ------------------------------------------------------------------

    def _function_spotlight(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> str:
        if step.get("is_recursive"):
            return (
                f"`{step['name']}` calls itself, so the key question is:"
                f" where does the recursion stop?"
            )
        args = step.get("args") or []
        if args:
            return (
                f"Focus on how `{step['name']}` transforms"
                f" {'its input' if len(args) == 1 else 'its inputs'}"
                f" into a result."
            )
        return (
            f"Focus on the internal logic of `{step['name']}` and what"
            f" effect it produces."
        )

    def _method_spotlight(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> str:
        cls_name = step.get("parent_class", "")
        method_name = step.get("display_name", step["name"])
        if step.get("is_recursive"):
            return (
                f"`{cls_name}.{method_name}` calls itself, so the key"
                f" question is: where does the recursion stop?"
            )
        args = step.get("args") or []
        if args:
            return (
                f"Focus on how `{method_name}` transforms"
                f" {'its input' if len(args) == 1 else 'its inputs'}"
                f" and what it does with the instance state."
            )
        return (
            f"Focus on what `{method_name}` does with the instance state"
            f" and what effect it produces."
        )

    # ------------------------------------------------------------------
    # Key points
    # ------------------------------------------------------------------

    def _import_key_points(
        self, imports: list[str], profile: LanguageProfile,
    ) -> list[str]:
        preview = ", ".join(line.strip() for line in imports[:3])
        points = [
            f"External building blocks introduced here: {preview}.",
            f"These {self._pluralize(profile.import_noun, len(imports))} frame"
            " everything that follows.",
        ]
        if len(imports) > 1:
            points.append(
                "Compare them: which support computation versus input/output?"
            )
        return points

    def _function_key_points(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> list[str]:
        args = step.get("args") or []
        points: list[str] = []
        if args:
            points.append(
                f"Inputs: {', '.join(f'`{a}`' for a in args)}."
            )
        else:
            points.append("No explicit inputs — focus on the internal flow.")

        if step.get("is_recursive"):
            points.append("Recursive — trace both the base case and the self-call.")

        if "return" in step["code"]:
            points.append("Returns a value — ask what and when.")

        kw_pattern = r"\b(if|switch|match)\b"
        if re.search(kw_pattern, step["code"]):
            points.append("Contains a decision point — good for branch tracing.")

        uses = step.get("uses", [])
        if uses:
            points.append(
                f"Depends on: {self._join_with_and([f'`{u}`' for u in uses])}."
            )

        used_by = step.get("used_by", [])
        if used_by:
            points.append(
                f"Used later by: {self._join_with_and([f'`{u}`' for u in used_by])}."
            )

        return points

    def _class_key_points(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> list[str]:
        methods = step.get("methods") or []
        points: list[str] = []
        if methods:
            points.append(
                f"Methods: {', '.join(f'`{m}`' for m in methods)}."
            )
        else:
            points.append(
                "Mostly about structure — identify what data or contract it represents."
            )

        if profile.state_tokens and any(
            tok in step["code"] for tok in profile.state_tokens
        ):
            points.append("Carries state that persists across method calls.")

        uses = step.get("uses", [])
        if uses:
            points.append(
                f"Depends on: {self._join_with_and([f'`{u}`' for u in uses])}."
            )

        points.append(
            "Ask what responsibilities belong inside this type and what should stay outside."
        )
        return points

    def _class_intro_key_points(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> list[str]:
        cls_name = step.get("parent_class", step["name"])
        methods = step.get("methods") or []
        points: list[str] = []
        if methods:
            points.append(
                f"Full method list: {', '.join(f'`{m}`' for m in methods)}."
                f" We will cover them one by one."
            )
        if profile.state_tokens and any(
            tok in step["code"] for tok in profile.state_tokens
        ):
            points.append(
                f"The constructor sets up state that the other methods will read and modify."
            )
        uses = step.get("uses", [])
        if uses:
            points.append(
                f"Depends on: {self._join_with_and([f'`{u}`' for u in uses])}."
            )
        points.append(
            f"This step introduces the class — the methods follow in the next steps."
        )
        return points

    def _main_key_points(self, code: str, profile: LanguageProfile) -> list[str]:
        calls = self._top_level_calls(code, profile)
        points = [
            "This is where the earlier pieces come together into a full program run.",
        ]
        if calls:
            points.append(
                f"Calls to trace: {', '.join(f'`{c}`' for c in calls[:4])}."
            )
        points.append(
            "Students should be able to explain this section using the previous steps."
        )
        return points

    # ------------------------------------------------------------------
    # Discussion prompts
    # ------------------------------------------------------------------

    def _function_prompts(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> list[str]:
        args = step.get("args") or []
        prompts = [
            f"What single job does `{step['name']}` do for the rest of the program?",
        ]
        if args:
            prompts.append(
                f"Which input changes the behavior of `{step['name']}` the most:"
                f" {', '.join(f'`{a}`' for a in args)}?"
            )
        if step.get("used_by"):
            prompts.append(
                f"What would break if `{step['name']}` returned a different type?"
            )
        return prompts

    def _class_prompts(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> list[str]:
        prompts = [
            f"What problem does `{step['name']}` solve better as a"
            f" {step.get('kind_label', profile.class_noun)} than as loose code?",
        ]
        methods = step.get("methods") or []
        if methods:
            prompts.append(
                f"Which {profile.method_noun} is the best starting point for"
                f" understanding `{step['name']}`?"
            )
        return prompts

    def _method_prompts(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> list[str]:
        cls_name = step.get("parent_class", "")
        method_name = step.get("display_name", step["name"])
        prompts = [
            f"What single job does `{method_name}` do for `{cls_name}`?",
        ]
        args = step.get("args") or []
        if args:
            prompts.append(
                f"Which input changes the behavior of `{method_name}` the most:"
                f" {', '.join(f'`{a}`' for a in args)}?"
            )
        uses = step.get("uses", [])
        if uses:
            dep_names = [u.split(".")[-1] if "." in u else u for u in uses]
            prompts.append(
                f"Why does `{method_name}` call"
                f" {self._join_with_and([f'`{d}`' for d in dep_names])}?"
            )
        return prompts

    def _main_prompts(self, code: str, profile: LanguageProfile) -> list[str]:
        calls = self._top_level_calls(code, profile)
        prompts = ["What happens first, second, and third when this section runs?"]
        if calls:
            prompts.append(
                f"Which earlier definition explains the behavior of `{calls[0]}`?"
            )
        return prompts

    # ------------------------------------------------------------------
    # Exercises — predict & modify
    # ------------------------------------------------------------------

    def _import_predict(
        self, imports: list[str], profile: LanguageProfile,
    ) -> str:
        if len(imports) == 1:
            return (
                f"If this {profile.import_noun} were missing, which line"
                " would fail first?"
            )
        return (
            f"If you removed the last {profile.import_noun}, which later line"
            " would be the first to fail?"
        )

    def _function_predict(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> str:
        args = step.get("args") or []
        if step.get("is_recursive") and args:
            return (
                f"Trace `{step['name']}({args[0]}=3)` by hand."
                f" How many times does it call itself before returning?"
            )
        if args:
            return (
                f"Pick a simple value for"
                f" `{args[0]}` and predict what `{step['name']}` returns."
            )
        return f"What does `{step['name']}()` produce when called?"

    def _function_modify(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> str:
        if step.get("is_recursive"):
            return (
                f"Change the base case in `{step['name']}`. What happens"
                " to the recursion?"
            )
        args = step.get("args") or []
        if args:
            return (
                f"Add a new parameter to `{step['name']}` and predict what"
                " else needs to change."
            )
        return (
            f"Make `{step['name']}` accept one input it currently does not."
            " What would you pass in?"
        )

    def _class_intro_predict(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> str:
        cls_name = step.get("parent_class", step["name"])
        return (
            f"After creating an instance of `{cls_name}`, what state"
            f" does it hold? List each attribute and its initial value."
        )

    def _class_predict(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> str:
        methods = step.get("methods") or []
        # Pick the first non-dunder method for a more interesting exercise
        interesting = [m for m in methods if not m.startswith("__")]
        if interesting:
            return (
                f"Create an instance of `{step['name']}` and call"
                f" `{interesting[0]}` with a simple input."
                f" What does it return?"
            )
        if methods:
            return (
                f"After creating an instance of `{step['name']}`,"
                f" what state does it hold? Inspect its attributes."
            )
        return f"What data does a new `{step['name']}` instance start with?"

    def _method_predict(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> str:
        args = step.get("args") or []
        method_name = step.get("display_name", step["name"])
        cls_name = step.get("parent_class", "")
        if step.get("is_recursive") and args:
            return (
                f"Trace `{cls_name}.{method_name}({args[0]}=3)` by hand."
                f" How many times does it call itself?"
            )
        if args:
            return (
                f"Pick a simple value for `{args[0]}` and predict"
                f" what `{method_name}` returns."
            )
        return (
            f"Call `{method_name}` on an instance and predict what"
            f" it returns or how it changes the object's state."
        )

    def _method_modify(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> str:
        method_name = step.get("display_name", step["name"])
        args = step.get("args") or []
        if args:
            return (
                f"Add a new parameter to `{method_name}` and predict"
                f" what else needs to change."
            )
        return (
            f"Make `{method_name}` accept one input it currently does not."
            f" What would you pass in?"
        )

    def _class_modify(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> str:
        return (
            f"Add one new {profile.method_noun} to `{step['name']}` that"
            " would make it more useful. Justify why that behavior belongs here."
        )

    def _main_predict(self, code: str, profile: LanguageProfile) -> str:
        calls = self._top_level_calls(code, profile)
        if calls:
            return (
                f"Before running, predict the output of the `{calls[0]}`"
                " call in this section."
            )
        return "Before running, write down what you expect the output to be."

    # ------------------------------------------------------------------
    # Practice / hands-on
    # ------------------------------------------------------------------

    def _function_practice(self, step: dict[str, Any]) -> str:
        args = step.get("args") or []
        if args:
            return (
                f"Change one argument to `{step['name']}` and predict the"
                " new result before running the code."
            )
        return (
            f"Ask students how `{step['name']}` would need to change"
            " if it accepted one extra input."
        )

    def _class_practice(
        self, step: dict[str, Any], profile: LanguageProfile,
    ) -> str:
        return (
            f"Ask students to add one new {profile.method_noun} to"
            f" `{step['name']}` and explain what behavior it should own."
        )

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def _build_complete_program(self, parsed_code: ParseResult) -> str:
        source = parsed_code.get("source")
        if source is not None:
            return source.rstrip("\n")

        parts: list[str] = []
        if parsed_code.get("imports"):
            parts.append("\n".join(parsed_code["imports"]))
        for func in parsed_code.get("functions", []):
            parts.append(func["body"])
        for cls in parsed_code.get("classes", []):
            parts.append(cls["body"])
        if parsed_code.get("main_code"):
            parts.append(parsed_code["main_code"])
        return "\n\n".join(parts)

    def _build_overview(
        self,
        parsed_code: ParseResult,
        profile: LanguageProfile,
        steps: list[dict[str, Any]],
        graph: ProgramAnalysis,
    ) -> str:
        component_text = self._component_summary(parsed_code, profile)
        concept_text = self._join_with_and(graph.concepts)

        if component_text != "code-reading only":
            base = (
                f"This {profile.display_name} lesson builds the program"
                f" step by step across {len(steps)}"
                f" teaching {'step' if len(steps) == 1 else 'steps'},"
                f" covering {component_text}."
            )
        else:
            base = (
                f"This {profile.display_name} lesson focuses on reading"
                " the code carefully and explaining how each section"
                " contributes to the whole program."
            )

        if concept_text:
            return f"{base} Along the way, students will encounter {concept_text}."
        return base

    def _build_warm_up(
        self,
        parsed_code: ParseResult,
        profile: LanguageProfile,
        graph: ProgramAnalysis,
    ) -> str:
        if "recursion" in graph.concepts:
            return (
                "Ask students what has to be true for a recursive call to stop,"
                " then have them predict where that stopping case appears."
            )
        if parsed_code.get("classes"):
            return (
                f"Ask why someone might choose a {profile.class_noun} instead"
                " of scattered variables and helper code for this problem."
            )
        if parsed_code.get("imports"):
            noun = self._pluralize(
                profile.import_noun, len(parsed_code["imports"]),
            )
            return (
                f"Ask students what this program would have to build from"
                f" scratch if these {noun} were missing."
            )
        if parsed_code.get("functions"):
            noun = self._pluralize(
                profile.function_noun, len(parsed_code["functions"]),
            )
            return (
                f"Ask students why breaking a problem into separate {noun}"
                " makes a program easier to understand and debug."
            )
        return (
            "Ask students to scan the file for the first line that changes"
            " state or produces output, then explain why that line matters."
        )

    def _build_vocabulary(
        self,
        parsed_code: ParseResult,
        profile: LanguageProfile,
        graph: ProgramAnalysis,
    ) -> list[str]:
        vocab: list[str] = []
        if parsed_code.get("imports"):
            vocab.append(
                f"`{profile.import_noun}`: code this file pulls in before"
                " the main logic starts."
            )
        if parsed_code.get("functions"):
            vocab.append("`parameter`: a named input a function receives.")
            vocab.append(
                "`return value`: the result a function gives back to its caller."
            )
        if parsed_code.get("classes"):
            vocab.append(
                f"`{profile.class_noun}`: a reusable unit that groups"
                " related data and behavior."
            )
            vocab.append(
                f"`{profile.method_noun}`: a behavior that belongs to a"
                f" specific {profile.class_noun}."
            )
            vocab.append("`state`: information an object keeps between actions.")

        if "recursion" in graph.concepts:
            vocab.append(
                "`recursion`: solving a problem by calling the same function"
                " on a smaller case."
            )
        if "iteration" in graph.concepts:
            vocab.append("`iteration`: repeating work with a loop.")
        if "control flow" in graph.concepts:
            vocab.append(
                "`control flow`: the decisions that determine which lines"
                " run next."
            )
        if "error handling" in graph.concepts:
            vocab.append(
                "`error handling`: detecting and responding to problems at runtime."
            )

        return list(dict.fromkeys(vocab))[:8]

    def _build_learning_goals(
        self,
        parsed_code: ParseResult,
        profile: LanguageProfile,
        graph: ProgramAnalysis,
    ) -> list[str]:
        goals: list[str] = []
        if parsed_code.get("imports"):
            goals.append(
                f"Explain why each {profile.import_noun} appears before"
                " the main logic begins."
            )
        if parsed_code.get("functions"):
            goals.append(
                f"Trace how each {profile.function_noun} uses inputs,"
                " decisions, and return values."
            )
        if parsed_code.get("classes"):
            goals.append(
                f"Describe how each {profile.class_noun} groups"
                " responsibilities and manages state."
            )
        if graph.has_dependencies:
            goals.append(
                "Explain how components depend on one another by following"
                " the call chain."
            )
        if parsed_code.get("main_code"):
            goals.append(
                "Connect the supporting definitions to the final execution flow."
            )
        if not goals:
            goals.append(
                "Read unfamiliar code methodically and explain what happens"
                " in each section."
            )
        return goals[:5]

    def _build_teaching_tips(
        self,
        parsed_code: ParseResult,
        profile: LanguageProfile,
        graph: ProgramAnalysis,
    ) -> list[str]:
        tips = [
            "Ask students to predict what the code will do before you"
            " reveal the explanation or run it.",
            "Have learners annotate where data enters, changes, and leaves"
            " the program.",
            "Pause after each step and connect it back to the overall goal.",
        ]
        if "recursion" in graph.concepts:
            tips.append(
                "For recursion, trace one concrete call stack on paper and"
                " mark the stopping case before running the code."
            )
        if parsed_code.get("classes"):
            tips.append(
                f"Separate what the {profile.class_noun} knows (state)"
                f" from what it does ({profile.method_noun}s) so"
                " object-oriented structure feels less abstract."
            )
        if graph.has_dependencies:
            tips.append(
                "Use the dependency map to show students the order in which"
                " pieces build on each other."
            )
        if parsed_code.get("main_code"):
            tips.append(
                "Use the final execution step as a recap: students should"
                " be able to explain every call it makes."
            )
        return tips[:6]

    def _build_checks_for_understanding(
        self,
        steps: list[dict[str, Any]],
        graph: ProgramAnalysis,
    ) -> list[str]:
        questions = [
            "Where does data enter the program, and where does it leave?",
            "Which step would you revisit first if the final output were wrong?",
        ]
        first_named = next(
            (s for s in steps if s["step_type"] in {"function", "class", "class_intro", "method"}),
            None,
        )
        if first_named is not None:
            questions.insert(
                0,
                f"What essential job would disappear if"
                f" `{first_named['name']}` were removed?",
            )

        if graph.has_dependencies:
            questions.append(
                "Trace the dependency chain from the first function to the"
                " last. What order do they need to be called in?"
            )

        if any(s["step_type"] == "main" for s in steps):
            questions.append(
                "Which earlier definition does the final execution step"
                " rely on first?"
            )
        return questions[:5]

    def _build_extension_challenge(
        self,
        parsed_code: ParseResult,
        profile: LanguageProfile,
        graph: ProgramAnalysis,
    ) -> str:
        if "recursion" in graph.concepts:
            return (
                "Rewrite the recursive logic iteratively, then compare"
                " which version is easier to explain and why."
            )
        if parsed_code.get("classes"):
            first_class = parsed_code["classes"][0]["name"]
            return (
                f"Add one new {profile.method_noun} to `{first_class}`"
                " that makes the type more useful, and justify why"
                " that behavior belongs there."
            )
        functions = parsed_code.get("functions", [])
        if functions:
            first_func = functions[0]["name"]
            return (
                f"Modify `{first_func}` to handle one new edge case,"
                " and predict which lines need to change before editing."
            )
        if parsed_code.get("imports"):
            return (
                "Replace one imported helper with your own implementation"
                " and discuss the tradeoff for readability versus control."
            )
        return (
            "Change one input, constant, or branch condition and predict"
            " the new behavior before running it."
        )

    def _build_recap_points(self, steps: list[dict[str, Any]]) -> list[str]:
        return [self._step_takeaway(s) for s in steps[:5]]

    def _build_lesson_stats(
        self,
        parsed_code: ParseResult,
        profile: LanguageProfile,
        steps: list[dict[str, Any]],
        graph: ProgramAnalysis,
    ) -> list[str]:
        return [
            f"Language: {profile.display_name}",
            f"Suggested level: {self._estimate_difficulty(parsed_code, steps, graph)}",
            f"Estimated pacing: {self._estimate_pacing(steps)}",
            f"Lesson steps: {len(steps)}",
            f"Components covered: {self._component_summary(parsed_code, profile)}",
            f"Core concepts: {self._join_with_and(graph.concepts) or 'program flow'}",
        ]

    def _build_dependency_map(self, graph: ProgramAnalysis) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for comp in graph.components:
            rows.append({
                "name": comp.name,
                "kind": comp.kind,
                "uses": self._join_with_and([f"`{u}`" for u in comp.calls]) or "---",
                "used_by": self._join_with_and(
                    [f"`{u}`" for u in comp.called_by]
                ) or "---",
            })
        return rows

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _component_summary(
        self, parsed_code: ParseResult, profile: LanguageProfile,
    ) -> str:
        parts: list[str] = []
        if parsed_code.get("imports"):
            n = len(parsed_code["imports"])
            parts.append(f"{n} {self._pluralize(profile.import_noun, n)}")
        if parsed_code.get("functions"):
            n = len(parsed_code["functions"])
            parts.append(f"{n} {self._pluralize(profile.function_noun, n)}")
        if parsed_code.get("classes"):
            n = len(parsed_code["classes"])
            parts.append(f"{n} {self._pluralize(profile.class_noun, n)}")
        if parsed_code.get("main_code"):
            parts.append("a final execution flow")
        return self._join_with_and(parts) or "code-reading only"

    def _estimate_difficulty(
        self,
        parsed_code: ParseResult,
        steps: list[dict[str, Any]],
        graph: ProgramAnalysis,
    ) -> str:
        score = len(steps) + len(graph.concepts)
        if "recursion" in graph.concepts:
            score += 2
        if "error handling" in graph.concepts:
            score += 1
        if parsed_code.get("classes"):
            score += 1
        if score <= 4:
            return "Introductory"
        if score <= 7:
            return "Intermediate"
        return "Advanced"

    @staticmethod
    def _estimate_pacing(steps: list[dict[str, Any]]) -> str:
        if len(steps) <= 2:
            return "10-15 minutes"
        if len(steps) <= 4:
            return "20-30 minutes"
        return "35-45 minutes"

    def _classify_main_code(
        self,
        code: str,
        profile: LanguageProfile,
        graph: ProgramAnalysis,
    ) -> str:
        """Classify main code as 'orchestration' or 'setup'."""
        calls = self._top_level_calls(code, profile)
        defined = {c.name for c in graph.components}
        # Also accept the class name from dotted method names
        for c in graph.components:
            if c.parent_class:
                defined.add(c.parent_class)
        if any(c in defined for c in calls):
            return "orchestration"
        return "setup"

    @staticmethod
    def _find_method_detail(cls_dict: dict, method_name: str) -> dict:
        """Find a method's detail dict inside a class's method_details."""
        for md in cls_dict.get("method_details", []):
            if md["name"] == method_name:
                return md
        return {}

    def _step_takeaway(self, step: dict[str, Any]) -> str:
        if step["step_type"] == "imports":
            return (
                f"{step['title']}: students can explain what the program"
                " needs before it begins."
            )
        if step["step_type"] == "function":
            return (
                f"{step['title']}: trace the inputs, decisions, and outputs"
                f" inside `{step['name']}`."
            )
        if step["step_type"] == "class":
            return (
                f"{step['title']}: explain what responsibility"
                f" `{step['name']}` owns."
            )
        if step["step_type"] == "class_intro":
            cls_name = step.get("parent_class", step["name"])
            return (
                f"{step['title']}: explain what `{cls_name}` is for"
                f" and what state it starts with."
            )
        if step["step_type"] == "method":
            return (
                f"{step['title']}: trace inputs, logic, and state"
                f" changes inside this method."
            )
        return (
            f"{step['title']}: connect the earlier building blocks"
            " into one full execution."
        )

    @staticmethod
    def _is_recursive(func: dict[str, Any]) -> bool:
        body = func["body"]
        lines = body.split("\n")
        search_text = "\n".join(lines[1:]) if len(lines) > 1 else ""
        return re.search(
            rf"\b{re.escape(func['name'])}\s*\(", search_text,
        ) is not None

    def _top_level_calls(self, code: str, profile: LanguageProfile) -> list[str]:
        builtins = set(profile.builtin_calls)
        noise = {"if", "for", "while", "switch", "match", "else", "elif", "case"}
        calls = re.findall(r"(?<!\.)\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", code)
        seen: list[str] = []
        for call in calls:
            if call in builtins or call in noise:
                continue
            if call not in seen:
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
    def _join_with_and(items: list[str]) -> str:
        if not items:
            return ""
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return f"{items[0]} and {items[1]}"
        return ", ".join(items[:-1]) + f", and {items[-1]}"

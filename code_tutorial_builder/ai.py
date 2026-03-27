from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3-nano-30b-a3b:free"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class OpenRouterSettings:
    api_key: str
    model: str = DEFAULT_OPENROUTER_MODEL
    base_url: str = DEFAULT_OPENROUTER_BASE_URL
    app_name: str = "code-tutorial-builder"
    site_url: Optional[str] = None


def build_openrouter_client(search_path: Optional[str] = None) -> Optional["OpenRouterClient"]:
    """Create an OpenRouter client if credentials are configured."""
    settings = load_openrouter_settings(search_path=search_path)
    if settings is None:
        return None
    return OpenRouterClient(settings)


def load_openrouter_settings(
    search_path: Optional[str] = None,
    env_file: Optional[str] = None,
) -> Optional[OpenRouterSettings]:
    """Load OpenRouter settings from environment or a nearby .env file."""
    env_values: Dict[str, str] = {}
    if env_file is not None:
        env_path = Path(env_file)
        if env_path.is_file():
            env_values = _read_env_file(env_path)
    else:
        discovered = _find_env_file(search_path=search_path)
        if discovered is not None:
            env_values = _read_env_file(discovered)

    api_key = os.environ.get("OPENROUTER_API_KEY") or env_values.get("OPENROUTER_API_KEY")
    if not api_key:
        return None

    return OpenRouterSettings(
        api_key=api_key,
        model=os.environ.get("OPENROUTER_MODEL")
        or env_values.get("OPENROUTER_MODEL")
        or DEFAULT_OPENROUTER_MODEL,
        base_url=(
            os.environ.get("OPENROUTER_BASE_URL")
            or env_values.get("OPENROUTER_BASE_URL")
            or DEFAULT_OPENROUTER_BASE_URL
        ).rstrip("/"),
        app_name=os.environ.get("OPENROUTER_APP_NAME")
        or env_values.get("OPENROUTER_APP_NAME")
        or "code-tutorial-builder",
        site_url=os.environ.get("OPENROUTER_SITE_URL")
        or env_values.get("OPENROUTER_SITE_URL"),
    )


class OpenRouterClient:
    """Minimal OpenRouter client for improving tutorial copy."""

    def __init__(self, settings: OpenRouterSettings, timeout_seconds: int = 60):
        self.settings = settings
        self.timeout_seconds = timeout_seconds

    def rewrite_steps(
        self,
        language: str,
        steps: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        if not steps:
            return steps

        payload = {
            "model": self.settings.model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You write concise developer tutorials. "
                        "Return JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": self._build_prompt(language, steps),
                },
            ],
        }

        request = Request(
            f"{self.settings.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"OpenRouter request failed ({exc.code}): {detail}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"OpenRouter request failed: {exc.reason}") from exc

        data = json.loads(body)
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("OpenRouter returned no choices.")

        message = choices[0].get("message") or {}
        content = _message_text(message.get("content"))
        if not content:
            raise RuntimeError("OpenRouter returned an empty response.")

        step_payload = _parse_step_payload(content)
        ai_steps = step_payload.get("steps")
        if not isinstance(ai_steps, list) or len(ai_steps) != len(steps):
            raise RuntimeError("OpenRouter returned an invalid step payload.")

        merged_steps: List[Dict[str, str]] = []
        for original, updated in zip(steps, ai_steps):
            title = str(updated.get("title") or original["title"]).strip()
            description = str(
                updated.get("description") or original["description"]
            ).strip()
            merged_steps.append(
                {
                    **original,
                    "title": title,
                    "description": description,
                }
            )

        return merged_steps

    def _build_prompt(self, language: str, steps: List[Dict[str, str]]) -> str:
        step_payload = [
            {
                "title": step["title"],
                "description": step["description"],
                "code": step["code"],
            }
            for step in steps
        ]
        return (
            f"Improve this {language} code tutorial.\n"
            "Return strict JSON with this shape:\n"
            '{"steps":[{"title":"...","description":"..."}]}\n'
            "Rules:\n"
            "- Keep the same number of steps and the same order.\n"
            "- Keep each title concise and concrete.\n"
            "- Keep each description to one or two sentences.\n"
            "- Do not mention the AI or add markdown fences.\n"
            "- Do not change the underlying code.\n\n"
            f"Current steps:\n{json.dumps(step_payload, indent=2)}"
        )

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Title": self.settings.app_name,
        }
        if self.settings.site_url:
            headers["HTTP-Referer"] = self.settings.site_url
        return headers


def _find_env_file(search_path: Optional[str] = None) -> Optional[Path]:
    for directory in _search_directories(search_path):
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
    return None


def _search_directories(search_path: Optional[str]) -> List[Path]:
    roots: List[Path] = []
    if search_path:
        candidate = Path(search_path).resolve()
        roots.append(candidate if candidate.is_dir() else candidate.parent)
    roots.append(Path.cwd().resolve())

    seen = set()
    directories: List[Path] = []
    for root in roots:
        for directory in [root, *root.parents]:
            if directory not in seen:
                seen.add(directory)
                directories.append(directory)
    return directories


def _read_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = _strip_quotes(value.strip())
    return values


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _message_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ).strip()
    return ""


def _parse_step_payload(content: str) -> Dict[str, object]:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise RuntimeError("OpenRouter did not return valid JSON.")

    return json.loads(text[start : end + 1])

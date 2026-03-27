import json
import pytest
from unittest.mock import patch, MagicMock
from code_tutorial_builder.ai import (
    DEFAULT_OPENROUTER_MODEL,
    OpenRouterClient,
    OpenRouterSettings,
    build_openrouter_client,
    load_openrouter_settings,
    _message_text,
    _parse_step_payload,
    _strip_quotes,
)


class TestOpenRouterSettings:
    def test_loads_from_env_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text(
            "OPENROUTER_API_KEY=test-key\n"
            "OPENROUTER_MODEL=custom/model\n"
        )

        settings = load_openrouter_settings(env_file=str(env_file))

        assert settings is not None
        assert settings.api_key == "test-key"
        assert settings.model == "custom/model"

    def test_uses_default_model_when_not_specified(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("OPENROUTER_API_KEY=test-key\n")

        settings = load_openrouter_settings(env_file=str(env_file))

        assert settings is not None
        assert settings.model == DEFAULT_OPENROUTER_MODEL

    def test_returns_none_without_api_key(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("OPENROUTER_MODEL=some/model\n")

        settings = load_openrouter_settings(env_file=str(env_file))
        assert settings is None

    def test_env_vars_override_file(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("OPENROUTER_API_KEY=file-key\nOPENROUTER_MODEL=file/model\n")
        monkeypatch.setenv("OPENROUTER_API_KEY", "env-key")
        monkeypatch.setenv("OPENROUTER_MODEL", "env/model")

        settings = load_openrouter_settings(env_file=str(env_file))
        assert settings.api_key == "env-key"
        assert settings.model == "env/model"


class TestBuildClient:
    def test_returns_none_without_credentials(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        assert build_openrouter_client() is None

    def test_returns_client_with_credentials(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        client = build_openrouter_client()
        assert isinstance(client, OpenRouterClient)


class TestStripQuotes:
    def test_double_quotes(self):
        assert _strip_quotes('"hello"') == "hello"

    def test_single_quotes(self):
        assert _strip_quotes("'hello'") == "hello"

    def test_no_quotes(self):
        assert _strip_quotes("hello") == "hello"

    def test_mismatched_quotes(self):
        assert _strip_quotes("'hello\"") == "'hello\""

    def test_empty_quoted(self):
        assert _strip_quotes('""') == ""


class TestMessageText:
    def test_string_content(self):
        assert _message_text("hello world") == "hello world"

    def test_list_content(self):
        content = [{"type": "text", "text": "hello "}, {"type": "text", "text": "world"}]
        assert _message_text(content) == "hello world"

    def test_empty_list(self):
        assert _message_text([]) == ""

    def test_none_content(self):
        assert _message_text(None) == ""

    def test_strips_whitespace(self):
        assert _message_text("  hello  ") == "hello"


class TestParseStepPayload:
    def test_plain_json(self):
        content = '{"steps": [{"title": "A", "description": "B"}]}'
        result = _parse_step_payload(content)
        assert result["steps"][0]["title"] == "A"

    def test_json_in_markdown_fence(self):
        content = "```json\n{\"steps\": [{\"title\": \"A\"}]}\n```"
        result = _parse_step_payload(content)
        assert result["steps"][0]["title"] == "A"

    def test_json_with_surrounding_text(self):
        content = 'Here is the result: {"steps": [{"title": "A"}]} done.'
        result = _parse_step_payload(content)
        assert result["steps"][0]["title"] == "A"

    def test_no_json_raises(self):
        with pytest.raises(RuntimeError, match="valid JSON"):
            _parse_step_payload("no json here")

    def test_invalid_json_raises(self):
        with pytest.raises((RuntimeError, json.JSONDecodeError)):
            _parse_step_payload("{invalid json}")


class TestRewriteSteps:
    def _make_client(self):
        settings = OpenRouterSettings(api_key="test-key")
        return OpenRouterClient(settings)

    def test_empty_steps_returns_empty(self):
        client = self._make_client()
        assert client.rewrite_steps("python", []) == []

    def test_successful_rewrite(self):
        client = self._make_client()
        original_steps = [
            {"title": "Old Title", "description": "Old desc", "code": "x = 1"},
        ]
        api_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "steps": [{"title": "New Title", "description": "New desc"}]
                    })
                }
            }]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(api_response).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("code_tutorial_builder.ai.urlopen", return_value=mock_response):
            result = client.rewrite_steps("python", original_steps)

        assert len(result) == 1
        assert result[0]["title"] == "New Title"
        assert result[0]["description"] == "New desc"
        assert result[0]["code"] == "x = 1"  # code preserved from original

    def test_preserves_original_code(self):
        client = self._make_client()
        original_steps = [
            {"title": "T", "description": "D", "code": "print('hello')"},
        ]
        api_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "steps": [{"title": "Better T", "description": "Better D", "code": "WRONG"}]
                    })
                }
            }]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(api_response).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("code_tutorial_builder.ai.urlopen", return_value=mock_response):
            result = client.rewrite_steps("python", original_steps)

        assert result[0]["code"] == "print('hello')"

    def test_mismatched_step_count_raises(self):
        client = self._make_client()
        original_steps = [
            {"title": "T1", "description": "D1", "code": "x = 1"},
            {"title": "T2", "description": "D2", "code": "y = 2"},
        ]
        api_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "steps": [{"title": "Only One"}]
                    })
                }
            }]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(api_response).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("code_tutorial_builder.ai.urlopen", return_value=mock_response):
            with pytest.raises(RuntimeError, match="invalid step payload"):
                client.rewrite_steps("python", original_steps)

    def test_empty_response_raises(self):
        client = self._make_client()
        api_response = {"choices": []}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(api_response).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("code_tutorial_builder.ai.urlopen", return_value=mock_response):
            with pytest.raises(RuntimeError, match="no choices"):
                client.rewrite_steps("python", [{"title": "T", "description": "D", "code": "x"}])

    def test_http_error_raises(self):
        from urllib.error import HTTPError

        client = self._make_client()
        error = HTTPError(
            url="http://test",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=MagicMock(read=lambda: b"rate limited"),
        )

        with patch("code_tutorial_builder.ai.urlopen", side_effect=error):
            with pytest.raises(RuntimeError, match="429"):
                client.rewrite_steps("python", [{"title": "T", "description": "D", "code": "x"}])

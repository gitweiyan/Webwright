from webwright.models.base import text_part
from webwright.models.openai_model import (
    OpenAIModel,
    OpenAIModelConfig,
    _extract_chat_completions_text,
    _extract_response_text,
)


def test_openai_model_chat_completions_includes_json_schema_when_enforced() -> None:
    config = OpenAIModelConfig(
        model_name="qwen3-vl-plus",
        openai_api_key="test-key",
        openai_endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        enforce_json_schema=True,
    )
    model = OpenAIModel(config_class=OpenAIModelConfig, **config.model_dump())

    payload = model._build_payload([{"role": "user", "content": "Hello!"}])

    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["strict"] is True
    assert "thought" in payload["response_format"]["json_schema"]["schema"]["properties"]


def test_openai_model_uses_chat_completions_payload_for_deepseek_endpoint() -> None:
    config = OpenAIModelConfig(
        model_name="deepseek-v4-pro",
        openai_api_key="test-key",
        openai_endpoint="https://api.deepseek.com/chat/completions",
    )
    model = OpenAIModel(config_class=OpenAIModelConfig, **config.model_dump())

    payload = model._build_payload([
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ])

    assert payload["model"] == "deepseek-v4-pro"
    assert payload["messages"] == [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ]
    assert payload["max_tokens"] == config.max_output_tokens
    assert "input" not in payload


def test_openai_model_uses_responses_payload_for_responses_endpoint() -> None:
    config = OpenAIModelConfig(
        model_name="gpt-4o",
        openai_api_key="test-key",
        openai_endpoint="https://api.openai.com/v1/responses",
    )
    model = OpenAIModel(config_class=OpenAIModelConfig, **config.model_dump())

    payload = model._build_payload([
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ])

    assert payload["model"] == "gpt-4o"
    assert "input" in payload
    assert payload["input"][0]["type"] == "message"
    assert payload["max_output_tokens"] == config.max_output_tokens
    assert "messages" not in payload


def test_extract_chat_completions_text_reads_choices_message_content() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '{"thought": "ok", "bash_command": "echo hi", "done": false, "final_response": ""}',
                }
            }
        ]
    }
    assert _extract_chat_completions_text(payload) == payload["choices"][0]["message"]["content"]


def test_openai_model_extract_text_uses_chat_completions_for_deepseek_endpoint() -> None:
    model = OpenAIModel(
        config_class=OpenAIModelConfig,
        model_name="deepseek-v4-pro",
        openai_api_key="test-key",
        openai_endpoint="https://api.deepseek.com/chat/completions",
    )
    payload = {
        "choices": [{"message": {"content": "hello from deepseek"}}],
    }
    assert model._extract_text(payload) == "hello from deepseek"


def test_openai_model_serializes_vision_parts_for_chat_completions() -> None:
    config = OpenAIModelConfig(
        model_name="qwen3-vl-plus",
        openai_api_key="test-key",
        openai_endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    )
    model = OpenAIModel(config_class=OpenAIModelConfig, **config.model_dump())

    payload = model._build_payload([
        {
            "role": "user",
            "content": [
                text_part("describe this"),
                {
                    "type": "input_image",
                    "image_url": "data:image/png;base64,abc",
                    "detail": "high",
                },
            ],
        },
    ])

    assert payload["messages"] == [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "describe this"},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64,abc", "detail": "high"},
                },
            ],
        },
    ]


def test_openai_model_reads_dashscope_api_key_from_env(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-dashscope-test")
    model = OpenAIModel(
        config_class=OpenAIModelConfig,
        model_name="qwen3-vl-plus",
        openai_endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    )
    assert model.config.openai_api_key == "sk-dashscope-test"


def test_openai_model_extract_text_uses_responses_api_for_responses_endpoint() -> None:
    model = OpenAIModel(
        config_class=OpenAIModelConfig,
        model_name="gpt-4o",
        openai_api_key="test-key",
        openai_endpoint="https://api.openai.com/v1/responses",
    )
    payload = {"output_text": "hello from responses"}
    assert model._extract_text(payload) == "hello from responses"
    assert _extract_response_text(payload) == "hello from responses"

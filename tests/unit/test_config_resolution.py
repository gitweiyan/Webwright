from webwright.config import get_config_from_spec


def test_config_spec_without_yaml_suffix():
    config = get_config_from_spec("model_qwen_vision")
    assert config["model"]["model_class"] == "openai"
    assert config["model"]["model_name"] == "qwen3-vl-plus"

from app.config import PromptConfig, get_settings


class TestPromptConfig:
    def test_title_defaults_when_not_in_yaml(self, tmp_path):
        yaml_file = tmp_path / "prompt.yaml"
        yaml_file.write_text("system_prompt: |\n  Test prompt.\n\nexpected_fields: []\n")
        config = PromptConfig(str(yaml_file))
        assert config.title == "Insurance Quote"

    def test_description_defaults_when_not_in_yaml(self, tmp_path):
        yaml_file = tmp_path / "prompt.yaml"
        yaml_file.write_text("system_prompt: |\n  Test prompt.\n\nexpected_fields: []\n")
        config = PromptConfig(str(yaml_file))
        assert "collect a few details" in config.description.lower()

    def test_title_from_yaml_overrides_default(self, tmp_path):
        yaml_file = tmp_path / "prompt.yaml"
        yaml_file.write_text(
            "title: My Custom Title\n"
            "system_prompt: |\n  Test prompt.\n\nexpected_fields: []\n"
        )
        config = PromptConfig(str(yaml_file))
        assert config.title == "My Custom Title"

    def test_description_from_yaml_overrides_default(self, tmp_path):
        yaml_file = tmp_path / "prompt.yaml"
        yaml_file.write_text(
            "description: Custom description.\n"
            "system_prompt: |\n  Test prompt.\n\nexpected_fields: []\n"
        )
        config = PromptConfig(str(yaml_file))
        assert config.description == "Custom description."

    def test_schema_version_is_hash_of_system_prompt(self, tmp_path):
        yaml_file = tmp_path / "prompt.yaml"
        yaml_file.write_text("system_prompt: |\n  Test prompt.\n\nexpected_fields: []\n")
        config = PromptConfig(str(yaml_file))
        assert len(config.schema_version) == 12
        assert all(c in "0123456789abcdef" for c in config.schema_version)

    def test_different_prompts_different_versions(self, tmp_path):
        f1 = tmp_path / "p1.yaml"
        f1.write_text("system_prompt: |\n  Prompt A\n\nexpected_fields: []\n")
        f2 = tmp_path / "p2.yaml"
        f2.write_text("system_prompt: |\n  Prompt B\n\nexpected_fields: []\n")
        c1 = PromptConfig(str(f1))
        c2 = PromptConfig(str(f2))
        assert c1.schema_version != c2.schema_version

    def test_raw_returns_parsed_yaml(self, tmp_path):
        yaml_file = tmp_path / "prompt.yaml"
        yaml_file.write_text(
            "system_prompt: |\n  Test prompt.\n\nexpected_fields: []\n"
        )
        config = PromptConfig(str(yaml_file))
        assert "system_prompt" in config.raw
        assert config.raw["expected_fields"] == []

    def test_reload_updates_config(self, tmp_path):
        yaml_file = tmp_path / "prompt.yaml"
        yaml_file.write_text("system_prompt: |\n  Version 1\n\nexpected_fields: []\n")
        config = PromptConfig(str(yaml_file))
        v1 = config.schema_version

        yaml_file.write_text("system_prompt: |\n  Version 2\n\nexpected_fields: []\n")
        config.reload()
        assert config.schema_version != v1
        assert "Version 2" in config.system_prompt


class TestGetSettings:
    def test_returns_settings_instance(self):
        settings = get_settings()
        assert settings.app_name == "Squad Nous Chatbot"

from unittest.mock import AsyncMock

import pytest

from app.services.schema_extractor import ExtractedSchema, FieldDefinition, SchemaExtractor


class TestBuildExtractionTools:
    def test_builds_valid_tool_definitions(self):
        extractor = SchemaExtractor(llm=None)
        extractor._cached_schema = ExtractedSchema(
            title="Car Insurance Quote",
            description="Collect car details for an insurance quote.",
            fields=[
                FieldDefinition(
                    name="car_type",
                    type="string",
                    description="Car type",
                    enum=["sedan", "coupe"],
                ),
                FieldDefinition(name="year", type="integer", description="Year"),
            ],
            pii_fields=[],
        )
        tools = extractor.build_extraction_tools()

        assert len(tools) == 2
        func = tools[0]["function"]
        assert func["name"] == "extract_customer_data"
        assert "car_type" in func["parameters"]["properties"]
        assert func["parameters"]["properties"]["car_type"]["enum"] == ["sedan", "coupe"]
        assert func["parameters"]["properties"]["year"]["type"] == "integer"

        # Second tool is mark_registration_complete
        assert tools[1]["function"]["name"] == "mark_registration_complete"

    def test_returns_empty_without_schema(self):
        extractor = SchemaExtractor(llm=None)
        assert extractor.build_extraction_tools() == []

    def test_includes_format_property(self):
        """Fields with a format (e.g. date) should include it in the tool definition."""
        extractor = SchemaExtractor(llm=None)
        extractor._cached_schema = ExtractedSchema(
            title="Test",
            description="Test",
            fields=[
                FieldDefinition(
                    name="birth_date", type="string", description="Date of birth", format="date"
                ),
            ],
            pii_fields=["birth_date"],
        )
        tools = extractor.build_extraction_tools()
        props = tools[0]["function"]["parameters"]["properties"]
        assert props["birth_date"]["format"] == "date"
        assert props["birth_date"]["type"] == "string"

    def test_format_and_enum_combined(self):
        """A field can have both format and enum."""
        extractor = SchemaExtractor(llm=None)
        extractor._cached_schema = ExtractedSchema(
            title="Test",
            description="Test",
            fields=[
                FieldDefinition(
                    name="period",
                    type="string",
                    description="Period",
                    format="date",
                    enum=["2024-Q1", "2024-Q2"],
                ),
            ],
            pii_fields=[],
        )
        tools = extractor.build_extraction_tools()
        prop = tools[0]["function"]["parameters"]["properties"]["period"]
        assert prop["format"] == "date"
        assert prop["enum"] == ["2024-Q1", "2024-Q2"]


class TestCacheInvalidation:
    def test_invalidate_clears_cached_schema(self):
        extractor = SchemaExtractor(llm=None)
        extractor._cached_schema = ExtractedSchema(
            title="X", description="X", fields=[], pii_fields=[]
        )
        assert extractor._cached_schema is not None
        extractor.invalidate_cache()
        assert extractor._cached_schema is None
        assert extractor.build_extraction_tools() == []


class TestExtract:
    @pytest.mark.asyncio
    async def test_returns_cached_schema_without_llm_call(self):
        """If schema is already cached, LLM should not be called."""
        llm = AsyncMock()
        extractor = SchemaExtractor(llm)
        cached = ExtractedSchema(
            title="Cached", description="Cached schema", fields=[], pii_fields=[]
        )
        extractor._cached_schema = cached

        # Prompt config is not even needed when cache exists
        result = await extractor.extract(None)
        assert result is cached
        llm.parse_structured.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_llm_when_no_cache(self, tmp_path):
        """Without cache, extract() should call the LLM and cache the result."""
        from app.config import PromptConfig

        yaml_file = tmp_path / "prompt.yaml"
        yaml_file.write_text("system_prompt: |\n  Test prompt.\n\nexpected_fields: []\n")
        config = PromptConfig(str(yaml_file))

        expected_schema = ExtractedSchema(
            title="Test",
            description="Test schema",
            fields=[FieldDefinition(name="field1", type="string", description="A field")],
            pii_fields=[],
        )
        llm = AsyncMock()
        llm.parse_structured.return_value = expected_schema
        extractor = SchemaExtractor(llm)

        result = await extractor.extract(config)
        assert result == expected_schema
        assert extractor._cached_schema == expected_schema
        llm.parse_structured.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_on_llm_failure(self, tmp_path):
        """If the LLM fails during extraction, the exception should propagate."""
        from app.config import PromptConfig

        yaml_file = tmp_path / "prompt.yaml"
        yaml_file.write_text("system_prompt: |\n  Test prompt.\n\nexpected_fields: []\n")
        config = PromptConfig(str(yaml_file))

        llm = AsyncMock()
        llm.parse_structured.side_effect = RuntimeError("LLM unavailable")
        extractor = SchemaExtractor(llm)

        with pytest.raises(RuntimeError, match="LLM unavailable"):
            await extractor.extract(config)

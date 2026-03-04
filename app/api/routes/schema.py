from fastapi import APIRouter, Depends

from app.api.deps import get_prompt_config, get_schema_extractor
from app.config import PromptConfig
from app.models.schema import FieldInfo, SchemaResponse
from app.services.schema_extractor import SchemaExtractor

router = APIRouter(prefix="/api", tags=["schema"])


@router.get("/schema", response_model=SchemaResponse)
async def get_schema(
    extractor: SchemaExtractor = Depends(get_schema_extractor),
    prompt_config: PromptConfig = Depends(get_prompt_config),
):
    schema = await extractor.extract(prompt_config)
    # YAML title/description override LLM-extracted ones if present
    title = prompt_config.raw.get("title") or schema.title
    description = prompt_config.raw.get("description") or schema.description
    return SchemaResponse(
        schema_version=prompt_config.schema_version,
        title=title,
        description=description,
        fields=[
            FieldInfo(
                name=f.name,
                type=f.type,
                description=f.description,
                required=f.required,
                format=f.format,
                enum=f.enum,
            )
            for f in schema.fields
        ],
    )

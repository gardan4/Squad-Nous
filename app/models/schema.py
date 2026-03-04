from pydantic import BaseModel


class FieldInfo(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    format: str | None = None
    enum: list[str] | None = None


class SchemaResponse(BaseModel):
    schema_version: str
    title: str
    description: str
    fields: list[FieldInfo]

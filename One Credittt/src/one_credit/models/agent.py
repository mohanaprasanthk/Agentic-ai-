from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Agent(BaseModel):
    """Represents an automated agent capable of handling requests."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str = Field(..., min_length=1)
    type: str = "agent"
    status: str = "active"
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("type must not be blank")
        return cleaned

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Resource(BaseModel):
    """Represents a digital or physical resource used for a request."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str = Field(..., min_length=1)
    kind: str
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("kind must not be blank")
        return cleaned

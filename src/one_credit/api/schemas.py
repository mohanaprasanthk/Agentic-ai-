from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from one_credit.simulation import ArchitectureType, Scenario


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "one-credit-api"


class SimulationRunRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    architecture: ArchitectureType | str | None = None
    scenario: Scenario | dict[str, Any] | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class ComparisonRunRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    scenario: Scenario | dict[str, Any] | None = None


__all__ = ["HealthResponse", "SimulationRunRequest", "ComparisonRunRequest"]

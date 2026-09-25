from __future__ import annotations

import random
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from one_credit.models import Agent, Request, Resource
from one_credit.simulation import ArchitectureType, Scenario


class ScenarioGeneratorConfig(BaseModel):
    """Deterministic configuration used to generate a reusable scenario."""

    model_config = ConfigDict(extra="ignore")

    number_of_agents: int = 5
    number_of_resources: int = 3
    number_of_requests: int = 5
    conflict_probability: float = 0.25
    priority_range: tuple[str, str] = ("low", "high")
    flexibility_range: tuple[int, int] = (1, 5)
    time_range: tuple[int, int] = (1, 7)
    random_seed: int = 42
    architecture: str = "CENTRALIZED"

    @field_validator("number_of_agents", "number_of_resources", "number_of_requests")
    @classmethod
    def validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Counts must be positive integers.")
        return value

    @field_validator("conflict_probability")
    @classmethod
    def validate_conflict_probability(cls, value: float) -> float:
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError("conflict_probability must be between 0.0 and 1.0 inclusive.")
        return float(value)

    @field_validator("priority_range")
    @classmethod
    def validate_priority_range(cls, value: tuple[str, str] | list[str]) -> tuple[str, str]:
        values = list(value)
        if len(values) != 2:
            raise ValueError("priority_range must contain exactly two priority values.")
        allowed = ["low", "normal", "medium", "high", "critical"]
        normalized = [str(item).strip().lower() for item in values]
        if any(item not in allowed for item in normalized):
            raise ValueError(f"Invalid priority values in priority_range: {values}")
        ordered = sorted(normalized, key=lambda item: allowed.index(item))
        return (ordered[0], ordered[-1])

    @field_validator("flexibility_range", "time_range")
    @classmethod
    def validate_range(cls, value: tuple[int, int] | list[int]) -> tuple[int, int]:
        values = list(value)
        if len(values) != 2:
            raise ValueError("Ranges must contain exactly two integer values.")
        start, end = int(values[0]), int(values[1])
        if start > end:
            raise ValueError("Range start must be less than or equal to the end value.")
        return (start, end)

    @field_validator("architecture")
    @classmethod
    def validate_architecture(cls, value: str) -> str:
        normalized = str(value).strip().upper()
        allowed = {
            "CENTRALIZED",
            "HIERARCHICAL",
            "DECENTRALIZED",
            "SEQUENTIAL",
            "PARALLEL",
            "BLACKBOARD",
            "PEER_TO_PEER",
        }
        if normalized not in allowed:
            raise ValueError(f"Unsupported architecture: {value}")
        return normalized


class ScenarioGenerator:
    """Generate deterministic and reusable negotiation scenarios."""

    _PRIORITY_ORDER = ["low", "normal", "medium", "high", "critical"]

    def __init__(self, config: ScenarioGeneratorConfig | dict[str, Any] | None = None) -> None:
        self.config = self._coerce_config(config)

    def _coerce_config(self, config: ScenarioGeneratorConfig | dict[str, Any] | None) -> ScenarioGeneratorConfig:
        if config is None:
            return ScenarioGeneratorConfig()
        if isinstance(config, ScenarioGeneratorConfig):
            return config
        return ScenarioGeneratorConfig(**config)

    def generate_small(self) -> Scenario:
        return self.generate(ScenarioGeneratorConfig(number_of_agents=5, number_of_resources=3, number_of_requests=5, random_seed=self.config.random_seed))

    def generate_medium(self) -> Scenario:
        return self.generate(ScenarioGeneratorConfig(number_of_agents=10, number_of_resources=5, number_of_requests=10, random_seed=self.config.random_seed))

    def generate_large(self) -> Scenario:
        return self.generate(ScenarioGeneratorConfig(number_of_agents=25, number_of_resources=10, number_of_requests=25, random_seed=self.config.random_seed))

    def generate_stress(self) -> Scenario:
        return self.generate(ScenarioGeneratorConfig(number_of_agents=50, number_of_resources=20, number_of_requests=50, random_seed=self.config.random_seed))

    def generate_very_large(self) -> Scenario:
        return self.generate(ScenarioGeneratorConfig(number_of_agents=100, number_of_resources=30, number_of_requests=100, random_seed=self.config.random_seed))

    def generate(self, config: ScenarioGeneratorConfig | dict[str, Any] | None = None) -> Scenario:
        cfg = self._coerce_config(config or self.config)
        rng = random.Random(cfg.random_seed)

        agents = self._generate_agents(cfg, rng)
        resources = self._generate_resources(cfg, rng)
        requests = self._generate_requests(cfg, rng, agents, resources)

        scenario_id = f"scenario-{cfg.random_seed}-{cfg.number_of_agents}-{cfg.number_of_requests}"
        return Scenario(
            agents=agents,
            resources=resources,
            requests=requests,
            architecture=ArchitectureType(cfg.architecture),
            scenario_id=scenario_id,
            parameters={
                "expected_value": 200.0,
                "max_budget": 150.0,
                "risk": 10.0,
                "conflict_probability": cfg.conflict_probability,
                "priority_range": list(cfg.priority_range),
                "flexibility_range": list(cfg.flexibility_range),
                "time_range": list(cfg.time_range),
                "random_seed": cfg.random_seed,
            },
            metadata={
                "generator": "ScenarioGenerator",
                "random_seed": cfg.random_seed,
                "conflict_probability": cfg.conflict_probability,
                "architecture": cfg.architecture,
            },
        )

    def _generate_agents(self, config: ScenarioGeneratorConfig, rng: random.Random) -> list[Agent]:
        agents: list[Agent] = []
        for index in range(config.number_of_agents):
            agent_id = f"agent-{config.random_seed}-{index:03d}-{rng.randint(1000, 9999)}"
            name = f"Agent-{config.random_seed}-{index:03d}-{rng.randint(10, 99)}"
            agent_type = ["researcher", "provider", "analyst", "coordinator", "operator"][index % 5]
            capabilities = [
                "resource_access",
                agent_type,
                f"role-{index % 4}",
                "negotiation",
            ]
            agents.append(
                Agent(
                    id=agent_id,
                    name=name,
                    type=agent_type,
                    capabilities=capabilities,
                    metadata={"seed": config.random_seed, "index": index},
                )
            )
        return agents

    def _generate_resources(self, config: ScenarioGeneratorConfig, rng: random.Random) -> list[Resource]:
        resources: list[Resource] = []
        for index in range(config.number_of_resources):
            resource_id = f"resource-{config.random_seed}-{index:03d}-{rng.randint(1000, 9999)}"
            resource_name = f"Resource-{config.random_seed}-{index:03d}-{rng.randint(100, 999)}"
            kind = ["compute", "storage", "network", "data", "facility"][index % 5]
            resources.append(
                Resource(
                    id=resource_id,
                    name=resource_name,
                    kind=kind,
                    url=f"https://example.com/{resource_name.lower().replace(' ', '-')}",
                    metadata={"seed": config.random_seed, "index": index},
                )
            )
        return resources

    def _generate_requests(
        self,
        config: ScenarioGeneratorConfig,
        rng: random.Random,
        agents: list[Agent],
        resources: list[Resource],
    ) -> list[Request]:
        request_ids: set[str] = set()
        requests: list[Request] = []
        resource_names = [resource.name for resource in resources]
        relevant_resource_pool = list(resource_names)

        for index in range(config.number_of_requests):
            agent = agents[index % len(agents)]
            requester_id = agent.id
            priority = self._pick_priority(config, rng)

            chosen_resource = resource_names[index % len(resource_names)]
            if len(resource_names) > 1 and rng.random() < config.conflict_probability:
                chosen_resource = resource_names[rng.randrange(len(resource_names))]

            required_resources = [chosen_resource]
            if len(resource_names) > 1 and rng.random() < 0.3:
                alternate = resource_names[rng.randrange(len(resource_names))]
                if alternate not in required_resources:
                    required_resources.append(alternate)

            request_id = f"request-{config.random_seed}-{index:03d}-{rng.randint(1000, 9999)}"
            request_id = request_id if request_id not in request_ids else f"request-{config.random_seed}-{index:03d}-{rng.randint(1000, 9999)}-{rng.randint(1, 999)}"
            request_ids.add(request_id)

            flexibility = rng.randint(*config.flexibility_range)
            timeline = rng.randint(*config.time_range)
            request = Request(
                id=request_id,
                title=f"Request-{config.random_seed}-{index:03d}",
                description=f"Generated request {index + 1} using {', '.join(required_resources)}.",
                requester_id=requester_id,
                required_resources=required_resources,
                priority=priority,
                status="open",
                metadata={
                    "seed": config.random_seed,
                    "flexibility": flexibility,
                    "timeline": timeline,
                    "requested_at_index": index,
                    "conflict_probability": config.conflict_probability,
                    "resource_names": required_resources,
                },
            )
            requests.append(request)

        return requests

    def _pick_priority(self, config: ScenarioGeneratorConfig, rng: random.Random) -> str:
        lower, upper = config.priority_range
        ordered = [priority.lower() for priority in self._PRIORITY_ORDER]
        start_index = ordered.index(lower.lower())
        end_index = ordered.index(upper.lower())
        if start_index > end_index:
            start_index, end_index = end_index, start_index
        choice = ordered[rng.randint(start_index, end_index)]
        return choice


__all__ = ["ScenarioGenerator", "ScenarioGeneratorConfig"]

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from one_credit.architecture_comparison import ArchitectureComparisonResult
from one_credit.metrics import MetricsResult
from one_credit.models import Agent, Resource
from one_credit.simulation import SimulationResult


@dataclass
class InMemoryStore:
    """Simple in-memory repository for API state."""

    agents: dict[str, Agent] = field(default_factory=dict)
    resources: dict[str, Resource] = field(default_factory=dict)
    simulations: dict[str, SimulationResult] = field(default_factory=dict)
    metrics: dict[str, MetricsResult] = field(default_factory=dict)
    comparisons: dict[str, ArchitectureComparisonResult] = field(default_factory=dict)

    def register_agent(self, agent: Agent) -> Agent:
        self.agents[agent.id] = agent
        return agent

    def list_agents(self) -> list[Agent]:
        return list(self.agents.values())

    def register_resource(self, resource: Resource) -> Resource:
        self.resources[resource.id] = resource
        return resource

    def list_resources(self) -> list[Resource]:
        return list(self.resources.values())

    def store_simulation(self, result: SimulationResult) -> SimulationResult:
        self.simulations[result.simulation_id] = result
        return result

    def get_simulation(self, simulation_id: str) -> SimulationResult | None:
        return self.simulations.get(simulation_id)

    def store_metrics(self, simulation_id: str, metrics: MetricsResult) -> MetricsResult:
        self.metrics[simulation_id] = metrics
        return metrics

    def get_metrics(self, simulation_id: str) -> MetricsResult | None:
        return self.metrics.get(simulation_id)

    def store_comparison(self, comparison: ArchitectureComparisonResult) -> ArchitectureComparisonResult:
        self.comparisons[comparison.scenario.scenario_id if comparison.scenario else "comparison"] = comparison
        return comparison

    def get_comparison(self, scenario_id: str) -> ArchitectureComparisonResult | None:
        return self.comparisons.get(scenario_id)


store = InMemoryStore()

__all__ = ["InMemoryStore", "store"]

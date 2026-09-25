from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from one_credit.metrics import MetricsEngine, MetricsResult
from one_credit.simulation import ArchitectureType, Scenario, SimulationEngine, SimulationResult


class ArchitectureExecutionResult(BaseModel):
    """Detailed comparison data for a single architecture execution."""

    model_config = ConfigDict(extra="ignore")

    architecture: str = "UNKNOWN"
    success: bool = False
    total_requests: int = 0
    successful_negotiations: int = 0
    failed_negotiations: int = 0
    success_rate: float = 0.0
    resource_utilization: float = 0.0
    total_execution_time: float = 0.0
    average_negotiation_time: float = 0.0
    communication_overhead: int = 0
    number_of_conflicts: int = 0
    average_agent_utility: float = 0.0
    fairness: float = 0.0
    negotiation_rounds: int = 0
    final_allocation: dict[str, Any] = Field(default_factory=dict)
    simulation_result: SimulationResult | None = None
    metrics_result: MetricsResult | None = None
    error: str | None = None
    errors: list[str] = Field(default_factory=list)


class ArchitectureComparisonResult(BaseModel):
    """Aggregate comparison across the supported architectures."""

    model_config = ConfigDict(extra="ignore")

    scenario: Scenario | None = None
    results: dict[str, ArchitectureExecutionResult] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)
    architecture_count: int = 0
    executed_architectures: list[str] = Field(default_factory=list)
    failed_architectures: list[str] = Field(default_factory=list)
    successful_architectures: list[str] = Field(default_factory=list)
    completed: bool = False

    @property
    def all_results(self) -> list[ArchitectureExecutionResult]:
        return list(self.results.values())

    @property
    def result_map(self) -> dict[str, ArchitectureExecutionResult]:
        return self.results


class ArchitectureComparisonEngine:
    """Run a single scenario through every supported architecture and collect outcomes."""

    _ARCHITECTURES = [
        ArchitectureType.CENTRALIZED,
        ArchitectureType.HIERARCHICAL,
        ArchitectureType.DECENTRALIZED,
        ArchitectureType.SEQUENTIAL,
        ArchitectureType.PARALLEL,
        ArchitectureType.BLACKBOARD,
        ArchitectureType.PEER_TO_PEER,
    ]

    def __init__(self, *, simulation_engine: SimulationEngine | None = None, metrics_engine: MetricsEngine | None = None) -> None:
        self.simulation_engine = simulation_engine or SimulationEngine()
        self.metrics_engine = metrics_engine or MetricsEngine()

    def _valid_scenario(self, scenario: Scenario | None) -> Scenario | None:
        if scenario is None:
            return None
        if isinstance(scenario, Scenario):
            return scenario
        if isinstance(scenario, dict):
            return Scenario.model_validate(scenario)
        return None

    def _architecture_names(self) -> list[str]:
        return [architecture.value for architecture in self._ARCHITECTURES]

    def _extract_metrics(self, result: SimulationResult) -> ArchitectureExecutionResult:
        metrics = self.metrics_engine.calculate(result)
        return ArchitectureExecutionResult(
            architecture=result.architecture,
            success=bool(result.success),
            total_requests=int(metrics.total_requests),
            successful_negotiations=int(metrics.successful_negotiations),
            failed_negotiations=int(metrics.failed_negotiations),
            success_rate=float(metrics.success_rate),
            resource_utilization=float(metrics.resource_utilization),
            total_execution_time=float(metrics.total_execution_time),
            average_negotiation_time=float(metrics.average_negotiation_time),
            communication_overhead=int(metrics.communication_overhead),
            number_of_conflicts=int(metrics.number_of_conflicts),
            average_agent_utility=float(metrics.average_agent_utility),
            fairness=float(metrics.fairness),
            negotiation_rounds=int(metrics.negotiation_rounds),
            final_allocation=dict(result.final_allocation or {}),
            simulation_result=result,
            metrics_result=metrics,
            error=(result.errors[0] if result.errors else None),
            errors=list(result.errors or []),
        )

    def _run_architecture(self, scenario: Scenario, architecture: str | ArchitectureType) -> ArchitectureExecutionResult:
        architecture_name = architecture.value if isinstance(architecture, ArchitectureType) else str(architecture).strip().upper()
        try:
            simulation_result = self.simulation_engine.run(scenario, architecture=architecture_name)
            execution = self._extract_metrics(simulation_result)
            execution.architecture = architecture_name
            if execution.error is not None:
                execution.success = False
            return execution
        except Exception as exc:  # pragma: no cover - defensive guard
            return ArchitectureExecutionResult(
                architecture=architecture_name,
                success=False,
                error=str(exc),
                errors=[str(exc)],
                simulation_result=None,
                metrics_result=None,
            )

    def compare(self, scenario: Scenario | dict[str, Any] | None) -> ArchitectureComparisonResult:
        validated = self._valid_scenario(scenario)
        if validated is None:
            return ArchitectureComparisonResult(
                scenario=scenario,
                errors={"SCENARIO": "Scenario is required and must be valid."},
                completed=False,
            )

        try:
            self.simulation_engine.validate_scenario(validated)
        except ValueError as exc:
            return ArchitectureComparisonResult(
                scenario=validated,
                errors={"SCENARIO": str(exc)},
                completed=False,
            )

        comparison = ArchitectureComparisonResult(scenario=validated)
        for architecture_name in self._architecture_names():
            entry = self._run_architecture(validated, architecture_name)
            comparison.results[architecture_name] = entry
            comparison.executed_architectures.append(architecture_name)
            if entry.success:
                comparison.successful_architectures.append(architecture_name)
            else:
                comparison.failed_architectures.append(architecture_name)
                if entry.error:
                    comparison.errors[architecture_name] = entry.error

        comparison.architecture_count = len(comparison.results)
        comparison.completed = True
        return comparison

    def compare_all(self, scenario: Scenario | dict[str, Any] | None) -> ArchitectureComparisonResult:
        return self.compare(scenario)


__all__ = [
    "ArchitectureComparisonEngine",
    "ArchitectureComparisonResult",
    "ArchitectureExecutionResult",
]

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from pydantic import BaseModel, Field

from one_credit.simulation import SimulationResult


class MetricsResult(BaseModel):
    """Deterministic aggregate metrics derived from a simulation result."""

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
    architecture: str = "UNKNOWN"
    simulation_id: str = ""
    errors: list[str] = Field(default_factory=list)


class MetricsEngine:
    """Architecture-agnostic calculator for per-simulation metrics."""

    def calculate(self, result: SimulationResult | dict[str, Any] | None) -> MetricsResult:
        if result is None:
            return MetricsResult(errors=["No simulation result provided."])

        if isinstance(result, dict):
            try:
                result = SimulationResult.model_validate(result)
            except Exception as exc:  # pragma: no cover - defensive conversion path
                return MetricsResult(errors=[f"Invalid simulation result payload: {exc}"])

        output = MetricsResult(
            architecture=result.architecture,
            simulation_id=result.simulation_id,
            total_execution_time=float(result.execution_time or 0.0),
            negotiation_rounds=int(result.negotiation_rounds or 0),
            successful_negotiations=len(result.successful_negotiations or []),
            failed_negotiations=len(result.failed_negotiations or []),
        )

        try:
            output.total_requests = self._total_requests(result)
            output.success_rate = self._success_rate(output.total_requests, output.successful_negotiations)
            output.resource_utilization = self._resource_utilization(result)
            output.total_execution_time = float(result.execution_time or 0.0)
            output.average_negotiation_time = self._average_negotiation_time(result)
            output.communication_overhead = self._communication_overhead(result)
            output.number_of_conflicts = self._number_of_conflicts(result)
            output.average_agent_utility = self._average_agent_utility(result)
            output.fairness = self._fairness(result)
            if output.negotiation_rounds == 0:
                output.negotiation_rounds = self._estimate_negotiation_rounds(result)
            if output.successful_negotiations == 0 and output.failed_negotiations == 0:
                output.success_rate = 0.0
        except Exception as exc:  # pragma: no cover - defensive fallback for bad data
            output.errors.append(str(exc))

        return output

    def _total_requests(self, result: SimulationResult) -> int:
        successful = set(result.successful_negotiations or [])
        failed = set(result.failed_negotiations or [])
        combined = successful | failed
        if combined:
            return len(combined)
        allocations = result.final_allocation or {}
        if isinstance(allocations, dict):
            return len(allocations)
        return 0

    def _success_rate(self, total_requests: int, successful_negotiations: int) -> float:
        if total_requests <= 0:
            return 0.0
        return round((successful_negotiations / total_requests) * 100.0, 2)

    def _resource_utilization(self, result: SimulationResult) -> float:
        allocations = result.final_allocation or {}
        resources: set[str] = set()

        for allocation in allocations.values():
            if not isinstance(allocation, dict):
                continue
            resource_name = allocation.get("resource_name") or allocation.get("resource")
            if resource_name:
                resources.add(str(resource_name))

        if not resources:
            for event in result.negotiation_events or []:
                if isinstance(event, dict):
                    resource_name = event.get("resource_name") or event.get("resource")
                    if resource_name:
                        resources.add(str(resource_name))
            for conflict in result.unresolved_conflicts or []:
                if isinstance(conflict, dict):
                    resource_name = conflict.get("resource_name") or conflict.get("resource")
                    if resource_name:
                        resources.add(str(resource_name))

        if not resources:
            return 0.0

        utilized = len(resources)
        available = max(len(resources), 1)
        return round((utilized / available) * 100.0, 2)

    def _average_negotiation_time(self, result: SimulationResult) -> float:
        durations: list[float] = []
        for event in result.negotiation_events or []:
            if not isinstance(event, dict):
                continue
            for key in ("duration_seconds", "duration_ms", "duration", "elapsed_seconds", "elapsed_ms", "time_seconds", "time_ms"):
                if key in event:
                    try:
                        value = float(event[key])
                        if key.endswith("ms"):
                            value = value / 1000.0
                        durations.append(value)
                    except (TypeError, ValueError):
                        continue

        if durations:
            return round(sum(durations) / len(durations), 2)
        if result.execution_time and self._total_requests(result) > 0:
            return round(float(result.execution_time) / self._total_requests(result), 2)
        return 0.0

    def _communication_overhead(self, result: SimulationResult) -> int:
        messages = result.communication_messages or []
        events = result.negotiation_events or []
        return len(messages) + len(events)

    def _number_of_conflicts(self, result: SimulationResult) -> int:
        unresolved = result.unresolved_conflicts or []
        if unresolved:
            conflict_keys: set[str] = set()
            for conflict in unresolved:
                if not isinstance(conflict, dict):
                    continue
                resource_name = conflict.get("resource_name") or conflict.get("resource")
                request_ids = conflict.get("request_ids") or []
                key = str(resource_name or "")
                if request_ids:
                    key = f"{key}:{','.join(map(str, request_ids))}"
                if key:
                    conflict_keys.add(key)
            return len(conflict_keys)

        conflict_keys: set[str] = set()
        for event in result.negotiation_events or []:
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("type", "")).lower()
            if "conflict" in event_type and event.get("status") in {"conflict", "unresolved"}:
                resource_name = event.get("resource_name") or event.get("resource")
                key = str(resource_name or event_type)
                conflict_keys.add(key)

        return len(conflict_keys)

    def _average_agent_utility(self, result: SimulationResult) -> float:
        utilities: list[float] = []
        for event in result.negotiation_events or []:
            if not isinstance(event, dict):
                continue
            for key in ("utility", "agent_utility", "value"):
                if key in event:
                    try:
                        utilities.append(float(event[key]))
                    except (TypeError, ValueError):
                        continue

        for allocation in (result.final_allocation or {}).values():
            if not isinstance(allocation, dict):
                continue
            for key in ("utility", "agent_utility", "value"):
                if key in allocation:
                    try:
                        utilities.append(float(allocation[key]))
                    except (TypeError, ValueError):
                        continue

        if not utilities:
            return 0.0
        return round(sum(utilities) / len(utilities), 4)

    def _fairness(self, result: SimulationResult) -> float:
        utilities = []
        for event in result.negotiation_events or []:
            if not isinstance(event, dict):
                continue
            for key in ("utility", "agent_utility"):
                if key in event:
                    try:
                        utilities.append(float(event[key]))
                    except (TypeError, ValueError):
                        continue

        for allocation in (result.final_allocation or {}).values():
            if not isinstance(allocation, dict):
                continue
            for key in ("utility", "agent_utility"):
                if key in allocation:
                    try:
                        utilities.append(float(allocation[key]))
                    except (TypeError, ValueError):
                        continue

        if not utilities:
            return 0.0

        numerator = sum(utilities) ** 2
        denominator = len(utilities) * sum(value ** 2 for value in utilities)
        if denominator <= 0:
            return 0.0
        return round(numerator / denominator, 4)

    def _estimate_negotiation_rounds(self, result: SimulationResult) -> int:
        if result.negotiation_rounds:
            return int(result.negotiation_rounds)
        count = 0
        for event in result.negotiation_events or []:
            if isinstance(event, dict):
                event_type = str(event.get("type", "")).upper()
                if event_type in {"PROPOSAL", "COUNTEROFFER", "ACCEPT", "REJECT", "AGREEMENT", "CONFLICT"}:
                    count += 1
        return count


__all__ = ["MetricsEngine", "MetricsResult"]

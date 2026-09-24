from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from one_credit.architecture import (
    BlackboardArchitecture,
    CentralizedArchitecture,
    DecentralizedArchitecture,
    HierarchicalArchitecture,
    ParallelArchitecture,
    PeerToPeerArchitecture,
    SequentialArchitecture,
)
from one_credit.models import Agent, Proposal, Request, Resource


class ArchitectureType(str, Enum):
    """Supported architecture families for scenario execution."""

    CENTRALIZED = "CENTRALIZED"
    HIERARCHICAL = "HIERARCHICAL"
    DECENTRALIZED = "DECENTRALIZED"
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"
    BLACKBOARD = "BLACKBOARD"
    PEER_TO_PEER = "PEER_TO_PEER"


class Scenario(BaseModel):
    """Reusable execution blueprint for a negotiation scenario."""

    model_config = ConfigDict(extra="ignore")

    agents: list[Agent] = Field(default_factory=list)
    resources: list[Resource] = Field(default_factory=list)
    requests: list[Request] = Field(default_factory=list)
    architecture: ArchitectureType | str = ArchitectureType.CENTRALIZED
    parameters: dict[str, Any] = Field(default_factory=dict)
    simulation_parameters: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    scenario_id: str = Field(default_factory=lambda: uuid.uuid4().hex)

    @model_validator(mode="before")
    @classmethod
    def normalize_inputs(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values

        if "simulation_parameters" not in values and "parameters" in values:
            values["simulation_parameters"] = values["parameters"]
        if "parameters" not in values and "simulation_parameters" in values:
            values["parameters"] = values["simulation_parameters"]

        if "architecture" in values and isinstance(values["architecture"], str):
            values["architecture"] = values["architecture"].upper()
        return values

    @field_validator("architecture", mode="before")
    @classmethod
    def validate_architecture_value(cls, value: Any) -> ArchitectureType | str:
        if isinstance(value, ArchitectureType):
            return value
        if isinstance(value, str):
            normalized = value.strip().upper()
            try:
                return ArchitectureType(normalized)
            except ValueError:
                return normalized
        return value


class SimulationResult(BaseModel):
    """Standard output returned by the simulation engine."""

    model_config = ConfigDict(extra="ignore")

    simulation_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    architecture: str = "UNKNOWN"
    success: bool = False
    final_allocation: dict[str, Any] = Field(default_factory=dict)
    successful_negotiations: list[str] = Field(default_factory=list)
    failed_negotiations: list[str] = Field(default_factory=list)
    unresolved_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    negotiation_events: list[dict[str, Any]] = Field(default_factory=list)
    negotiation_rounds: int = 0
    communication_messages: list[dict[str, Any]] = Field(default_factory=list)
    execution_time: float = 0.0
    errors: list[str] = Field(default_factory=list)


class SimulationEngine:
    """Common runner that executes the same scenario across any supported architecture."""

    def __init__(self, *, strategy: Any | None = None) -> None:
        self.strategy = strategy
        self.scenario: Scenario | None = None

    def select_architecture(self, architecture: str | ArchitectureType) -> type:
        normalized = architecture.value if isinstance(architecture, Enum) else str(architecture).strip().upper()
        mapping: dict[str, type] = {
            "CENTRALIZED": CentralizedArchitecture,
            "HIERARCHICAL": HierarchicalArchitecture,
            "DECENTRALIZED": DecentralizedArchitecture,
            "SEQUENTIAL": SequentialArchitecture,
            "PARALLEL": ParallelArchitecture,
            "BLACKBOARD": BlackboardArchitecture,
            "PEER_TO_PEER": PeerToPeerArchitecture,
        }
        if normalized not in mapping:
            raise ValueError(f"Unknown architecture: {architecture}. Supported architectures: {sorted(mapping)}")
        return mapping[normalized]

    def load_scenario(self, scenario: Scenario) -> Scenario:
        self.scenario = scenario
        self.validate_scenario(scenario)
        return scenario

    def validate_scenario(self, scenario: Scenario) -> bool:
        if not scenario.agents:
            raise ValueError("Scenario must include at least one agent.")
        if not scenario.resources:
            raise ValueError("Scenario must include at least one resource.")
        if not scenario.requests:
            raise ValueError("Scenario must include at least one request.")

        agent_ids = {agent.id for agent in scenario.agents}
        resource_names = {resource.name for resource in scenario.resources}

        for request in scenario.requests:
            if not request.requester_id:
                raise ValueError(f"Request {request.id} is missing a requester_id.")
            if request.requester_id not in agent_ids:
                raise ValueError(f"Request {request.id} references unknown requester_id {request.requester_id}.")
            missing = [resource_name for resource_name in request.required_resources if resource_name not in resource_names]
            if missing:
                raise ValueError(f"Request {request.id} references missing resources: {missing}")

        self.select_architecture(scenario.architecture)
        return True

    def _coerce_parameters(self, scenario: Scenario) -> dict[str, Any]:
        values = dict(scenario.parameters)
        if not values and scenario.simulation_parameters:
            values = dict(scenario.simulation_parameters)
        return values

    def _register_architecture(self, architecture_instance: Any, scenario: Scenario) -> None:
        for resource in scenario.resources:
            architecture_instance.register_resource(resource)

        if isinstance(architecture_instance, HierarchicalArchitecture):
            campus_manager = Agent(
                id="campus-manager",
                name="Campus Manager",
                type="campus_manager",
                capabilities=["coordination"],
            )
            architecture_instance.register_manager(campus_manager)
            for agent in scenario.agents:
                architecture_instance.register_agent(agent, manager_id=campus_manager.id)
            return

        for agent in scenario.agents:
            if isinstance(architecture_instance, PeerToPeerArchitecture):
                if hasattr(architecture_instance, "register_peer"):
                    architecture_instance.register_peer(agent)
                else:
                    architecture_instance.register_agent(agent)
            elif hasattr(architecture_instance, "register_agent"):
                architecture_instance.register_agent(agent)
            elif hasattr(architecture_instance, "register_peer"):
                architecture_instance.register_peer(agent)

    def _register_requests(self, architecture_instance: Any, scenario: Scenario) -> None:
        for request in scenario.requests:
            if hasattr(architecture_instance, "create_request"):
                architecture_instance.create_request(request)
            elif hasattr(architecture_instance, "register_request"):
                architecture_instance.register_request(request)
            else:
                raise ValueError(f"Architecture {type(architecture_instance).__name__} cannot register requests.")

    def _choose_agent_for_request(self, scenario: Scenario, request: Request) -> Agent:
        candidates = [agent for agent in scenario.agents if agent.id != request.requester_id]
        if not candidates:
            return scenario.agents[0]

        resource_names = {name.lower() for name in request.required_resources}
        for agent in candidates:
            token_set = {cap.lower() for cap in agent.capabilities}
            if resource_names & token_set:
                return agent
        for agent in candidates:
            if agent.type.lower() != "requester":
                return agent
        return candidates[0]

    def _build_proposal(self, scenario: Scenario, request: Request, agent: Agent, parameters: dict[str, Any]) -> Proposal:
        resource_name = next(iter(request.required_resources), "unknown-resource")
        price = float(parameters.get("proposal_price", parameters.get("max_budget", 90.0)))
        if price <= 0:
            price = 90.0
        return Proposal(
            id=f"{request.id}-{agent.id}-proposal",
            request_id=request.id,
            agent_id=agent.id,
            summary=f"Provide {resource_name} to support {request.title}.",
            price=price,
            estimated_duration=str(parameters.get("estimated_duration", "1 day")),
        )

    def _execute_request(self, architecture_instance: Any, scenario: Scenario, request: Request, parameters: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], bool]:
        resource_name = next(iter(request.required_resources), "unknown-resource")
        agent = self._choose_agent_for_request(scenario, request)
        proposal = self._build_proposal(scenario, request, agent, parameters)

        if hasattr(architecture_instance, "create_proposal"):
            architecture_instance.create_proposal(proposal)
        elif hasattr(architecture_instance, "publish_proposal"):
            architecture_instance.publish_proposal(proposal)
        elif hasattr(architecture_instance, "send_proposal"):
            architecture_instance.send_proposal(
                request=request,
                from_agent_id=agent.id,
                to_agent_id=request.requester_id,
                summary=proposal.summary,
                price=proposal.price,
                estimated_duration=proposal.estimated_duration,
            )

        decision = None
        if hasattr(architecture_instance, "evaluate_proposal"):
            decision = architecture_instance.evaluate_proposal(
                request=request,
                proposal=proposal,
                expected_value=float(parameters.get("expected_value", 200.0)),
                max_budget=float(parameters.get("max_budget", 150.0)),
                risk=float(parameters.get("risk", 10.0)),
            )

        if hasattr(architecture_instance, "start_negotiation") and hasattr(architecture_instance, "respond_to_message"):
            message = architecture_instance.start_negotiation(
                request=request,
                proposal=proposal,
                expected_value=float(parameters.get("expected_value", 200.0)),
                max_budget=float(parameters.get("max_budget", 150.0)),
                risk=float(parameters.get("risk", 10.0)),
            )
            response = architecture_instance.respond_to_message(
                message,
                next_step=__import__("one_credit.negotiation", fromlist=["AGREEMENT"]).AGREEMENT if decision in {"ACCEPT", "AGREEMENT"} else __import__("one_credit.negotiation", fromlist=["REJECT"]).REJECT,
                actor_id=request.requester_id,
                content="Agreement reached." if decision in {"ACCEPT", "AGREEMENT"} else "Proposal rejected.",
                price=proposal.price,
            )
            response_payload = {
                "type": response.type.value if hasattr(response, "type") else str(response),
                "request_id": request.id,
                "proposal_id": proposal.id,
                "actor_id": response.actor_id,
                "content": response.content,
                "price": response.price,
            }
            outcome = {
                "status": "success" if response.type.value in {"AGREEMENT", "ACCEPT"} else "failed",
                "request_id": request.id,
                "proposal_id": proposal.id,
                "allocation": None,
            }
            if hasattr(architecture_instance, "finalize_allocation"):
                allocation = architecture_instance.finalize_allocation(
                    request_id=request.id,
                    resource_name=resource_name,
                    agent_id=proposal.agent_id,
                    status="allocated" if outcome["status"] == "success" else "failed",
                )
                outcome["allocation"] = allocation
            return outcome, response_payload, self._extract_events(architecture_instance), self._extract_communication_messages(architecture_instance), outcome["status"] == "success"

        if hasattr(architecture_instance, "negotiate"):
            outcome = architecture_instance.negotiate(
                request=request,
                proposal=proposal,
                expected_value=float(parameters.get("expected_value", 200.0)),
                max_budget=float(parameters.get("max_budget", 150.0)),
                risk=float(parameters.get("risk", 10.0)),
            )
            response_payload = {"request_id": request.id, "proposal_id": proposal.id, "status": outcome.get("status", "failed")}
            return outcome, response_payload, self._extract_events(architecture_instance), self._extract_communication_messages(architecture_instance), outcome.get("status") == "success"

        if hasattr(architecture_instance, "accept_proposal"):
            result = architecture_instance.accept_proposal(
                request=request,
                proposal=proposal,
                actor_id=request.requester_id,
                content="Agreement reached.",
            )
            outcome = {"status": "success", "request_id": request.id, "proposal_id": proposal.id, "allocation": None}
            if hasattr(architecture_instance, "finalize_allocation"):
                outcome["allocation"] = architecture_instance.finalize_allocation(
                    request_id=request.id,
                    resource_name=resource_name,
                    agent_id=proposal.agent_id,
                )
            response_payload = {"request_id": request.id, "proposal_id": proposal.id, "type": str(result.type)}
            return outcome, response_payload, self._extract_events(architecture_instance), self._extract_communication_messages(architecture_instance), True

        raise ValueError(f"Architecture {type(architecture_instance).__name__} does not support runnable negotiation flows.")

    def _extract_events(self, architecture_instance: Any) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for attr_name in ("negotiation_events", "events"):
            value = getattr(architecture_instance, attr_name, None)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        events.append(item)
                    elif hasattr(item, "model_dump"):
                        events.append(item.model_dump())
        return events

    def _extract_communication_messages(self, architecture_instance: Any) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for attr_name in ("message_history", "messages"):
            value = getattr(architecture_instance, attr_name, None)
            if isinstance(value, list):
                for item in value:
                    if hasattr(item, "model_dump"):
                        messages.append(item.model_dump())
                    elif isinstance(item, dict):
                        messages.append(item)
        return messages

    def _capture_conflicts(self, architecture_instance: Any) -> list[dict[str, Any]]:
        if hasattr(architecture_instance, "detect_conflicts"):
            try:
                conflicts = architecture_instance.detect_conflicts()
                if isinstance(conflicts, list):
                    return [dict(conflict) for conflict in conflicts]
            except Exception:
                return []
        return []

    def run(self, scenario: Scenario | None = None, *, architecture: str | ArchitectureType | None = None) -> SimulationResult:
        if scenario is None:
            scenario = self.scenario
        if scenario is None:
            raise ValueError("A scenario must be provided before running the simulation.")

        if architecture is not None:
            scenario = Scenario.model_validate({
                **scenario.model_dump(),
                "architecture": architecture,
            })

        execution_start = time.perf_counter()
        architecture_name = scenario.architecture.value if isinstance(scenario.architecture, ArchitectureType) else str(scenario.architecture).upper()
        result = SimulationResult(
            architecture=architecture_name,
            simulation_id=scenario.scenario_id,
        )

        try:
            self.validate_scenario(scenario)
            architecture_class = self.select_architecture(scenario.architecture)
            architecture_instance = architecture_class(strategy=self.strategy)
            self._register_architecture(architecture_instance, scenario)
            self._register_requests(architecture_instance, scenario)

            parameters = self._coerce_parameters(scenario)
            final_allocation: dict[str, Any] = {}
            successful_negotiations: list[str] = []
            failed_negotiations: list[str] = []
            negotiation_events: list[dict[str, Any]] = []
            communication_messages: list[dict[str, Any]] = []
            unresolved_conflicts = self._capture_conflicts(architecture_instance)

            for request in scenario.requests:
                try:
                    outcome, response_payload, events_for_request, messages_for_request, is_successful = self._execute_request(
                        architecture_instance,
                        scenario,
                        request,
                        parameters,
                    )
                    negotiation_events.extend(events_for_request)
                    communication_messages.extend(messages_for_request)
                    if outcome.get("allocation"):
                        final_allocation[request.id] = outcome["allocation"]
                    if is_successful:
                        successful_negotiations.append(request.id)
                    else:
                        failed_negotiations.append(request.id)
                    if response_payload:
                        negotiation_events.append(response_payload)
                except ValueError as exc:
                    failed_negotiations.append(request.id)
                    result.errors.append(f"Request {request.id} failed: {exc}")

            if not result.errors:
                result.success = len(successful_negotiations) >= 1 or not failed_negotiations

            result.final_allocation = final_allocation
            result.successful_negotiations = successful_negotiations
            result.failed_negotiations = failed_negotiations
            result.unresolved_conflicts = unresolved_conflicts
            result.negotiation_events = negotiation_events
            result.negotiation_rounds = len(negotiation_events)
            result.communication_messages = communication_messages
            result.execution_time = time.perf_counter() - execution_start
            result.architecture = architecture_name
            if not result.errors and not successful_negotiations and failed_negotiations:
                result.success = False
        except Exception as exc:  # pragma: no cover - defensive fallback for invalid scenarios
            result.success = False
            result.errors.append(str(exc))
            result.execution_time = time.perf_counter() - execution_start
            result.architecture = architecture_name

        return result


__all__ = [
    "ArchitectureType",
    "Scenario",
    "SimulationEngine",
    "SimulationResult",
]

from __future__ import annotations

from collections import defaultdict
from typing import Any

from one_credit.models import Agent, Proposal, Request, Resource
from one_credit.negotiation import (
    ACCEPT,
    AGREEMENT,
    NegotiationEngine,
    NegotiationMessage,
    NegotiationStep,
    UtilityMaximizingStrategy,
)


class CentralizedArchitecture:
    """Central registry and entry point for the core One Credit backend domain."""

    def __init__(self, *, strategy: Any | None = None) -> None:
        self.agents: dict[str, Agent] = {}
        self.resources: dict[str, Resource] = {}
        self.requests: dict[str, Request] = {}
        self.proposals: dict[str, Proposal] = {}
        self.negotiation_engine = NegotiationEngine(strategy=strategy or UtilityMaximizingStrategy())

    def register_agent(self, agent: Agent) -> Agent:
        self.agents[agent.id] = agent
        return agent

    def register_resource(self, resource: Resource) -> Resource:
        self.resources[resource.id] = resource
        return resource

    def create_request(self, request: Request) -> Request:
        self.requests[request.id] = request
        return request

    def create_proposal(self, proposal: Proposal) -> Proposal:
        self.proposals[proposal.id] = proposal
        return proposal

    def get_agent(self, agent_id: str) -> Agent | None:
        return self.agents.get(agent_id)

    def get_resource(self, resource_id: str) -> Resource | None:
        return self.resources.get(resource_id)

    def get_request(self, request_id: str) -> Request | None:
        return self.requests.get(request_id)

    def get_proposal(self, proposal_id: str) -> Proposal | None:
        return self.proposals.get(proposal_id)

    def evaluate_proposal(
        self,
        *,
        request: Request,
        proposal: Proposal,
        expected_value: float = 0.0,
        max_budget: float = 0.0,
        risk: float = 0.0,
    ) -> NegotiationStep:
        return self.negotiation_engine.strategy.decide(
            request=request,
            proposal=proposal,
            expected_value=expected_value,
            max_budget=max_budget,
            risk=risk,
        )

    def start_negotiation(
        self,
        *,
        request: Request,
        proposal: Proposal,
        expected_value: float = 0.0,
        max_budget: float = 0.0,
        risk: float = 0.0,
    ) -> NegotiationMessage:
        return self.negotiation_engine.negotiate(
            request=request,
            proposal=proposal,
            expected_value=expected_value,
            max_budget=max_budget,
            risk=risk,
        )

    def respond_to_message(
        self,
        message: NegotiationMessage,
        *,
        next_step: NegotiationStep,
        actor_id: str,
        content: str | None = None,
        price: float | None = None,
    ) -> NegotiationMessage:
        return self.negotiation_engine.respond(
            message,
            next_step=next_step,
            actor_id=actor_id,
            content=content,
            price=price,
        )

    def accept_proposal(
        self,
        *,
        request: Request,
        proposal: Proposal,
        actor_id: str,
        content: str | None = None,
    ) -> NegotiationMessage:
        message = self.start_negotiation(request=request, proposal=proposal)
        return self.respond_to_message(
            message,
            next_step=ACCEPT,
            actor_id=actor_id,
            content=content or "Proposal accepted.",
            price=proposal.price,
        )

    def finalize_agreement(
        self,
        *,
        request: Request,
        proposal: Proposal,
        actor_id: str,
        content: str | None = None,
    ) -> NegotiationMessage:
        message = self.start_negotiation(request=request, proposal=proposal)
        return self.respond_to_message(
            message,
            next_step=AGREEMENT,
            actor_id=actor_id,
            content=content or "Agreement reached.",
            price=proposal.price,
        )


class HierarchicalArchitecture:
    """A three-level hierarchy where local managers resolve requests and escalate unresolved conflicts upward."""

    def __init__(self, *, strategy: Any | None = None) -> None:
        self.agents: dict[str, Agent] = {}
        self.managers: dict[str, Agent] = {}
        self.resources: dict[str, Resource] = {}
        self.requests: dict[str, Request] = {}
        self.proposals: dict[str, Proposal] = {}
        self.request_queues: defaultdict[str, list[str]] = defaultdict(list)
        self.allocations: dict[str, dict[str, Any]] = {}
        self.negotiation_engine = NegotiationEngine(strategy=strategy or UtilityMaximizingStrategy())
        self.negotiation_events: list[dict[str, Any]] = []
        self.escalation_events: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.campus_manager: Agent | None = None


class DecentralizedArchitecture:
    """Direct peer-to-peer negotiations without a central manager or hierarchy."""

    def __init__(self, *, strategy: Any | None = None) -> None:
        self.agents: dict[str, Agent] = {}
        self.resources: dict[str, Resource] = {}
        self.requests: dict[str, Request] = {}
        self.proposals: dict[str, Proposal] = {}
        self.allocations: dict[str, dict[str, Any]] = {}
        self.negotiation_engine = NegotiationEngine(strategy=strategy or UtilityMaximizingStrategy())
        self.negotiation_events: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []

    def _log_event(self, event_type: str, **payload: Any) -> dict[str, Any]:
        event = {"type": event_type, **payload}
        self.negotiation_events.append(event)
        self.events.append(event)
        return event

    def register_agent(self, agent: Agent) -> Agent:
        self.agents[agent.id] = agent
        return agent

    def register_resource(self, resource: Resource) -> Resource:
        self.resources[resource.id] = resource
        return resource

    def create_request(self, request: Request) -> Request:
        self.requests[request.id] = request
        return request

    def create_proposal(self, proposal: Proposal) -> Proposal:
        self.proposals[proposal.id] = proposal
        self._log_event("proposal", proposal_id=proposal.id, request_id=proposal.request_id, agent_id=proposal.agent_id)
        return proposal

    def get_agent(self, agent_id: str) -> Agent | None:
        return self.agents.get(agent_id)

    def get_resource(self, resource_id: str) -> Resource | None:
        return self.resources.get(resource_id)

    def get_request(self, request_id: str) -> Request | None:
        return self.requests.get(request_id)

    def get_proposal(self, proposal_id: str) -> Proposal | None:
        return self.proposals.get(proposal_id)

    def discover_agents_for_request(self, request: Request) -> list[Agent]:
        if not self.agents:
            return []

        required_resources = {item.lower() for item in request.required_resources}
        resource_names = {resource.name.lower() for resource in self.resources.values()}
        discovered: list[Agent] = []
        seen: set[str] = set()

        for agent in self.agents.values():
            token_set = {item.lower() for item in agent.capabilities} | {agent.type.lower()}
            matches_resource = bool(required_resources & resource_names)
            matches_agent = bool(required_resources & token_set)
            if agent.id == request.requester_id or matches_resource or matches_agent or not required_resources:
                if agent.id not in seen:
                    discovered.append(agent)
                    seen.add(agent.id)

        if not discovered:
            discovered = list(self.agents.values())
        return discovered

    def detect_conflicts(self, *, resource_name: str | None = None, request_ids: list[str] | None = None) -> list[dict[str, Any]]:
        candidates = list(self.requests.values())
        if resource_name is not None:
            candidates = [request for request in candidates if resource_name in request.required_resources]
        if request_ids is not None:
            candidate_ids = set(request_ids)
            candidates = [request for request in candidates if request.id in candidate_ids]

        by_resource: defaultdict[str, list[str]] = defaultdict(list)
        for request in candidates:
            for item in request.required_resources:
                by_resource[item].append(request.id)

        conflicts: list[dict[str, Any]] = []
        for resource, ids in by_resource.items():
            unique_ids = sorted(set(ids))
            if len(unique_ids) > 1:
                conflict = {"resource_name": resource, "request_ids": unique_ids, "status": "conflict"}
                conflicts.append(conflict)
                self._log_event("conflict", resource_name=resource, request_ids=unique_ids)

        return conflicts

    def send_proposal(
        self,
        *,
        request: Request,
        from_agent_id: str,
        to_agent_id: str,
        summary: str,
        price: float | None = None,
        estimated_duration: str | None = None,
    ) -> Proposal:
        proposal = Proposal(
            id=f"{request.id}-{from_agent_id}-proposal",
            request_id=request.id,
            agent_id=from_agent_id,
            summary=summary,
            price=price,
            estimated_duration=estimated_duration,
        )
        self.proposals[proposal.id] = proposal
        self._log_event(
            "proposal",
            proposal_id=proposal.id,
            request_id=request.id,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            price=price,
        )
        return proposal

    def evaluate_proposal(
        self,
        *,
        request: Request,
        proposal: Proposal,
        expected_value: float = 0.0,
        max_budget: float = 0.0,
        risk: float = 0.0,
    ) -> NegotiationStep:
        return self.negotiation_engine.strategy.decide(
            request=request,
            proposal=proposal,
            expected_value=expected_value,
            max_budget=max_budget,
            risk=risk,
        )

    def start_negotiation(
        self,
        *,
        request: Request,
        proposal: Proposal,
        expected_value: float = 0.0,
        max_budget: float = 0.0,
        risk: float = 0.0,
    ) -> NegotiationMessage:
        return self.negotiation_engine.negotiate(
            request=request,
            proposal=proposal,
            expected_value=expected_value,
            max_budget=max_budget,
            risk=risk,
        )

    def respond_to_message(
        self,
        message: NegotiationMessage,
        *,
        next_step: NegotiationStep,
        actor_id: str,
        content: str | None = None,
        price: float | None = None,
    ) -> NegotiationMessage:
        response = self.negotiation_engine.respond(
            message,
            next_step=next_step,
            actor_id=actor_id,
            content=content,
            price=price,
        )

        event_type = {
            NegotiationStep.COUNTEROFFER: "counteroffer",
            NegotiationStep.ACCEPT: "acceptance",
            NegotiationStep.REJECT: "rejection",
            NegotiationStep.AGREEMENT: "agreement",
        }.get(next_step, next_step.value.lower())
        self._log_event(
            event_type,
            message_id=response.id,
            request_id=response.request_id,
            proposal_id=response.proposal_id,
            actor_id=response.actor_id,
            price=response.price,
            content=response.content,
        )
        return response

    def accept_proposal(
        self,
        *,
        request: Request,
        proposal: Proposal,
        actor_id: str,
        content: str | None = None,
    ) -> NegotiationMessage:
        message = self.start_negotiation(request=request, proposal=proposal)
        return self.respond_to_message(
            message,
            next_step=ACCEPT,
            actor_id=actor_id,
            content=content or "Proposal accepted.",
            price=proposal.price,
        )

    def reject_proposal(
        self,
        *,
        request: Request,
        proposal: Proposal,
        actor_id: str,
        content: str | None = None,
    ) -> NegotiationMessage:
        message = self.start_negotiation(request=request, proposal=proposal)
        return self.respond_to_message(
            message,
            next_step=REJECT,
            actor_id=actor_id,
            content=content or "Proposal rejected.",
            price=proposal.price,
        )

    def record_unresolved_conflict(
        self,
        *,
        resource_name: str,
        request_ids: list[str],
        reason: str,
    ) -> dict[str, Any]:
        event = {
            "resource_name": resource_name,
            "request_ids": request_ids,
            "status": "unresolved",
            "reason": reason,
        }
        self._log_event("unresolved conflict", **event)
        return event

    def finalize_allocation(
        self,
        *,
        request_id: str,
        resource_name: str,
        agent_id: str,
        status: str = "allocated",
        price: float | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        allocation = {
            "request_id": request_id,
            "resource_name": resource_name,
            "agent_id": agent_id,
            "status": status,
        }
        if price is not None:
            allocation["price"] = price
        if reason is not None:
            allocation["reason"] = reason
        self.allocations[request_id] = allocation
        return allocation

    def get_final_allocation(self, request_id: str) -> dict[str, Any] | None:
        return self.allocations.get(request_id)

    def accept_or_reject_proposal(
        self,
        *,
        request: Request,
        proposal: Proposal,
        actor_id: str,
        accept: bool,
        content: str | None = None,
    ) -> NegotiationMessage:
        if accept:
            return self.accept_proposal(request=request, proposal=proposal, actor_id=actor_id, content=content)
        return self.reject_proposal(request=request, proposal=proposal, actor_id=actor_id, content=content)


class HierarchicalArchitecture:
    """A three-level hierarchy where local managers resolve requests and escalate unresolved conflicts upward."""

    def __init__(self, *, strategy: Any | None = None) -> None:
        self.agents: dict[str, Agent] = {}
        self.managers: dict[str, Agent] = {}
        self.resources: dict[str, Resource] = {}
        self.requests: dict[str, Request] = {}
        self.proposals: dict[str, Proposal] = {}
        self.request_queues: defaultdict[str, list[str]] = defaultdict(list)
        self.allocations: dict[str, dict[str, Any]] = {}
        self.negotiation_engine = NegotiationEngine(strategy=strategy or UtilityMaximizingStrategy())
        self.negotiation_events: list[dict[str, Any]] = []
        self.escalation_events: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.campus_manager: Agent | None = None

    def register_manager(
        self,
        manager: Agent,
        *,
        parent_manager_id: str | None = None,
        level: int | None = None,
    ) -> Agent:
        self.managers[manager.id] = manager
        manager.metadata.setdefault("manager", True)
        manager.metadata.setdefault("level", level if level is not None else (1 if parent_manager_id is None else 2))
        if parent_manager_id is not None:
            manager.metadata["parent_manager_id"] = parent_manager_id
        if self.campus_manager is None or manager.type.lower() == "campus_manager":
            self.campus_manager = manager
        return manager

    def get_manager(self, manager_id: str) -> Agent | None:
        return self.managers.get(manager_id)

    def get_manager_for_agent(self, agent_id: str) -> str | None:
        agent = self.agents.get(agent_id)
        if agent is None:
            return None
        return agent.metadata.get("manager_id")

    def register_agent(self, agent: Agent, *, manager_id: str | None = None) -> Agent:
        self.agents[agent.id] = agent
        if manager_id is not None:
            self.assign_manager(agent.id, manager_id)
        elif self.campus_manager is not None:
            self.assign_manager(agent.id, self.campus_manager.id)
        return agent

    def assign_manager(self, agent_id: str, manager_id: str) -> Agent:
        agent = self.agents.get(agent_id)
        if agent is None:
            raise KeyError(f"Agent {agent_id} is not registered")
        if manager_id not in self.managers and self.campus_manager is not None and manager_id != self.campus_manager.id:
            raise KeyError(f"Manager {manager_id} is not registered")
        agent.metadata["manager_id"] = manager_id
        return agent

    def register_resource(self, resource: Resource) -> Resource:
        self.resources[resource.id] = resource
        return resource

    def get_agent(self, agent_id: str) -> Agent | None:
        return self.agents.get(agent_id)

    def get_resource(self, resource_id: str) -> Resource | None:
        return self.resources.get(resource_id)

    def get_request(self, request_id: str) -> Request | None:
        return self.requests.get(request_id)

    def get_proposal(self, proposal_id: str) -> Proposal | None:
        return self.proposals.get(proposal_id)

    def create_request(self, request: Request) -> Request:
        return self.submit_request(agent_id=request.requester_id, request=request)

    def submit_request(self, *, agent_id: str, request: Request) -> Request:
        manager_id = self.get_manager_for_agent(agent_id)
        if manager_id is None:
            if self.campus_manager is None:
                raise KeyError("A campus manager must be registered before routing requests")
            manager_id = self.campus_manager.id
            self.assign_manager(agent_id, manager_id)
        self.requests[request.id] = request
        request.metadata["manager_id"] = manager_id
        request.status = "queued"
        self.request_queues[manager_id].append(request.id)
        return request

    def create_proposal(self, proposal: Proposal) -> Proposal:
        self.proposals[proposal.id] = proposal
        return proposal

    def detect_local_conflicts(self, manager_id: str, request_ids: list[str] | None = None) -> list[dict[str, Any]]:
        manager_requests = self.request_queues.get(manager_id, [])
        if request_ids is not None:
            manager_requests = [request_id for request_id in manager_requests if request_id in set(request_ids)]

        by_resource: dict[str, list[str]] = defaultdict(list)
        for request_id in manager_requests:
            request = self.requests.get(request_id)
            if request is None:
                continue
            for resource_name in request.required_resources:
                by_resource[resource_name].append(request_id)

        conflicts: list[dict[str, Any]] = []
        for resource_name, request_ids_for_resource in by_resource.items():
            unique_ids = sorted(set(request_ids_for_resource))
            if len(unique_ids) > 1:
                conflicts.append({"resource": resource_name, "request_ids": unique_ids})
        return conflicts

    def _build_proposal_for_request(self, request: Request) -> Proposal:
        proposal = Proposal(
            id=f"{request.id}-proposal",
            request_id=request.id,
            agent_id=request.requester_id,
            summary=f"Manager review for {request.title}",
            price=50.0 if request.priority == "high" else 25.0,
            estimated_duration="1 day",
        )
        self.proposals[proposal.id] = proposal
        return proposal

    def record_negotiation_event(self, *, manager_id: str, request_ids: list[str], proposal: Proposal, message: NegotiationMessage) -> None:
        event = {
            "type": "negotiation",
            "manager_id": manager_id,
            "request_ids": request_ids,
            "proposal_id": proposal.id,
            "message_id": message.id,
            "content": message.content,
            "step": message.type.value,
        }
        self.negotiation_events.append(event)
        self.events.append(event)

    def record_escalation_event(self, *, manager_id: str, request_ids: list[str], to_manager_id: str, reason: str) -> None:
        event = {
            "type": "escalation",
            "from_manager_id": manager_id,
            "to_manager_id": to_manager_id,
            "request_ids": request_ids,
            "reason": reason,
        }
        self.escalation_events.append(event)
        self.events.append(event)

    def resolve_local_conflict(self, manager_id: str, request_ids: list[str]) -> dict[str, Any]:
        local_requests = [self.requests[request_id] for request_id in request_ids if request_id in self.requests]
        if not local_requests:
            return {"manager_id": manager_id, "resolved_requests": [], "status": "failed"}

        winner = sorted(local_requests, key=lambda req: (req.priority.lower() != "high", req.priority.lower() != "medium"))[0]
        proposal = self._build_proposal_for_request(winner)
        message = self.negotiation_engine.negotiate(request=winner, proposal=proposal)
        self.record_negotiation_event(manager_id=manager_id, request_ids=request_ids, proposal=proposal, message=message)

        result = {
            "manager_id": manager_id,
            "resolved_requests": [request.id for request in local_requests],
            "winner_request_id": winner.id,
            "status": "resolved",
            "resource": next(iter(winner.required_resources), "unknown"),
        }
        self.finalize_allocation(
            request_id=winner.id,
            resource_name=result["resource"],
            agent_id=winner.requester_id,
            manager_id=manager_id,
        )
        return result

    def escalate_conflict(self, manager_id: str, request_ids: list[str], *, reason: str) -> dict[str, Any]:
        if self.campus_manager is None:
            raise KeyError("Campus manager has not been registered")
        self.record_escalation_event(
            manager_id=manager_id,
            request_ids=request_ids,
            to_manager_id=self.campus_manager.id,
            reason=reason,
        )
        campus_result = {
            "manager_id": manager_id,
            "to_manager_id": self.campus_manager.id,
            "request_ids": request_ids,
            "reason": reason,
            "status": "escalated",
        }
        return campus_result

    def process_manager_requests(self, manager_id: str, *, force_escalation: bool = False) -> dict[str, Any]:
        queued = list(self.request_queues.get(manager_id, []))
        conflicts = self.detect_local_conflicts(manager_id)

        if not conflicts and queued:
            for request_id in queued:
                request = self.requests.get(request_id)
                if request is None:
                    continue
                self.finalize_allocation(
                    request_id=request.id,
                    resource_name=next(iter(request.required_resources), "unknown"),
                    agent_id=request.requester_id,
                    manager_id=manager_id,
                )
            return {"manager_id": manager_id, "status": "allocated", "conflicts": conflicts, "requests": queued}

        if conflicts:
            for conflict in conflicts:
                resolved = self.resolve_local_conflict(manager_id, conflict["request_ids"])
                if force_escalation or not resolved["resolved_requests"]:
                    escalation = self.escalate_conflict(manager_id, conflict["request_ids"], reason="Unresolved local conflict")
                    return {"manager_id": manager_id, "status": escalation["status"], "conflicts": conflicts, "escalation": escalation}
                return {"manager_id": manager_id, "status": "allocated", "conflicts": conflicts, "resolved": resolved}

        return {"manager_id": manager_id, "status": "allocated", "conflicts": conflicts, "requests": queued}

    def finalize_allocation(
        self,
        *,
        request_id: str,
        resource_name: str,
        agent_id: str,
        manager_id: str,
    ) -> dict[str, Any]:
        allocation = {
            "request_id": request_id,
            "resource_name": resource_name,
            "agent_id": agent_id,
            "manager_id": manager_id,
            "status": "allocated",
        }
        self.allocations[request_id] = allocation
        return allocation

    def get_final_allocation(self, request_id: str) -> dict[str, Any] | None:
        return self.allocations.get(request_id)

    def fail_allocation(
        self,
        *,
        request_id: str,
        resource_name: str,
        agent_id: str,
        manager_id: str,
        reason: str,
    ) -> dict[str, Any]:
        allocation = {
            "request_id": request_id,
            "resource_name": resource_name,
            "agent_id": agent_id,
            "manager_id": manager_id,
            "status": "failed",
            "reason": reason,
        }
        self.allocations[request_id] = allocation
        return allocation

    def allocate_resources(self) -> dict[str, dict[str, Any]]:
        return dict(self.allocations)

    def route_request(self, request: Request) -> Request:
        return self.submit_request(agent_id=request.requester_id, request=request)

    def resolve_conflict(self, manager_id: str, request_ids: list[str]) -> dict[str, Any]:
        return self.resolve_local_conflict(manager_id, request_ids)

    def get_allocation(self, request_id: str) -> dict[str, Any] | None:
        return self.get_final_allocation(request_id)

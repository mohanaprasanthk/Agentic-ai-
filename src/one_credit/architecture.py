from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Any

from one_credit.blackboard import Blackboard
from one_credit.models import Agent, Message, MessageType, Proposal, Request, Resource
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


class SequentialArchitecture:
    """A strictly ordered negotiation pipeline for request handling and allocation."""

    STAGES = [
        "request_validation",
        "priority_evaluation",
        "resource_availability_check",
        "conflict_detection",
        "negotiation",
        "allocation",
        "confirmation",
    ]

    def __init__(self, *, strategy: Any | None = None) -> None:
        self.agents: dict[str, Agent] = {}
        self.resources: dict[str, Resource] = {}
        self.requests: dict[str, Request] = {}
        self.proposals: dict[str, Proposal] = {}
        self.allocations: dict[str, dict[str, Any]] = {}
        self.negotiation_engine = NegotiationEngine(strategy=strategy or UtilityMaximizingStrategy())
        self.stage_results: dict[str, Any] = {}
        self.stage_processing_times: dict[str, float] = {}
        self.negotiation_events: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.latest_result: dict[str, Any] | None = None

    def _record_stage(self, stage_name: str, result: Any, start_time: float) -> Any:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        self.stage_results[stage_name] = result
        self.stage_processing_times[stage_name] = round(elapsed_ms, 6)
        self.events.append({"stage": stage_name, "result": result, "duration_ms": self.stage_processing_times[stage_name]})
        return result

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

    def validate_request(self, request: Request) -> dict[str, Any]:
        valid = bool(request.title and request.requester_id)
        result = {
            "stage": "request_validation",
            "status": "passed" if valid else "failed",
            "request_id": request.id,
            "valid": valid,
            "reason": "Request is valid." if valid else "Request validation failed.",
        }
        return result

    def evaluate_priority(self, request: Request) -> dict[str, Any]:
        priority_scores = {"low": 1, "normal": 2, "medium": 3, "high": 4, "critical": 5}
        score = priority_scores.get(str(request.priority).lower(), 2)
        return {
            "stage": "priority_evaluation",
            "status": "passed",
            "request_id": request.id,
            "priority": request.priority,
            "score": score,
            "decision": "continue",
        }

    def check_resource_availability(self, *, request: Request, resource_name: str | None = None) -> dict[str, Any]:
        target = resource_name or next(iter(request.required_resources), None)
        if target is None:
            return {"stage": "resource_availability_check", "status": "failed", "request_id": request.id, "resource_name": None, "available": False, "reason": "No resource specified."}

        resource = next((candidate for candidate in self.resources.values() if candidate.name.lower() == target.lower()), None)
        available = resource is not None
        return {
            "stage": "resource_availability_check",
            "status": "passed" if available else "failed",
            "request_id": request.id,
            "resource_name": target,
            "available": available,
            "reason": "Resource is available." if available else "Resource is unavailable.",
        }

    def detect_conflicts(self, *, resource_name: str | None = None) -> list[dict[str, Any]]:
        resource_filter = (resource_name or "").lower()
        conflicts: list[dict[str, Any]] = []
        by_resource: defaultdict[str, list[str]] = defaultdict(list)

        for request in self.requests.values():
            for required in request.required_resources:
                if resource_filter and required.lower() != resource_filter:
                    continue
                by_resource[required.lower()].append(request.id)

        for resource_key, request_ids in by_resource.items():
            unique_ids = sorted(set(request_ids))
            if len(unique_ids) > 1:
                conflicts.append({"resource_name": resource_key, "request_ids": unique_ids, "status": "conflict"})

        return conflicts

    def negotiate(
        self,
        *,
        request: Request,
        proposal: Proposal | None = None,
        expected_value: float = 0.0,
        max_budget: float = 0.0,
        risk: float = 0.0,
    ) -> dict[str, Any]:
        if proposal is None:
            candidate_agent = next(iter(self.agents.values()), None)
            if candidate_agent is None:
                return {"stage": "negotiation", "status": "failed", "request_id": request.id, "reason": "No agent available to negotiate."}
            resource_name = next(iter(request.required_resources), "resource")
            proposal = Proposal(
                id=f"{request.id}-{candidate_agent.id}-proposal",
                request_id=request.id,
                agent_id=candidate_agent.id,
                summary=f"Provide {resource_name} for this request.",
                price=0.0,
            )
            self.proposals[proposal.id] = proposal

        first_message = self.negotiation_engine.negotiate(
            request=request,
            proposal=proposal,
            expected_value=expected_value,
            max_budget=max_budget,
            risk=risk,
        )
        self.negotiation_events.append({
            "type": "proposal",
            "message_id": first_message.id,
            "request_id": request.id,
            "proposal_id": proposal.id,
            "actor_id": proposal.agent_id,
            "content": first_message.content,
            "price": first_message.price,
        })

        decision = self.negotiation_engine.strategy.decide(
            request=request,
            proposal=proposal,
            expected_value=expected_value,
            max_budget=max_budget,
            risk=risk,
        )
        if decision in {ACCEPT, AGREEMENT}:
            response = self.negotiation_engine.respond(
                first_message,
                next_step=AGREEMENT,
                actor_id=request.requester_id,
                content="Agreement reached.",
                price=proposal.price,
            )
            self.negotiation_events.append({
                "type": "agreement",
                "message_id": response.id,
                "request_id": request.id,
                "proposal_id": proposal.id,
                "actor_id": response.actor_id,
                "content": response.content,
                "price": response.price,
            })
            return {"stage": "negotiation", "status": "passed", "request_id": request.id, "proposal_id": proposal.id, "decision": decision.value, "message": response.content}

        response = self.negotiation_engine.respond(
            first_message,
            next_step=NegotiationStep.REJECT,
            actor_id=request.requester_id,
            content="Negotiation failed.",
            price=proposal.price,
        )
        self.negotiation_events.append({
            "type": "rejection",
            "message_id": response.id,
            "request_id": request.id,
            "proposal_id": proposal.id,
            "actor_id": response.actor_id,
            "content": response.content,
            "price": response.price,
        })
        return {"stage": "negotiation", "status": "failed", "request_id": request.id, "proposal_id": proposal.id, "decision": decision.value, "reason": "Negotiation failed."}

    def allocate_resource(
        self,
        *,
        request: Request,
        resource_name: str | None = None,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        target = resource_name or next(iter(request.required_resources), "unknown")
        owner = agent_id or request.requester_id
        allocation = {"request_id": request.id, "resource_name": target, "agent_id": owner, "status": "allocated"}
        self.allocations[request.id] = allocation
        return {"stage": "allocation", "status": "passed", "allocation": allocation}

    def confirm_allocation(self, *, request: Request, allocation: dict[str, Any]) -> dict[str, Any]:
        return {"stage": "confirmation", "status": "passed", "request_id": request.id, "allocation": allocation, "message": "Allocation confirmed."}

    def run_pipeline(
        self,
        *,
        request: Request,
        resource_name: str | None = None,
        proposal: Proposal | None = None,
        agent_id: str | None = None,
        expected_value: float = 0.0,
        max_budget: float = 0.0,
        risk: float = 0.0,
    ) -> dict[str, Any]:
        self.stage_results = {}
        self.stage_processing_times = {}
        self.negotiation_events = []
        self.events = []
        self.requests[request.id] = request

        final_allocation: dict[str, Any] | None = None
        overall_result = "success"

        for stage_name in self.STAGES:
            start_time = time.perf_counter()
            if stage_name == "request_validation":
                stage_result = self.validate_request(request)
                self._record_stage(stage_name, stage_result, start_time)
                if stage_result["status"] != "passed":
                    overall_result = "failed"
                    break
                continue

            if stage_name == "priority_evaluation":
                stage_result = self.evaluate_priority(request)
                self._record_stage(stage_name, stage_result, start_time)
                continue

            if stage_name == "resource_availability_check":
                stage_result = self.check_resource_availability(request=request, resource_name=resource_name)
                self._record_stage(stage_name, stage_result, start_time)
                if stage_result["status"] != "passed":
                    overall_result = "failed"
                    break
                continue

            if stage_name == "conflict_detection":
                resource_to_check = resource_name or next(iter(request.required_resources), None)
                conflicts = self.detect_conflicts(resource_name=resource_to_check)
                stage_result = {
                    "stage": "conflict_detection",
                    "status": "passed" if not conflicts else "conflict",
                    "request_id": request.id,
                    "resource_name": resource_to_check,
                    "conflicts": conflicts,
                    "reason": "No conflict detected." if not conflicts else "Conflict detected.",
                }
                self._record_stage(stage_name, stage_result, start_time)
                continue

            if stage_name == "negotiation":
                resource_to_check = resource_name or next(iter(request.required_resources), None)
                conflicts = self.detect_conflicts(resource_name=resource_to_check)
                if not conflicts:
                    stage_result = {"stage": "negotiation", "status": "skipped", "request_id": request.id, "resource_name": resource_to_check, "reason": "No conflict detected; negotiation skipped."}
                    self._record_stage(stage_name, stage_result, start_time)
                    continue

                stage_result = self.negotiate(
                    request=request,
                    proposal=proposal,
                    expected_value=expected_value,
                    max_budget=max_budget,
                    risk=risk,
                )
                self._record_stage(stage_name, stage_result, start_time)
                if stage_result["status"] != "passed":
                    overall_result = "failed"
                    break
                continue

            if stage_name == "allocation":
                if overall_result == "failed":
                    break
                resource_to_check = resource_name or next(iter(request.required_resources), None)
                stage_result = self.allocate_resource(request=request, resource_name=resource_to_check, agent_id=agent_id)
                self._record_stage(stage_name, stage_result, start_time)
                final_allocation = stage_result["allocation"]
                continue

            if stage_name == "confirmation":
                if final_allocation is None:
                    stage_result = {"stage": "confirmation", "status": "skipped", "request_id": request.id, "reason": "No allocation to confirm."}
                    self._record_stage(stage_name, stage_result, start_time)
                    overall_result = "failed"
                    break
                stage_result = self.confirm_allocation(request=request, allocation=final_allocation)
                self._record_stage(stage_name, stage_result, start_time)

        pipeline_result = {
            "final_allocation": final_allocation,
            "overall_result": overall_result,
            "stage_results": self.stage_results,
            "stage_processing_times": self.stage_processing_times,
            "negotiation_events": self.negotiation_events,
        }
        self.latest_result = pipeline_result
        return pipeline_result

    def process_request(self, *, request: Request, resource_name: str | None = None, proposal: Proposal | None = None, agent_id: str | None = None, expected_value: float = 0.0, max_budget: float = 0.0, risk: float = 0.0) -> dict[str, Any]:
        return self.run_pipeline(
            request=request,
            resource_name=resource_name,
            proposal=proposal,
            agent_id=agent_id,
            expected_value=expected_value,
            max_budget=max_budget,
            risk=risk,
        )

    def execute_pipeline(self, *, request: Request, resource_name: str | None = None, proposal: Proposal | None = None, agent_id: str | None = None, expected_value: float = 0.0, max_budget: float = 0.0, risk: float = 0.0) -> dict[str, Any]:
        return self.run_pipeline(
            request=request,
            resource_name=resource_name,
            proposal=proposal,
            agent_id=agent_id,
            expected_value=expected_value,
            max_budget=max_budget,
            risk=risk,
        )


class ParallelArchitecture(CentralizedArchitecture):
    """Concurrent negotiation coordinator with resource-level synchronization."""

    def __init__(self, *, strategy: Any | None = None) -> None:
        super().__init__(strategy=strategy or UtilityMaximizingStrategy())
        self.allocations: dict[str, dict[str, Any]] = {}
        self.resource_allocations: dict[str, str] = {}
        self.resource_locks: dict[str, asyncio.Lock] = {}
        self.negotiation_events: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.negotiation_records: list[dict[str, Any]] = []

    def _resource_key(self, resource_name: str | None) -> str:
        return (resource_name or "unknown").strip().lower()

    def _request_sort_key(self, request: Request) -> tuple[int, str]:
        priority_order = {"critical": 5, "high": 4, "medium": 3, "normal": 2, "low": 1}
        priority_score = priority_order.get(str(request.priority).lower(), 2)
        return (-priority_score, request.id)

    def _resource_lock(self, resource_name: str | None) -> asyncio.Lock:
        key = self._resource_key(resource_name)
        if key not in self.resource_locks:
            self.resource_locks[key] = asyncio.Lock()
        return self.resource_locks[key]

    def _requests_for_resource(self, resource_name: str | None) -> list[Request]:
        key = self._resource_key(resource_name)
        candidates = []
        for request in self.requests.values():
            required = {self._resource_key(item) for item in request.required_resources}
            if key in required:
                candidates.append(request)
        return sorted(candidates, key=self._request_sort_key)

    async def allocate_resource(
        self,
        *,
        request: Request,
        resource_name: str | None = None,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        target = resource_name or next(iter(request.required_resources), "unknown")
        lock = self._resource_lock(target)

        async with lock:
            ordered_requests = self._requests_for_resource(target)
            if ordered_requests and ordered_requests[0].id != request.id:
                return {
                    "status": "failed",
                    "request_id": request.id,
                    "resource_name": target,
                    "allocation": None,
                    "reason": "Resource is reserved for a higher-priority request.",
                }

            if self.resource_allocations.get(target) and self.resource_allocations[target] != request.id:
                return {
                    "status": "failed",
                    "request_id": request.id,
                    "resource_name": target,
                    "allocation": None,
                    "reason": "Resource is already allocated to another request.",
                }

            allocation = {
                "request_id": request.id,
                "resource_name": target,
                "agent_id": agent_id or request.requester_id,
                "status": "allocated",
            }
            self.allocations[request.id] = allocation
            self.resource_allocations[target] = request.id
            request.status = "allocated"
            return {
                "status": "passed",
                "request_id": request.id,
                "resource_name": target,
                "allocation": allocation,
            }

    async def _run_single_negotiation(
        self,
        *,
        request: Request,
        proposal: Proposal | None = None,
        expected_value: float = 0.0,
        max_budget: float = 0.0,
        risk: float = 0.0,
    ) -> dict[str, Any]:
        start_time = time.perf_counter()
        messages: list[dict[str, Any]] = []

        if proposal is not None and expected_value <= 0.0:
            expected_value = max(100.0, (proposal.price or 0.0) + 10.0)
        if proposal is not None and max_budget <= 0.0:
            max_budget = max(100.0, (proposal.price or 0.0) + 10.0)

        if proposal is None:
            candidate = next(iter(sorted(self.agents.values(), key=lambda agent: agent.id)), None)
            if candidate is None:
                end_time = time.perf_counter()
                record = {
                    "request_id": request.id,
                    "resource_name": next(iter(request.required_resources), "unknown"),
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_seconds": end_time - start_time,
                    "result": "failed",
                    "allocation": None,
                    "messages": messages,
                    "events": messages,
                    "reason": "No agent available to negotiate.",
                }
                self.negotiation_records.append(record)
                return record

            resource_name = next(iter(request.required_resources), "resource")
            proposal = Proposal(
                id=f"{request.id}-{candidate.id}-proposal",
                request_id=request.id,
                agent_id=candidate.id,
                summary=f"Provide {resource_name} for {request.title}.",
                price=0.0,
            )
            self.proposals[proposal.id] = proposal

        self.requests[request.id] = request
        first_message = self.negotiation_engine.negotiate(
            request=request,
            proposal=proposal,
            expected_value=expected_value,
            max_budget=max_budget,
            risk=risk,
        )
        message_event = {
            "type": "proposal",
            "message_id": first_message.id,
            "request_id": request.id,
            "proposal_id": proposal.id,
            "actor_id": proposal.agent_id,
            "content": first_message.content,
            "price": first_message.price,
        }
        self.negotiation_events.append(message_event)
        self.events.append(message_event)
        messages.append(message_event)

        decision = self.negotiation_engine.strategy.decide(
            request=request,
            proposal=proposal,
            expected_value=expected_value,
            max_budget=max_budget,
            risk=risk,
        )

        if decision in {ACCEPT, AGREEMENT}:
            response = self.negotiation_engine.respond(
                first_message,
                next_step=AGREEMENT,
                actor_id=request.requester_id,
                content="Agreement reached.",
                price=proposal.price,
            )
            response_event = {
                "type": "agreement",
                "message_id": response.id,
                "request_id": request.id,
                "proposal_id": proposal.id,
                "actor_id": response.actor_id,
                "content": response.content,
                "price": response.price,
            }
            self.negotiation_events.append(response_event)
            self.events.append(response_event)
            messages.append(response_event)

            allocation_result = await self.allocate_resource(
                request=request,
                resource_name=next(iter(request.required_resources), "unknown"),
                agent_id=proposal.agent_id,
            )
            end_time = time.perf_counter()
            record = {
                "request_id": request.id,
                "resource_name": next(iter(request.required_resources), "unknown"),
                "start_time": start_time,
                "end_time": end_time,
                "duration_seconds": end_time - start_time,
                "result": "success" if allocation_result["status"] == "passed" else "failed",
                "allocation": allocation_result.get("allocation"),
                "messages": messages,
                "events": messages,
                "decision": decision.value,
            }
            self.negotiation_records.append(record)
            return record

        response = self.negotiation_engine.respond(
            first_message,
            next_step=NegotiationStep.REJECT,
            actor_id=request.requester_id,
            content="Negotiation failed.",
            price=proposal.price,
        )
        response_event = {
            "type": "rejection",
            "message_id": response.id,
            "request_id": request.id,
            "proposal_id": proposal.id,
            "actor_id": response.actor_id,
            "content": response.content,
            "price": response.price,
        }
        self.negotiation_events.append(response_event)
        self.events.append(response_event)
        messages.append(response_event)

        end_time = time.perf_counter()
        record = {
            "request_id": request.id,
            "resource_name": next(iter(request.required_resources), "unknown"),
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": end_time - start_time,
            "result": "failed",
            "allocation": None,
            "messages": messages,
            "events": messages,
            "decision": decision.value,
            "reason": "Negotiation failed.",
        }
        self.negotiation_records.append(record)
        return record

    async def execute_negotiations(
        self,
        *,
        requests: list[Request] | None = None,
        proposals: dict[str, Proposal] | None = None,
    ) -> list[dict[str, Any]]:
        requests_to_process = list(requests) if requests is not None else list(self.requests.values())
        proposals_by_id = proposals or {}
        ordered = sorted(requests_to_process, key=self._request_sort_key)
        tasks = [
            asyncio.create_task(self._run_single_negotiation(request=request, proposal=proposals_by_id.get(request.id)))
            for request in ordered
        ]
        if not tasks:
            return []
        return list(await asyncio.gather(*tasks))

    async def execute_concurrently(
        self,
        *,
        requests: list[Request] | None = None,
        proposals: dict[str, Proposal] | None = None,
    ) -> list[dict[str, Any]]:
        return await self.execute_negotiations(requests=requests, proposals=proposals)

    async def run_parallel(
        self,
        *,
        requests: list[Request] | None = None,
        proposals: dict[str, Proposal] | None = None,
    ) -> list[dict[str, Any]]:
        return await self.execute_negotiations(requests=requests, proposals=proposals)

    async def process_request(
        self,
        *,
        request: Request,
        proposal: Proposal | None = None,
        expected_value: float = 0.0,
        max_budget: float = 0.0,
        risk: float = 0.0,
    ) -> dict[str, Any]:
        return await self._run_single_negotiation(
            request=request,
            proposal=proposal,
            expected_value=expected_value,
            max_budget=max_budget,
            risk=risk,
        )


class BlackboardArchitecture:
    """Shared-state coordination layer without a central manager."""

    def __init__(self, *, strategy: Any | None = None) -> None:
        self.agents: dict[str, Agent] = {}
        self.resources: dict[str, Resource] = {}
        self.requests: dict[str, Request] = {}
        self.proposals: dict[str, Proposal] = {}
        self.negotiation_engine = NegotiationEngine(strategy=strategy or UtilityMaximizingStrategy())
        self.blackboard = Blackboard()

    def register_agent(self, agent: Agent) -> Agent:
        self.agents[agent.id] = agent
        return agent

    def register_resource(self, resource: Resource) -> Resource:
        self.resources[resource.id] = resource
        self.blackboard.register_resource_status(resource.name, status="available")
        return resource

    def register_resource_status(self, resource_name: str, status: str = "available", **metadata: Any) -> dict[str, Any]:
        return self.blackboard.register_resource_status(resource_name, status=status, **metadata)

    def get_resource_status(self, resource_name: str) -> dict[str, Any] | None:
        return self.blackboard.resource_status.get(resource_name)

    def create_request(self, request: Request) -> Request:
        self.requests[request.id] = request
        self.blackboard.register_request(request)
        return request

    def register_request(self, request: Request) -> Request:
        return self.create_request(request)

    def read_request(self, request_id: str) -> Request | None:
        return self.blackboard.get_request(request_id)

    def get_request(self, request_id: str) -> Request | None:
        return self.read_request(request_id)

    def read_requests(self) -> list[Request]:
        return self.blackboard.get_requests()

    def get_requests(self) -> list[Request]:
        return self.read_requests()

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

    def detect_conflicts(self) -> list[dict[str, Any]]:
        by_resource: defaultdict[str, list[str]] = defaultdict(list)
        for request in self.blackboard.get_requests():
            for resource_name in request.required_resources:
                by_resource[resource_name].append(request.id)

        conflicts: list[dict[str, Any]] = []
        for resource_name, request_ids in by_resource.items():
            unique_ids = sorted(set(request_ids))
            if len(unique_ids) > 1:
                conflict = {"resource_name": resource_name, "request_ids": unique_ids, "status": "conflict"}
                self.blackboard.register_conflict(conflict)
                conflicts.append(conflict)
        return conflicts

    def record_unresolved_conflict(self, resource_name: str, request_ids: list[str], reason: str) -> dict[str, Any]:
        conflict = {
            "resource_name": resource_name,
            "request_ids": list(request_ids),
            "status": "unresolved",
            "reason": reason,
        }
        self.blackboard.register_conflict(conflict)
        return conflict

    def publish_proposal(self, proposal: Proposal) -> Proposal:
        self.proposals[proposal.id] = proposal
        self.blackboard.register_proposal(proposal)
        return proposal

    def read_proposals_for_agent(self, agent_id: str) -> list[Proposal]:
        return [proposal for proposal in self.blackboard.proposals.values() if proposal.agent_id == agent_id]

    def read_proposals(self) -> list[Proposal]:
        return list(self.blackboard.proposals.values())

    def publish_counteroffer(
        self,
        *,
        request_id: str,
        proposal_id: str,
        from_agent_id: str,
        to_agent_id: str,
        content: str,
        price: float | None = None,
    ) -> dict[str, Any]:
        counteroffer = {
            "id": f"counteroffer-{request_id}-{proposal_id}-{from_agent_id}",
            "request_id": request_id,
            "proposal_id": proposal_id,
            "from_agent_id": from_agent_id,
            "to_agent_id": to_agent_id,
            "content": content,
            "price": price,
            "status": "countered",
        }
        return self.blackboard.register_counteroffer(counteroffer)

    def read_counteroffers_for_agent(self, agent_id: str) -> list[dict[str, Any]]:
        values = list(self.blackboard.counteroffers.values())
        return [counteroffer for counteroffer in values if counteroffer.get("from_agent_id") == agent_id or counteroffer.get("to_agent_id") == agent_id]

    def publish_agreement(
        self,
        *,
        request_id: str,
        resource_name: str,
        agent_id: str,
        proposal_id: str,
        content: str,
    ) -> dict[str, Any]:
        agreement = {
            "id": f"agreement-{request_id}-{agent_id}",
            "request_id": request_id,
            "resource_name": resource_name,
            "agent_id": agent_id,
            "proposal_id": proposal_id,
            "content": content,
            "status": "agreed",
        }
        self.blackboard.register_agreement(agreement)
        return agreement

    def record_negotiation_event(self, event_type: str, **payload: Any) -> dict[str, Any]:
        return self.blackboard.record_event(event_type, **payload)

    def inspect_blackboard(self) -> dict[str, Any]:
        return self.blackboard.inspect_state()

    def finalize_allocation(
        self,
        *,
        request_id: str,
        resource_name: str,
        agent_id: str,
        status: str = "allocated",
        **metadata: Any,
    ) -> dict[str, Any]:
        allocation = self.blackboard.finalize_allocation(
            request_id=request_id,
            resource_name=resource_name,
            agent_id=agent_id,
            status=status,
            **metadata,
        )
        return allocation

    def get_final_allocation(self, request_id: str) -> dict[str, Any] | None:
        return self.blackboard.get_final_allocation(request_id)

    def negotiate(
        self,
        *,
        request: Request,
        proposal: Proposal,
        expected_value: float = 0.0,
        max_budget: float = 0.0,
        risk: float = 0.0,
    ) -> dict[str, Any]:
        if proposal is None:
            raise ValueError("A proposal is required for blackboard negotiation.")

        message = self.start_negotiation(
            request=request,
            proposal=proposal,
            expected_value=expected_value,
            max_budget=max_budget,
            risk=risk,
        )
        decision = self.evaluate_proposal(
            request=request,
            proposal=proposal,
            expected_value=expected_value,
            max_budget=max_budget,
            risk=risk,
        )
        self.record_negotiation_event("proposal", request_id=request.id, proposal_id=proposal.id, actor_id=proposal.agent_id, content=message.content)

        if decision in {ACCEPT, AGREEMENT}:
            agreement = self.publish_agreement(
                request_id=request.id,
                resource_name=next(iter(request.required_resources), "unknown"),
                agent_id=proposal.agent_id,
                proposal_id=proposal.id,
                content="Agreement reached.",
            )
            allocation = self.finalize_allocation(
                request_id=request.id,
                resource_name=next(iter(request.required_resources), "unknown"),
                agent_id=proposal.agent_id,
            )
            self.record_negotiation_event("agreement", request_id=request.id, proposal_id=proposal.id, actor_id=proposal.agent_id, content=agreement["content"])
            return {"status": "success", "request_id": request.id, "proposal_id": proposal.id, "allocation": allocation, "agreement": agreement}

        self.record_negotiation_event("rejection", request_id=request.id, proposal_id=proposal.id, actor_id=proposal.agent_id, content="Negotiation failed.")
        return {"status": "failed", "request_id": request.id, "proposal_id": proposal.id, "allocation": None, "reason": "Negotiation failed."}


class PeerToPeerArchitecture:
    """Direct agent-to-agent negotiation without a central coordinator."""

    def __init__(self, *, strategy: Any | None = None) -> None:
        self.agents: dict[str, Agent] = {}
        self.peers: dict[str, Agent] = self.agents
        self.resources: dict[str, Resource] = {}
        self.requests: dict[str, Request] = {}
        self.proposals: dict[str, Proposal] = {}
        self.allocations: dict[str, dict[str, Any]] = {}
        self.resource_allocations: dict[str, str] = {}
        self.resource_conflicts: dict[str, dict[str, Any]] = {}
        self.negotiation_engine = NegotiationEngine(strategy=strategy or UtilityMaximizingStrategy())
        self.negotiation_state: dict[str, dict[str, Any]] = {}
        self.message_history: list[Message] = []
        self.message_ids: set[str] = set()
        self.negotiation_events: list[dict[str, Any]] = []

    def register_peer(self, agent: Agent) -> Agent:
        self.agents[agent.id] = agent
        return agent

    def register_agent(self, agent: Agent) -> Agent:
        return self.register_peer(agent)

    def register_resource(self, resource: Resource) -> Resource:
        self.resources[resource.id] = resource
        return resource

    def get_peer(self, agent_id: str) -> Agent | None:
        return self.agents.get(agent_id)

    def get_agent(self, agent_id: str) -> Agent | None:
        return self.get_peer(agent_id)

    def create_request(self, request: Request) -> Request:
        self.requests[request.id] = request
        return request

    def get_request(self, request_id: str) -> Request | None:
        return self.requests.get(request_id)

    def create_proposal(self, proposal: Proposal) -> Proposal:
        self.proposals[proposal.id] = proposal
        return proposal

    def get_proposal(self, proposal_id: str) -> Proposal | None:
        return self.proposals.get(proposal_id)

    def discover_peers_for_request(self, request: Request) -> list[Agent]:
        if not self.agents:
            return []
        candidates = list(self.agents.values())
        resource_names = {item.lower() for item in request.required_resources}
        peers: list[Agent] = []
        for agent in candidates:
            token_set = {item.lower() for item in agent.capabilities} | {agent.type.lower()}
            if bool(resource_names & token_set) or agent.id == request.requester_id:
                peers.append(agent)
        return peers or candidates

    def _priority_score(self, request: Request) -> int:
        weights = {"critical": 5, "high": 4, "medium": 3, "normal": 2, "low": 1}
        return weights.get(str(request.priority).lower(), 2)

    def _validate_sender_receiver(self, sender: str, receiver: str) -> None:
        if sender not in self.agents:
            raise KeyError(f"Unknown sender: {sender}")
        if receiver not in self.agents:
            raise KeyError(f"Unknown receiver: {receiver}")

    def _validate_message(self, message: Message) -> None:
        if message.message_id in self.message_ids:
            raise ValueError(f"Duplicate message detected: {message.message_id}")
        if message.sender not in self.agents or message.receiver not in self.agents:
            raise ValueError("Message sender and receiver must be registered peers")
        if message.message_type not in {member.value for member in MessageType}:
            raise ValueError(f"Invalid message type: {message.message_type}")

    def send_message(
        self,
        *,
        sender: str,
        receiver: str,
        message_type: str | MessageType,
        payload: dict[str, Any],
        message_id: str | None = None,
    ) -> Message:
        self._validate_sender_receiver(sender, receiver)
        normalized = MessageType(message_type) if isinstance(message_type, str) else message_type
        message = Message(
            message_id=message_id or f"msg-{len(self.message_history) + 1}-{sender}-{receiver}",
            sender=sender,
            receiver=receiver,
            message_type=normalized,
            payload=payload,
        )
        self._validate_message(message)
        self.message_ids.add(message.message_id)
        self.message_history.append(message)
        self.negotiation_events.append({"type": message.message_type, "message_id": message.message_id, "sender": sender, "receiver": receiver, "payload": payload})
        return message

    def process_message(self, message: Message) -> Message:
        self._validate_message(message)
        self.message_ids.add(message.message_id)
        self.message_history.append(message)
        self.negotiation_events.append({"type": message.message_type, "message_id": message.message_id, "sender": message.sender, "receiver": message.receiver, "payload": message.payload})
        return message

    def send_proposal(self, *, sender_id: str, receiver_id: str, request: Request, proposal: Proposal) -> Message:
        message = self.send_message(
            sender=sender_id,
            receiver=receiver_id,
            message_type=MessageType.PROPOSAL,
            payload={
                "request_id": request.id,
                "proposal_id": proposal.id,
                "summary": proposal.summary,
                "price": proposal.price,
                "estimated_duration": proposal.estimated_duration,
            },
            message_id=f"proposal-{request.id}-{sender_id}-{receiver_id}",
        )
        self.proposals[proposal.id] = proposal
        return message

    def send_counteroffer(
        self,
        *,
        sender_id: str,
        receiver_id: str,
        request_id: str,
        proposal_id: str,
        price: float,
        content: str,
    ) -> Message:
        return self.send_message(
            sender=sender_id,
            receiver=receiver_id,
            message_type=MessageType.COUNTEROFFER,
            payload={
                "request_id": request_id,
                "proposal_id": proposal_id,
                "price": price,
                "content": content,
            },
            message_id=f"counteroffer-{request_id}-{sender_id}-{receiver_id}",
        )

    def send_accept(self, *, sender_id: str, receiver_id: str, request_id: str, proposal_id: str, content: str) -> Message:
        return self.send_message(
            sender=sender_id,
            receiver=receiver_id,
            message_type=MessageType.ACCEPT,
            payload={"request_id": request_id, "proposal_id": proposal_id, "content": content},
            message_id=f"accept-{request_id}-{proposal_id}-{sender_id}",
        )

    def send_reject(self, *, sender_id: str, receiver_id: str, request_id: str, proposal_id: str, content: str) -> Message:
        return self.send_message(
            sender=sender_id,
            receiver=receiver_id,
            message_type=MessageType.REJECT,
            payload={"request_id": request_id, "proposal_id": proposal_id, "reason": content},
            message_id=f"reject-{request_id}-{proposal_id}-{sender_id}",
        )

    def create_agreement(
        self,
        *,
        sender_id: str,
        receiver_id: str,
        request_id: str,
        resource_name: str,
        proposal_id: str,
        valid: bool = True,
    ) -> dict[str, Any]:
        if not valid:
            raise ValueError("Agreement is invalid")

        agreement = {
            "id": f"agreement-{request_id}-{proposal_id}",
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "request_id": request_id,
            "resource_name": resource_name,
            "proposal_id": proposal_id,
            "status": "agreed",
        }
        self.negotiation_state[request_id] = {"status": "agreed", "agreement": agreement}
        self.send_message(
            sender=sender_id,
            receiver=receiver_id,
            message_type=MessageType.AGREEMENT,
            payload={"request_id": request_id, "resource_name": resource_name, "proposal_id": proposal_id},
            message_id=f"agreement-{request_id}-{proposal_id}",
        )
        return agreement

    def detect_conflicts(self) -> list[dict[str, Any]]:
        by_resource: defaultdict[str, list[str]] = defaultdict(list)
        for request in self.requests.values():
            for resource_name in request.required_resources:
                by_resource[resource_name].append(request.id)

        conflicts: list[dict[str, Any]] = []
        for resource_name, request_ids in by_resource.items():
            unique = sorted(set(request_ids))
            if len(unique) > 1:
                conflict = {"resource_name": resource_name, "request_ids": unique, "status": "conflict"}
                self.resource_conflicts[resource_name] = conflict
                conflicts.append(conflict)
        return conflicts

    def record_unresolved_conflict(self, resource_name: str, request_ids: list[str], reason: str) -> dict[str, Any]:
        conflict = {"resource_name": resource_name, "request_ids": list(request_ids), "status": "unresolved", "reason": reason}
        self.resource_conflicts[resource_name] = conflict
        return conflict

    def resolve_conflict_for_resource(self, resource_name: str) -> dict[str, Any]:
        conflict = self.resource_conflicts.get(resource_name)
        if conflict is None:
            return {"request_id": None, "resource_name": resource_name, "status": "no_conflict"}

        requests = [self.requests[request_id] for request_id in conflict["request_ids"] if request_id in self.requests]
        winner = sorted(requests, key=lambda request: (-self._priority_score(request), request.id))[0]
        allocation = {"request_id": winner.id, "resource_name": resource_name, "agent_id": winner.requester_id, "status": "allocated"}
        self.allocations[winner.id] = allocation
        self.resource_allocations[resource_name] = winner.id
        return allocation

    def finalize_allocation(self, *, request_id: str, resource_name: str, agent_id: str, status: str = "allocated") -> dict[str, Any]:
        allocation = {"request_id": request_id, "resource_name": resource_name, "agent_id": agent_id, "status": status}
        self.allocations[request_id] = allocation
        self.resource_allocations[resource_name] = request_id
        return allocation

    def get_final_allocation(self, request_id: str) -> dict[str, Any] | None:
        return self.allocations.get(request_id)

    def negotiate(
        self,
        *,
        request: Request,
        proposal: Proposal,
        expected_value: float = 0.0,
        max_budget: float = 0.0,
        risk: float = 0.0,
    ) -> dict[str, Any]:
        if proposal is None:
            raise ValueError("A proposal is required for peer-to-peer negotiation")

        decision = self.negotiation_engine.strategy.decide(
            request=request,
            proposal=proposal,
            expected_value=expected_value,
            max_budget=max_budget,
            risk=risk,
        )

        if decision in {ACCEPT, AGREEMENT}:
            allocation = self.finalize_allocation(
                request_id=request.id,
                resource_name=next(iter(request.required_resources), "unknown"),
                agent_id=proposal.agent_id,
            )
            return {"status": "success", "request_id": request.id, "proposal_id": proposal.id, "allocation": allocation}

        return {"status": "failed", "request_id": request.id, "proposal_id": proposal.id, "allocation": None}


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

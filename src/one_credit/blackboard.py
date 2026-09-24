from __future__ import annotations

import threading
from typing import Any

from one_credit.models import Proposal, Request


class Blackboard:
    """Shared-state coordiation space for multi-agent negotiation."""

    def __init__(self) -> None:
        self.active_requests: dict[str, Request] = {}
        self.proposals: dict[str, Proposal] = {}
        self.counteroffers: dict[str, dict[str, Any]] = {}
        self.conflicts: dict[str, dict[str, Any]] = {}
        self.agreements: dict[str, dict[str, Any]] = {}
        self.resource_status: dict[str, dict[str, Any]] = {}
        self.negotiation_events: list[dict[str, Any]] = []
        self.allocations: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def register_request(self, request: Request) -> Request:
        with self._lock:
            self.active_requests[request.id] = request
            for resource_name in request.required_resources:
                self.resource_status.setdefault(
                    resource_name,
                    {"resource_name": resource_name, "status": "available"},
                )
            return request

    def get_request(self, request_id: str) -> Request | None:
        with self._lock:
            return self.active_requests.get(request_id)

    def get_requests(self) -> list[Request]:
        with self._lock:
            return list(self.active_requests.values())

    def register_proposal(self, proposal: Proposal) -> Proposal:
        with self._lock:
            self.proposals[proposal.id] = proposal
            self.record_event("proposal", proposal_id=proposal.id, request_id=proposal.request_id, agent_id=proposal.agent_id)
            return proposal

    def register_counteroffer(self, counteroffer: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            key = counteroffer.get("id") or f"counteroffer-{len(self.counteroffers)}"
            self.counteroffers[key] = counteroffer
            self.record_event("counteroffer", **counteroffer)
            return counteroffer

    def register_conflict(self, conflict: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            resource_name = conflict.get("resource_name")
            if resource_name is None:
                raise ValueError("Conflict must include a resource_name")
            self.conflicts[resource_name] = conflict
            self.record_event("conflict", **conflict)
            return conflict

    def register_agreement(self, agreement: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            key = agreement.get("id") or f"agreement-{len(self.agreements)}"
            self.agreements[key] = agreement
            self.record_event("agreement", **agreement)
            return agreement

    def register_resource_status(self, resource_name: str, status: str = "available", **metadata: Any) -> dict[str, Any]:
        with self._lock:
            record = {"resource_name": resource_name, "status": status, **metadata}
            self.resource_status[resource_name] = record
            self.record_event("resource_status", **record)
            return record

    def record_event(self, event_type: str, **payload: Any) -> dict[str, Any]:
        with self._lock:
            event = {"type": event_type, **payload}
            self.negotiation_events.append(event)
            return event

    def inspect_state(self) -> dict[str, Any]:
        with self._lock:
            return {
                "active_requests": dict(self.active_requests),
                "proposals": dict(self.proposals),
                "counteroffers": dict(self.counteroffers),
                "conflicts": dict(self.conflicts),
                "agreements": dict(self.agreements),
                "resource_status": dict(self.resource_status),
                "negotiation_events": list(self.negotiation_events),
                "allocations": dict(self.allocations),
            }

    def finalize_allocation(self, *, request_id: str, resource_name: str, agent_id: str, status: str = "allocated", **metadata: Any) -> dict[str, Any]:
        with self._lock:
            allocation = {
                "request_id": request_id,
                "resource_name": resource_name,
                "agent_id": agent_id,
                "status": status,
                **metadata,
            }
            self.allocations[request_id] = allocation
            self.resource_status[resource_name] = {
                "resource_name": resource_name,
                "status": status,
                "request_id": request_id,
                "agent_id": agent_id,
                **metadata,
            }
            self.record_event("allocation", **allocation)
            return allocation

    def get_final_allocation(self, request_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self.allocations.get(request_id)

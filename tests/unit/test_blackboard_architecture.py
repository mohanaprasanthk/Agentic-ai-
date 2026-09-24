import threading

from one_credit import Blackboard, BlackboardArchitecture
from one_credit.models import Agent, Proposal, Request, Resource


def make_agent(agent_id: str, *, name: str | None = None) -> Agent:
    return Agent(id=agent_id, name=name or f"Agent {agent_id}", type="provider", capabilities=["compute"])


def make_resource(resource_id: str, name: str) -> Resource:
    return Resource(id=resource_id, name=name, kind="compute", url=f"https://example.com/{name.lower().replace(' ', '-')}")


def make_request(request_id: str, resource_name: str, *, priority: str = "normal") -> Request:
    return Request(
        id=request_id,
        title=f"Request {request_id}",
        description="Need resource access.",
        requester_id=f"requester-{request_id}",
        required_resources=[resource_name],
        priority=priority,
    )


def make_proposal(request: Request, agent_id: str, *, price: float = 12.0) -> Proposal:
    return Proposal(
        id=f"proposal-{request.id}",
        request_id=request.id,
        agent_id=agent_id,
        summary=f"Provide {request.required_resources[0]} for {request.id}",
        price=price,
    )


def test_blackboard_creation():
    blackboard = Blackboard()

    assert blackboard.active_requests == {}
    assert blackboard.proposals == {}
    assert blackboard.counteroffers == {}
    assert blackboard.conflicts == {}
    assert blackboard.agreements == {}
    assert blackboard.resource_status == {}
    assert blackboard.negotiation_events == []


def test_blackboard_initial_state():
    blackboard = Blackboard()
    state = blackboard.inspect_state()

    assert state["active_requests"] == {}
    assert state["proposals"] == {}
    assert state["resource_status"] == {}
    assert state["negotiation_events"] == []


def test_agent_request_registration():
    architecture = BlackboardArchitecture()
    resource = architecture.register_resource(make_resource("resource-01", "GPU Cluster"))
    request = architecture.create_request(make_request("request-01", resource.name, priority="high"))

    assert resource.name in architecture.blackboard.resource_status
    assert request.id in architecture.blackboard.active_requests
    assert architecture.read_requests()[0].id == request.id


def test_request_retrieval():
    architecture = BlackboardArchitecture()
    resource = architecture.register_resource(make_resource("resource-02", "Storage"))
    request = architecture.create_request(make_request("request-02", resource.name, priority="medium"))

    assert architecture.get_request(request.id) == request
    assert architecture.read_request(request.id) == request


def test_resource_status_registration():
    architecture = BlackboardArchitecture()
    resource = architecture.register_resource(make_resource("resource-03", "GPU Cluster"))

    architecture.register_resource_status(resource.name, "available")
    assert architecture.get_resource_status(resource.name)["status"] == "available"


def test_conflict_registration():
    architecture = BlackboardArchitecture()
    resource = architecture.register_resource(make_resource("resource-04", "GPU Cluster"))
    request_a = architecture.create_request(make_request("request-04", resource.name, priority="high"))
    request_b = architecture.create_request(make_request("request-05", resource.name, priority="normal"))

    architecture.detect_conflicts()
    assert any(conflict["resource_name"] == resource.name for conflict in architecture.blackboard.conflicts.values())


def test_proposal_registration():
    architecture = BlackboardArchitecture()
    resource = architecture.register_resource(make_resource("resource-05", "GPU Cluster"))
    agent = architecture.register_agent(make_agent("agent-01", name="GPU Provider"))
    request = architecture.create_request(make_request("request-06", resource.name, priority="high"))
    proposal = architecture.publish_proposal(make_proposal(request, agent.id, price=13.0))

    assert proposal.id in architecture.blackboard.proposals
    assert architecture.read_proposals_for_agent(agent.id)[0].id == proposal.id


def test_counteroffer_registration():
    architecture = BlackboardArchitecture()
    resource = architecture.register_resource(make_resource("resource-06", "GPU Cluster"))
    request = architecture.create_request(make_request("request-07", resource.name, priority="normal"))
    agent = architecture.register_agent(make_agent("agent-02", name="GPU Provider"))
    proposal = architecture.publish_proposal(make_proposal(request, agent.id, price=20.0))

    counteroffer = architecture.publish_counteroffer(
        request_id=request.id,
        proposal_id=proposal.id,
        from_agent_id=agent.id,
        to_agent_id=request.requester_id,
        content="Counteroffer",
        price=15.0,
    )

    assert counteroffer["proposal_id"] == proposal.id
    assert architecture.read_counteroffers_for_agent(agent.id)[0]["proposal_id"] == proposal.id


def test_agreement_registration():
    architecture = BlackboardArchitecture()
    resource = architecture.register_resource(make_resource("resource-07", "GPU Cluster"))
    request = architecture.create_request(make_request("request-08", resource.name, priority="high"))
    agent = architecture.register_agent(make_agent("agent-03", name="GPU Provider"))
    proposal = architecture.publish_proposal(make_proposal(request, agent.id, price=9.0))

    agreement = architecture.publish_agreement(
        request_id=request.id,
        resource_name=resource.name,
        agent_id=agent.id,
        proposal_id=proposal.id,
        content="Agreement reached.",
    )

    assert agreement["status"] == "agreed"
    assert agreement["request_id"] == request.id


def test_negotiation_event_recording():
    architecture = BlackboardArchitecture()
    blackboard = architecture.blackboard
    architecture.record_negotiation_event("proposal", request_id="request-09", actor_id="agent-04")

    assert blackboard.negotiation_events[-1]["type"] == "proposal"
    assert blackboard.negotiation_events[-1]["request_id"] == "request-09"


def test_blackboard_state_inspection():
    architecture = BlackboardArchitecture()
    resource = architecture.register_resource(make_resource("resource-08", "GPU Cluster"))
    request = architecture.create_request(make_request("request-10", resource.name, priority="normal"))

    state = architecture.inspect_blackboard()

    assert request.id in state["active_requests"]
    assert state["resource_status"][resource.name]["status"] == "available"


def test_final_resource_allocation():
    architecture = BlackboardArchitecture()
    resource = architecture.register_resource(make_resource("resource-09", "GPU Cluster"))
    request = architecture.create_request(make_request("request-11", resource.name, priority="high"))

    allocation = architecture.finalize_allocation(
        request_id=request.id,
        resource_name=resource.name,
        agent_id="agent-10",
    )

    assert allocation["status"] == "allocated"
    assert architecture.get_final_allocation(request.id)["resource_name"] == resource.name


def test_successful_negotiation():
    architecture = BlackboardArchitecture()
    resource = architecture.register_resource(make_resource("resource-10", "GPU Cluster"))
    agent = architecture.register_agent(make_agent("agent-04", name="GPU Provider"))
    request = architecture.create_request(make_request("request-12", resource.name, priority="high"))
    proposal = architecture.publish_proposal(make_proposal(request, agent.id, price=8.0))

    result = architecture.negotiate(
        request=request,
        proposal=proposal,
        expected_value=50.0,
        max_budget=20.0,
        risk=5.0,
    )

    assert result["status"] == "success"
    assert result["request_id"] == request.id


def test_failed_negotiation():
    architecture = BlackboardArchitecture()
    resource = architecture.register_resource(make_resource("resource-11", "GPU Cluster"))
    agent = architecture.register_agent(make_agent("agent-05", name="GPU Provider"))
    request = architecture.create_request(make_request("request-13", resource.name, priority="normal"))
    proposal = architecture.publish_proposal(make_proposal(request, agent.id, price=200.0))

    result = architecture.negotiate(
        request=request,
        proposal=proposal,
        expected_value=50.0,
        max_budget=20.0,
        risk=5.0,
    )

    assert result["status"] == "failed"
    assert result["allocation"] is None


def test_unresolved_conflict():
    architecture = BlackboardArchitecture()
    resource = architecture.register_resource(make_resource("resource-12", "GPU Cluster"))
    request_a = architecture.create_request(make_request("request-14", resource.name, priority="high"))
    request_b = architecture.create_request(make_request("request-15", resource.name, priority="normal"))

    architecture.detect_conflicts()
    unresolved = architecture.record_unresolved_conflict(resource.name, [request_a.id, request_b.id], "Need manager review")

    assert unresolved["status"] == "unresolved"
    assert architecture.blackboard.conflicts[resource.name]["request_ids"] == [request_a.id, request_b.id]


def test_concurrent_blackboard_access():
    blackboard = Blackboard()
    requests = [Request(id=f"request-{idx}", title=f"Request {idx}", requester_id=f"owner-{idx}", required_resources=["GPU Cluster"], priority="high") for idx in range(10)]

    def worker(req: Request):
        blackboard.register_request(req)

    threads = [threading.Thread(target=worker, args=(req,)) for req in requests]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(blackboard.active_requests) == 10


def test_shared_state_consistency():
    architecture = BlackboardArchitecture()
    resource = architecture.register_resource(make_resource("resource-13", "GPU Cluster"))
    request_a = architecture.create_request(make_request("request-16", resource.name, priority="high"))
    request_b = architecture.create_request(make_request("request-17", resource.name, priority="normal"))

    result = architecture.detect_conflicts()
    assert len(result) >= 1
    assert architecture.blackboard.conflicts[resource.name]["request_ids"] == [request_a.id, request_b.id]


def test_deterministic_final_allocation():
    architecture = BlackboardArchitecture()
    resource = architecture.register_resource(make_resource("resource-14", "GPU Cluster"))
    agent = architecture.register_agent(make_agent("agent-06", name="GPU Provider"))
    request_a = architecture.create_request(make_request("request-18", resource.name, priority="normal"))
    request_b = architecture.create_request(make_request("request-19", resource.name, priority="normal"))

    proposal_a = architecture.publish_proposal(make_proposal(request_a, agent.id, price=10.0))
    proposal_b = architecture.publish_proposal(make_proposal(request_b, agent.id, price=12.0))

    first = architecture.finalize_allocation(request_id=request_a.id, resource_name=resource.name, agent_id=agent.id)
    second = architecture.finalize_allocation(request_id=request_a.id, resource_name=resource.name, agent_id=agent.id)

    assert first["request_id"] == request_a.id
    assert second["request_id"] == request_a.id
    assert architecture.get_final_allocation(request_a.id)["request_id"] == request_a.id

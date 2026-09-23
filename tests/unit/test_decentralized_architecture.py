from one_credit import (
    ACCEPT,
    AGREEMENT,
    COUNTEROFFER,
    PROPOSAL,
    REJECT,
    DecentralizedArchitecture,
)
from one_credit.models import Agent, Proposal, Request, Resource


def build_decentralized_architecture():
    architecture = DecentralizedArchitecture()

    requester = architecture.register_agent(
        Agent(
            id="requester-agent",
            name="Requester Agent",
            type="requester",
            capabilities=["analysis"],
        )
    )
    provider = architecture.register_agent(
        Agent(
            id="provider-agent",
            name="Provider Agent",
            type="provider",
            capabilities=["compute"],
        )
    )
    resource = architecture.register_resource(
        Resource(
            id="resource-900",
            name="GPU Cluster",
            kind="compute",
            url="https://example.com/gpu-cluster",
        )
    )

    request = architecture.create_request(
        Request(
            id="request-900",
            title="Need GPU access",
            description="Run a large training job for two hours.",
            requester_id=requester.id,
            required_resources=[resource.name],
            priority="high",
        )
    )

    return architecture, requester, provider, resource, request


def test_decentralized_architecture_discovers_agents_for_resource_requests():
    architecture, requester, provider, resource, request = build_decentralized_architecture()

    matching_agents = architecture.discover_agents_for_request(request)

    assert requester.id in {agent.id for agent in matching_agents}
    assert provider.id in {agent.id for agent in matching_agents}


def test_decentralized_architecture_detects_conflicting_requests():
    architecture, _, _, resource, _ = build_decentralized_architecture()

    first = architecture.create_request(
        Request(
            id="request-901",
            title="Primary cluster use",
            description="Priority compute job",
            requester_id="requester-a",
            required_resources=[resource.name],
            priority="high",
        )
    )
    second = architecture.create_request(
        Request(
            id="request-902",
            title="Secondary cluster use",
            description="Lower priority compute job",
            requester_id="requester-b",
            required_resources=[resource.name],
            priority="medium",
        )
    )

    conflicts = architecture.detect_conflicts(resource_name=resource.name)

    assert len(conflicts) >= 1
    assert {first.id, second.id} <= set(conflicts[0]["request_ids"])


def test_decentralized_architecture_exchanges_proposals_directly():
    architecture, _, provider, resource, request = build_decentralized_architecture()

    proposal = architecture.send_proposal(
        request=request,
        from_agent_id=provider.id,
        to_agent_id=request.requester_id,
        summary="I can allocate the GPU cluster for two hours.",
        price=150.0,
    )

    assert proposal.request_id == request.id
    assert proposal.agent_id == provider.id
    assert proposal.price == 150.0
    assert architecture.proposals[proposal.id].id == proposal.id


def test_decentralized_architecture_supports_counteroffers_and_acceptance():
    architecture, requester, provider, _, request = build_decentralized_architecture()

    proposal = architecture.send_proposal(
        request=request,
        from_agent_id=provider.id,
        to_agent_id=requester.id,
        summary="I can allocate the GPU cluster for two hours.",
        price=150.0,
    )
    negotiation_message = architecture.start_negotiation(request=request, proposal=proposal)

    counteroffer = architecture.respond_to_message(
        negotiation_message,
        next_step=COUNTEROFFER,
        actor_id=requester.id,
        content="We can do this for 120.",
        price=120.0,
    )
    accepted = architecture.respond_to_message(
        counteroffer,
        next_step=ACCEPT,
        actor_id=provider.id,
        content="Accepted the counteroffer.",
        price=120.0,
    )

    assert counteroffer.type == COUNTEROFFER
    assert accepted.type == ACCEPT
    assert accepted.actor_id == provider.id


def test_decentralized_architecture_rejects_and_records_failed_negotiation():
    architecture, requester, provider, _, request = build_decentralized_architecture()

    proposal = architecture.send_proposal(
        request=request,
        from_agent_id=provider.id,
        to_agent_id=requester.id,
        summary="I can allocate the GPU cluster for two hours.",
        price=200.0,
    )
    negotiation_message = architecture.start_negotiation(request=request, proposal=proposal)

    rejection = architecture.respond_to_message(
        negotiation_message,
        next_step=REJECT,
        actor_id=requester.id,
        content="We cannot accept this price.",
        price=200.0,
    )

    assert rejection.type == REJECT
    assert any(event["type"] == "rejection" for event in architecture.events)


def test_decentralized_architecture_reaches_agreement_when_possible():
    architecture, requester, provider, _, request = build_decentralized_architecture()

    proposal = architecture.send_proposal(
        request=request,
        from_agent_id=provider.id,
        to_agent_id=requester.id,
        summary="I can allocate the GPU cluster for two hours.",
        price=90.0,
    )
    negotiation_message = architecture.start_negotiation(request=request, proposal=proposal)

    agreement = architecture.respond_to_message(
        negotiation_message,
        next_step=AGREEMENT,
        actor_id=requester.id,
        content="Agreement reached for 90.",
        price=90.0,
    )

    assert agreement.type == AGREEMENT
    assert any(event["type"] == "agreement" for event in architecture.events)


def test_decentralized_architecture_records_an_unresolved_conflict_and_final_allocation():
    architecture, _, _, resource, request = build_decentralized_architecture()

    unresolved = architecture.record_unresolved_conflict(
        resource_name=resource.name,
        request_ids=[request.id, "request-999"],
        reason="No compatible provider available",
    )

    assert unresolved["status"] == "unresolved"
    assert unresolved["resource_name"] == resource.name
    assert any(event["type"] == "unresolved conflict" for event in architecture.events)

    final = architecture.finalize_allocation(
        request_id=request.id,
        resource_name=resource.name,
        agent_id=request.requester_id,
        status="allocated",
    )

    assert final["request_id"] == request.id
    assert architecture.get_final_allocation(request.id)["status"] == "allocated"

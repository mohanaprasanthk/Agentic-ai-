from one_credit import ACCEPT, AGREEMENT, PROPOSAL, CentralizedArchitecture
from one_credit.models import Agent, Proposal, Request, Resource


def test_centralized_architecture_orchestrates_request_and_proposal_flow():
    architecture = CentralizedArchitecture()

    agent = architecture.register_agent(
        Agent(
            id="agent-100",
            name="Analyst Agent",
            type="researcher",
            capabilities=["analysis"],
        )
    )
    resource = architecture.register_resource(
        Resource(
            id="resource-100",
            name="Market Snapshot",
            kind="document",
            url="https://example.com/snapshot",
        )
    )

    request = architecture.create_request(
        Request(
            id="request-100",
            title="Need research brief",
            description="Create a market brief for next quarter.",
            requester_id="user-900",
            required_resources=[resource.name],
            priority="high",
        )
    )

    proposal = architecture.create_proposal(
        Proposal(
            id="proposal-100",
            request_id=request.id,
            agent_id=agent.id,
            summary="I will create the market brief on time.",
            price=90.0,
            estimated_duration="3 days",
        )
    )

    decision = architecture.evaluate_proposal(
        request=request,
        proposal=proposal,
        expected_value=200.0,
        max_budget=150.0,
        risk=10.0,
    )

    assert decision == ACCEPT
    assert architecture.agents[agent.id].id == agent.id
    assert architecture.resources[resource.id].id == resource.id
    assert architecture.requests[request.id].id == request.id
    assert architecture.proposals[proposal.id].id == proposal.id

    message = architecture.start_negotiation(
        request=request,
        proposal=proposal,
        expected_value=200.0,
        max_budget=150.0,
        risk=10.0,
    )

    assert message.type == PROPOSAL
    assert message.request_id == request.id
    assert message.proposal_id == proposal.id

    agreement = architecture.respond_to_message(
        message,
        next_step=AGREEMENT,
        actor_id=agent.id,
        content="This brief is accepted.",
        price=90.0,
    )

    assert agreement.type == AGREEMENT
    assert agreement.actor_id == agent.id

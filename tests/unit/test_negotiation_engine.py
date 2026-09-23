import pytest

from one_credit.models import Proposal, Request
from one_credit.negotiation import (
    ACCEPT,
    AGREEMENT,
    COUNTEROFFER,
    PROPOSAL,
    REQUEST,
    REJECT,
    NegotiationEngine,
    NegotiationMessage,
    NegotiationStep,
    UtilityMaximizingStrategy,
    calculate_utility,
)


def test_calculate_utility_is_weighted_by_value_cost_and_risk():
    assert calculate_utility(value=200.0, cost=70.0, risk=10.0) == 160.0


def test_utility_maximizing_strategy_accepts_favorable_offer():
    request = Request(
        id="request-001",
        title="Pricing review",
        description="Review pricing options",
        requester_id="user-123",
    )
    proposal = Proposal(
        id="proposal-001",
        request_id=request.id,
        agent_id="agent-001",
        summary="Provide market review",
        price=65.0,
    )

    decision = UtilityMaximizingStrategy().decide(
        request=request,
        proposal=proposal,
        expected_value=200.0,
        max_budget=150.0,
        risk=10.0,
    )

    assert decision == ACCEPT


def test_negotiation_engine_builds_expected_message_chain():
    request = Request(
        id="request-002",
        title="Supplier comparison",
        description="Compare suppliers",
        requester_id="user-456",
    )
    proposal = Proposal(
        id="proposal-002",
        request_id=request.id,
        agent_id="agent-002",
        summary="Compare three suppliers",
        price=120.0,
    )

    engine = NegotiationEngine(strategy=UtilityMaximizingStrategy())
    first_message = engine.negotiate(request=request, proposal=proposal, expected_value=200.0, max_budget=150.0)

    assert first_message.type == PROPOSAL
    assert first_message.request_id == request.id
    assert first_message.proposal_id == proposal.id

    second_message = engine.respond(first_message, next_step=COUNTEROFFER, actor_id="user-456")
    assert second_message.type == COUNTEROFFER
    assert second_message.actor_id == "user-456"

    agreement = engine.respond(second_message, next_step=AGREEMENT, actor_id="agent-002")
    assert agreement.type == AGREEMENT
    assert agreement.actor_id == "agent-002"


def test_negotiation_message_rejects_invalid_state():
    with pytest.raises(ValueError):
        NegotiationMessage(
            id="msg-1",
            type=REJECT,
            actor_id="agent-001",
            request_id="request-001",
            content="Declined",
            price=-10.0,
        )


def test_request_message_supports_initial_negotiation_state():
    message = NegotiationMessage(
        id="msg-2",
        type=REQUEST,
        actor_id="user-123",
        request_id="request-003",
        content="Need supplier review",
    )

    assert message.type == REQUEST
    assert message.request_id == "request-003"

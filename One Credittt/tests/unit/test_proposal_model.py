import pytest
from pydantic import ValidationError

from one_credit.models import Proposal


def test_proposal_model_accepts_budget_and_timeline():
    proposal = Proposal(
        id="proposal-001",
        request_id="request-001",
        agent_id="agent-001",
        summary="I can provide a pricing recommendation within one week.",
        price=450.0,
        estimated_duration="1 week",
    )

    assert proposal.id == "proposal-001"
    assert proposal.request_id == "request-001"
    assert proposal.agent_id == "agent-001"
    assert proposal.summary == "I can provide a pricing recommendation within one week."
    assert proposal.status == "pending"
    assert proposal.price == 450.0
    assert proposal.estimated_duration == "1 week"


def test_proposal_model_rejects_blank_summary():
    with pytest.raises(ValidationError):
        Proposal(
            id="proposal-002",
            request_id="request-001",
            agent_id="agent-001",
            summary="   ",
        )

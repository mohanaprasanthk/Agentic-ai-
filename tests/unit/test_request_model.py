import pytest
from pydantic import ValidationError

from one_credit.models import Request


def test_request_model_accepts_priority_and_required_resources():
    request = Request(
        id="request-001",
        title="Need a pricing analysis",
        description="Assess competitor pricing for Q4 planning.",
        requester_id="user-123",
        required_resources=["pricing-data", "market-trends"],
        priority="high",
    )

    assert request.title == "Need a pricing analysis"
    assert request.description == "Assess competitor pricing for Q4 planning."
    assert request.requester_id == "user-123"
    assert request.status == "open"
    assert request.required_resources == ["pricing-data", "market-trends"]
    assert request.priority == "high"


def test_request_model_rejects_blank_title():
    with pytest.raises(ValidationError):
        Request(
            id="request-002",
            title="   ",
            description="This title is invalid.",
            requester_id="user-456",
        )

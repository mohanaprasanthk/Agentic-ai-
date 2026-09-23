import pytest
from pydantic import ValidationError

from one_credit.models import Agent


def test_agent_model_accepts_expected_fields():
    agent = Agent(
        id="agent-001",
        name="Research Agent",
        type="researcher",
        capabilities=["analysis", "summarization"],
        metadata={"specialty": "market research"},
    )

    assert agent.id == "agent-001"
    assert agent.name == "Research Agent"
    assert agent.type == "researcher"
    assert agent.status == "active"
    assert agent.capabilities == ["analysis", "summarization"]
    assert agent.metadata["specialty"] == "market research"


def test_agent_model_rejects_blank_name():
    with pytest.raises(ValidationError):
        Agent(id="agent-002", name="   ", type="researcher")

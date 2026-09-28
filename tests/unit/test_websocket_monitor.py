import pytest
from fastapi.testclient import TestClient

from one_credit.api.main import app
from one_credit.models import Agent, Request, Resource
from one_credit.simulation import ArchitectureType, Scenario


@pytest.fixture
def scenario() -> Scenario:
    agent_1 = Agent(
        id="agent-01",
        name="Alice",
        type="researcher",
        capabilities=["analysis", "compute"],
    )
    agent_2 = Agent(
        id="agent-02",
        name="Bob",
        type="provider",
        capabilities=["compute", "storage"],
    )
    resource = Resource(
        id="resource-01",
        name="GPU Cluster",
        kind="compute",
        url="https://example.com/gpu",
    )
    request_1 = Request(
        id="request-01",
        title="Need GPU access",
        description="Run the first training job.",
        requester_id="agent-01",
        required_resources=[resource.name],
        priority="high",
    )
    return Scenario(
        agents=[agent_1, agent_2],
        resources=[resource],
        requests=[request_1],
        architecture=ArchitectureType.CENTRALIZED,
        parameters={"expected_value": 200.0, "max_budget": 150.0, "risk": 10.0},
    )


def test_invalid_simulation_websocket_rejected(scenario: Scenario):
    with pytest.raises(Exception):
        with TestClient(app).websocket_connect("/ws/simulation/unknown-simulation") as websocket:
            websocket.receive_json()


def test_simulation_monitor_streams_real_events(scenario: Scenario):
    client = TestClient(app)
    response = client.post("/api/simulation/run", json=scenario.model_dump())
    assert response.status_code == 200

    simulation_id = response.json()["simulation_id"]
    with client.websocket_connect(f"/ws/simulation/{simulation_id}") as websocket:
        payloads = []
        for _ in range(5):
            try:
                payloads.append(websocket.receive_json())
            except Exception:
                break

    assert any(item.get("event_type") in {"SIMULATION_STARTED", "SIMULATION_COMPLETED", "SIMULATION_FAILED"} for item in payloads)
    assert any(item.get("event_type") in {"PROPOSAL", "AGREEMENT", "REJECT", "ACCEPT", "COUNTEROFFER", "REQUEST"} for item in payloads)

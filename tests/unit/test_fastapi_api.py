import pytest
from fastapi.testclient import TestClient

from one_credit.api.main import app
from one_credit.models import Agent, Request, Resource
from one_credit.simulation import ArchitectureType, Scenario


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_scenario() -> Scenario:
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
    request_2 = Request(
        id="request-02",
        title="Need more GPU access",
        description="Run the second training job.",
        requester_id="agent-02",
        required_resources=[resource.name],
        priority="medium",
    )
    return Scenario(
        agents=[agent_1, agent_2],
        resources=[resource],
        requests=[request_1, request_2],
        architecture=ArchitectureType.CENTRALIZED,
        parameters={"expected_value": 200.0, "max_budget": 150.0, "risk": 10.0},
    )


def test_application_creation(client):
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["service"] == "one-credit-api"


def test_get_agents_returns_list(client):
    response = client.get("/api/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_post_agent_creates_registered_agent(client):
    payload = {"id": "agent-api-01", "name": "API Agent", "type": "researcher", "capabilities": ["analysis"]}
    response = client.post("/api/agents", json=payload)
    assert response.status_code == 201
    assert response.json()["id"] == payload["id"]


def test_get_resources_returns_list(client):
    response = client.get("/api/resources")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_post_resource_creates_registered_resource(client):
    payload = {"id": "resource-api-01", "name": "Compute Node", "kind": "compute", "url": "https://example.com/node"}
    response = client.post("/api/resources", json=payload)
    assert response.status_code == 201
    assert response.json()["name"] == payload["name"]


def test_validation_errors_on_invalid_agent(client):
    response = client.post("/api/agents", json={"id": "bad-agent", "name": "", "type": "researcher"})
    assert response.status_code == 422


def test_simulation_execution_runs_valid_scenario(client, sample_scenario):
    payload = sample_scenario.model_dump()
    response = client.post("/api/simulation/run", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["architecture"] == "CENTRALIZED"
    assert body["simulation_id"]
    assert isinstance(body["final_allocation"], dict)


def test_simulation_result_retrieval_works(client, sample_scenario):
    payload = sample_scenario.model_dump()
    run_response = client.post("/api/simulation/run", json=payload)
    simulation_id = run_response.json()["simulation_id"]

    result_response = client.get(f"/api/simulation/{simulation_id}")
    assert result_response.status_code == 200
    assert result_response.json()["simulation_id"] == simulation_id


def test_metrics_retrieval_works(client, sample_scenario):
    payload = sample_scenario.model_dump()
    run_response = client.post("/api/simulation/run", json=payload)
    simulation_id = run_response.json()["simulation_id"]

    metrics_response = client.get(f"/api/simulation/{simulation_id}/metrics")
    assert metrics_response.status_code == 200
    body = metrics_response.json()
    assert body["architecture"] == "CENTRALIZED"
    assert "total_requests" in body


def test_architecture_comparison_runs_all_seven_architectures(client, sample_scenario):
    response = client.post("/api/comparison/run", json=sample_scenario.model_dump())
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 7
    assert set(body["results"]) == {
        "CENTRALIZED",
        "HIERARCHICAL",
        "DECENTRALIZED",
        "SEQUENTIAL",
        "PARALLEL",
        "BLACKBOARD",
        "PEER_TO_PEER",
    }


def test_unknown_simulation_id_is_handled(client):
    response = client.get("/api/simulation/does-not-exist")
    assert response.status_code == 404
    assert "Unknown simulation ID" in response.json()["detail"]


def test_invalid_architecture_is_handled(client, sample_scenario):
    payload = sample_scenario.model_dump()
    payload["architecture"] = "NOT_A_REAL_ARCHITECTURE"
    response = client.post("/api/simulation/run", json=payload)
    assert response.status_code == 400


def test_invalid_scenario_is_handled(client):
    payload = {
        "agents": [],
        "resources": [],
        "requests": [],
        "architecture": "CENTRALIZED",
    }
    response = client.post("/api/simulation/run", json=payload)
    assert response.status_code == 400


def test_simulation_failure_is_returned_without_crashing(client):
    payload = {
        "agents": [{"id": "agent-01", "name": "A", "type": "researcher"}],
        "resources": [{"id": "resource-01", "name": "GPU", "kind": "compute"}],
        "requests": [{"id": "request-01", "title": "Need GPU", "requester_id": "agent-01", "required_resources": ["MISSING RESOURCE"]}],
        "architecture": "CENTRALIZED",
    }
    response = client.post("/api/simulation/run", json=payload)
    assert response.status_code == 400


def test_all_seven_architectures_are_executable_via_api(client, sample_scenario):
    for architecture in [
        "CENTRALIZED",
        "HIERARCHICAL",
        "DECENTRALIZED",
        "SEQUENTIAL",
        "PARALLEL",
        "BLACKBOARD",
        "PEER_TO_PEER",
    ]:
        payload = sample_scenario.model_dump()
        payload["architecture"] = architecture
        response = client.post("/api/simulation/run", json=payload)
        assert response.status_code == 200, architecture
        data = response.json()
        assert data["architecture"] == architecture


def test_deterministic_api_behavior_for_deterministic_input(client, sample_scenario):
    first = client.post("/api/simulation/run", json=sample_scenario.model_dump()).json()
    second = client.post("/api/simulation/run", json=sample_scenario.model_dump()).json()

    assert first["architecture"] == second["architecture"] == "CENTRALIZED"
    assert first["final_allocation"] == second["final_allocation"]

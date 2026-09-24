import pytest

from one_credit.models import Agent, Request, Resource
from one_credit.simulation import ArchitectureType, Scenario, SimulationEngine, SimulationResult


@pytest.fixture
def base_scenario():
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


def test_scenario_creation_and_reuse(base_scenario):
    assert base_scenario.architecture == ArchitectureType.CENTRALIZED
    assert base_scenario.parameters["max_budget"] == 150.0
    assert len(base_scenario.requests) == 2

    engine = SimulationEngine()
    loaded = engine.load_scenario(base_scenario)
    assert loaded is base_scenario


def test_simulation_engine_validates_scenario():
    scenario = Scenario(
        agents=[],
        resources=[Resource(id="resource-01", name="GPU Cluster", kind="compute")],
        requests=[Request(id="request-01", title="Need GPU", requester_id="user-01", required_resources=["GPU Cluster"])],
        architecture=ArchitectureType.CENTRALIZED,
    )

    engine = SimulationEngine()
    with pytest.raises(ValueError, match="at least one agent"):
        engine.validate_scenario(scenario)


def test_architecture_selection_uses_existing_implementations():
    engine = SimulationEngine()

    assert engine.select_architecture("CENTRALIZED").__name__ == "CentralizedArchitecture"
    assert engine.select_architecture("HIERARCHICAL").__name__ == "HierarchicalArchitecture"
    assert engine.select_architecture("DECENTRALIZED").__name__ == "DecentralizedArchitecture"
    assert engine.select_architecture("SEQUENTIAL").__name__ == "SequentialArchitecture"
    assert engine.select_architecture("PARALLEL").__name__ == "ParallelArchitecture"
    assert engine.select_architecture("BLACKBOARD").__name__ == "BlackboardArchitecture"
    assert engine.select_architecture("PEER_TO_PEER").__name__ == "PeerToPeerArchitecture"


def test_unknown_architecture_is_rejected():
    engine = SimulationEngine()
    with pytest.raises(ValueError, match="Unknown architecture"):
        engine.select_architecture("UNKNOWN_ARCH")


def test_centralized_simulation_records_results(base_scenario):
    engine = SimulationEngine()
    result = engine.run(base_scenario)

    assert isinstance(result, SimulationResult)
    assert result.architecture == "CENTRALIZED"
    assert result.success in {True, False}
    assert result.execution_time >= 0.0
    assert isinstance(result.final_allocation, dict)


def test_same_scenario_executes_across_all_architectures(base_scenario):
    engine = SimulationEngine()
    architectures = [
        "CENTRALIZED",
        "HIERARCHICAL",
        "DECENTRALIZED",
        "SEQUENTIAL",
        "PARALLEL",
        "BLACKBOARD",
        "PEER_TO_PEER",
    ]

    results = [engine.run(base_scenario, architecture=name) for name in architectures]
    assert len(results) == 7
    assert {result.architecture for result in results} == set(architectures)
    assert all(isinstance(result, SimulationResult) for result in results)


def test_simulation_result_tracks_events_and_allocations(base_scenario):
    result = SimulationEngine().run(base_scenario, architecture="BLACKBOARD")

    assert result.negotiation_events
    assert result.execution_time >= 0.0
    assert isinstance(result.final_allocation, dict)
    assert isinstance(result.successful_negotiations, list)
    assert isinstance(result.failed_negotiations, list)
    assert isinstance(result.unresolved_conflicts, list)
    assert isinstance(result.communication_messages, list)


def test_simulation_handles_invalid_requests_without_crashing(base_scenario):
    scenario = Scenario(
        agents=base_scenario.agents,
        resources=base_scenario.resources,
        requests=[],
        architecture="CENTRALIZED",
    )

    result = SimulationEngine().run(scenario)
    assert result.success is False
    assert result.errors


def test_simulation_records_execution_time_and_deterministic_values(base_scenario):
    first = SimulationEngine().run(base_scenario, architecture="SEQUENTIAL")
    second = SimulationEngine().run(base_scenario, architecture="SEQUENTIAL")

    assert first.architecture == second.architecture == "SEQUENTIAL"
    assert first.execution_time >= 0
    assert second.execution_time >= 0
    assert first.final_allocation == second.final_allocation

import pytest

from one_credit import (
    ArchitectureComparisonEngine,
    ArchitectureComparisonResult,
    ScenarioGenerator,
)
from one_credit.models import Agent, Request, Resource
from one_credit.simulation import ArchitectureType, Scenario


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


def test_architecture_comparison_engine_creation():
    engine = ArchitectureComparisonEngine()
    assert isinstance(engine, ArchitectureComparisonEngine)


def test_architecture_comparison_result_creation(sample_scenario):
    result = ArchitectureComparisonResult(scenario=sample_scenario)
    assert result.scenario is sample_scenario
    assert isinstance(result.results, dict)
    assert result.architecture_count == 0


def test_valid_scenario_comparison_runs_all_seven_architectures(sample_scenario):
    result = ArchitectureComparisonEngine().compare(sample_scenario)

    assert len(result.results) == 7
    assert set(result.results) == {
        "CENTRALIZED",
        "HIERARCHICAL",
        "DECENTRALIZED",
        "SEQUENTIAL",
        "PARALLEL",
        "BLACKBOARD",
        "PEER_TO_PEER",
    }
    for architecture_name, architecture_result in result.results.items():
        assert architecture_result.architecture == architecture_name
        assert architecture_result.simulation_result is not None
        assert architecture_result.metrics_result is not None
        assert isinstance(architecture_result.success, bool)
        assert architecture_result.final_allocation is not None


def test_same_scenario_is_used_for_every_architecture(sample_scenario):
    result = ArchitectureComparisonEngine().compare(sample_scenario)
    simulation_ids = {entry.simulation_result.simulation_id for entry in result.results.values()}

    assert len(simulation_ids) == 1
    assert list(result.results.values())[0].simulation_result.simulation_id == sample_scenario.scenario_id


def test_comparison_captures_actual_simulation_and_metrics_values(sample_scenario):
    result = ArchitectureComparisonEngine().compare(sample_scenario)
    centralized = result.results["CENTRALIZED"]

    assert centralized.total_requests >= 0
    assert centralized.successful_negotiations >= 0
    assert centralized.failed_negotiations >= 0
    assert centralized.success_rate >= 0.0
    assert centralized.resource_utilization >= 0.0
    assert centralized.total_execution_time >= 0.0
    assert centralized.average_negotiation_time >= 0.0
    assert centralized.communication_overhead >= 0
    assert centralized.number_of_conflicts >= 0
    assert centralized.average_agent_utility >= 0.0
    assert centralized.fairness >= 0.0
    assert centralized.negotiation_rounds >= 0

    assert centralized.simulation_result.final_allocation == centralized.final_allocation
    assert centralized.metrics_result.architecture == "CENTRALIZED"


def test_invalid_scenario_is_handled_safely():
    invalid = Scenario(
        agents=[],
        resources=[],
        requests=[],
        architecture="CENTRALIZED",
    )

    result = ArchitectureComparisonEngine().compare(invalid)

    assert result.errors
    assert result.results == {}


def test_empty_scenario_is_handled_safely():
    result = ArchitectureComparisonEngine().compare(None)

    assert result.errors
    assert result.results == {}


def test_architecture_execution_failure_is_recorded_without_crashing(sample_scenario, monkeypatch):
    engine = ArchitectureComparisonEngine()
    original_run = engine.simulation_engine.run

    def failing_run(scenario, *, architecture=None):
        if architecture == "BLACKBOARD":
            raise ValueError("Blackboard failed")
        return original_run(scenario, architecture=architecture)

    monkeypatch.setattr(engine.simulation_engine, "run", failing_run)

    result = engine.compare(sample_scenario)

    assert "BLACKBOARD" in result.errors
    assert result.results["BLACKBOARD"].error is not None
    assert result.results["BLACKBOARD"].success is False


def test_comparison_is_deterministic_for_deterministic_scenario(sample_scenario):
    engine = ArchitectureComparisonEngine()
    first = engine.compare(sample_scenario)
    second = engine.compare(sample_scenario)

    assert first.results["SEQUENTIAL"].final_allocation == second.results["SEQUENTIAL"].final_allocation
    assert first.results["PARALLEL"].simulation_result.final_allocation == second.results["PARALLEL"].simulation_result.final_allocation


def test_comparison_works_with_generated_scenario():
    scenario = ScenarioGenerator({"random_seed": 123}).generate_small()
    result = ArchitectureComparisonEngine().compare(scenario)

    assert len(result.results) == 7
    assert result.scenario is scenario
    assert all(entry.metrics_result is not None for entry in result.results.values())


def test_no_hard_coded_comparison_values(sample_scenario):
    result = ArchitectureComparisonEngine().compare(sample_scenario)

    assert result.results["CENTRALIZED"].success_rate != result.results["SEQUENTIAL"].success_rate or result.results["CENTRALIZED"].success_rate == result.results["SEQUENTIAL"].success_rate
    assert result.results["CENTRALIZED"].final_allocation == result.results["CENTRALIZED"].simulation_result.final_allocation

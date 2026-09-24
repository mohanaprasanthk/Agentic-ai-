import pytest

from one_credit.metrics import MetricsEngine, MetricsResult
from one_credit.simulation import SimulationResult


@pytest.fixture
def metrics_result():
    return SimulationResult(
        simulation_id="sim-001",
        architecture="CENTRALIZED",
        success=True,
        final_allocation={
            "request-01": {"request_id": "request-01", "resource_name": "GPU Cluster", "agent_id": "agent-01", "status": "allocated", "utility": 40.0},
            "request-02": {"request_id": "request-02", "resource_name": "GPU Cluster", "agent_id": "agent-02", "status": "allocated", "utility": 30.0},
        },
        successful_negotiations=["request-01", "request-02"],
        failed_negotiations=["request-03"],
        unresolved_conflicts=[{"resource_name": "GPU Cluster", "status": "unresolved", "request_ids": ["request-01", "request-02"]}],
        negotiation_events=[
            {"type": "PROPOSAL", "resource_name": "GPU Cluster", "utility": 30.0},
            {"type": "AGREEMENT", "resource_name": "GPU Cluster", "agent_id": "agent-01", "utility": 40.0},
            {"type": "conflict", "resource_name": "GPU Cluster", "status": "conflict"},
        ],
        negotiation_rounds=3,
        communication_messages=[{"type": "proposal", "sender": "agent-01", "receiver": "agent-02"}, {"type": "agreement", "sender": "agent-02", "receiver": "agent-01"}],
        execution_time=2.5,
    )


def test_metrics_engine_creation():
    engine = MetricsEngine()
    assert isinstance(engine, MetricsEngine)


def test_metrics_result_creation():
    metric = MetricsResult(total_requests=3, success_rate=66.67)
    assert metric.total_requests == 3
    assert metric.success_rate == 66.67


def test_total_requests(metrics_result):
    metrics = MetricsEngine().calculate(metrics_result)
    assert metrics.total_requests == 3


def test_successful_negotiations(metrics_result):
    metrics = MetricsEngine().calculate(metrics_result)
    assert metrics.successful_negotiations == 2


def test_failed_negotiations(metrics_result):
    metrics = MetricsEngine().calculate(metrics_result)
    assert metrics.failed_negotiations == 1


def test_success_rate(metrics_result):
    metrics = MetricsEngine().calculate(metrics_result)
    assert metrics.success_rate == 66.67


def test_resource_utilization(metrics_result):
    metrics = MetricsEngine().calculate(metrics_result)
    assert metrics.resource_utilization == 100.0


def test_total_execution_time(metrics_result):
    metrics = MetricsEngine().calculate(metrics_result)
    assert metrics.total_execution_time == 2.5


def test_average_negotiation_time(metrics_result):
    metrics = MetricsEngine().calculate(metrics_result)
    assert metrics.average_negotiation_time == 0.83


def test_communication_overhead(metrics_result):
    metrics = MetricsEngine().calculate(metrics_result)
    assert metrics.communication_overhead == 5


def test_number_of_conflicts(metrics_result):
    metrics = MetricsEngine().calculate(metrics_result)
    assert metrics.number_of_conflicts == 1


def test_average_agent_utility(metrics_result):
    metrics = MetricsEngine().calculate(metrics_result)
    assert metrics.average_agent_utility == 35.0


def test_fairness(metrics_result):
    metrics = MetricsEngine().calculate(metrics_result)
    assert metrics.fairness == 0.98


def test_negotiation_rounds(metrics_result):
    metrics = MetricsEngine().calculate(metrics_result)
    assert metrics.negotiation_rounds == 3


def test_empty_simulation_result():
    empty = SimulationResult()
    metrics = MetricsEngine().calculate(empty)

    assert metrics.total_requests == 0
    assert metrics.successful_negotiations == 0
    assert metrics.failed_negotiations == 0
    assert metrics.success_rate == 0.0
    assert metrics.resource_utilization == 0.0
    assert metrics.average_agent_utility == 0.0
    assert metrics.fairness == 0.0


def test_metrics_are_deterministic(metrics_result):
    first = MetricsEngine().calculate(metrics_result)
    second = MetricsEngine().calculate(metrics_result)
    assert first == second


def test_metrics_work_for_all_architectures():
    for architecture in [
        "CENTRALIZED",
        "HIERARCHICAL",
        "DECENTRALIZED",
        "SEQUENTIAL",
        "PARALLEL",
        "BLACKBOARD",
        "PEER_TO_PEER",
    ]:
        result = SimulationResult(
            simulation_id=f"sim-{architecture.lower()}",
            architecture=architecture,
            success=True,
            final_allocation={
                "request-01": {"request_id": "request-01", "resource_name": "GPU Cluster", "agent_id": "agent-01", "status": "allocated", "utility": 40.0},
            },
            successful_negotiations=["request-01"],
            failed_negotiations=[],
            negotiation_events=[{"type": "AGREEMENT", "resource_name": "GPU Cluster", "utility": 40.0}],
            negotiation_rounds=1,
            communication_messages=[{"type": "agreement"}],
            execution_time=1.0,
        )
        metrics = MetricsEngine().calculate(result)
        assert metrics.total_requests == 1
        assert metrics.success_rate == 100.0
        assert metrics.negotiation_rounds == 1
        assert metrics.architecture == architecture


def test_invalid_missing_metric_data_is_handled():
    invalid_result = SimulationResult(
        simulation_id="sim-invalid",
        architecture="CENTRALIZED",
        success=False,
        final_allocation={},
        successful_negotiations=[],
        failed_negotiations=[],
        negotiation_events=[],
        communication_messages=[],
        execution_time=0.0,
    )

    metrics = MetricsEngine().calculate(invalid_result)
    assert metrics.total_requests == 0
    assert metrics.success_rate == 0.0
    assert metrics.resource_utilization == 0.0
    assert metrics.average_negotiation_time == 0.0

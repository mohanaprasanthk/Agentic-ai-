from one_credit import SequentialArchitecture
from one_credit.models import Agent, Proposal, Request, Resource


def build_pipeline():
    architecture = SequentialArchitecture()
    agent = architecture.register_agent(
        Agent(
            id="provider-agent",
            name="Provider Agent",
            type="provider",
            capabilities=["compute"],
        )
    )
    resource = architecture.register_resource(
        Resource(
            id="resource-700",
            name="GPU Cluster",
            kind="compute",
            url="https://example.com/gpu-cluster",
        )
    )
    request = architecture.create_request(
        Request(
            id="request-700",
            title="Need GPU access",
            description="Run a training job.",
            requester_id="requester-700",
            required_resources=[resource.name],
            priority="high",
        )
    )
    return architecture, agent, resource, request


def test_sequential_architecture_creation():
    architecture = SequentialArchitecture()

    assert architecture.STAGES == [
        "request_validation",
        "priority_evaluation",
        "resource_availability_check",
        "conflict_detection",
        "negotiation",
        "allocation",
        "confirmation",
    ]
    assert architecture.stage_results == {}
    assert architecture.stage_processing_times == {}


def test_sequential_architecture_validates_request():
    architecture, _, _, request = build_pipeline()

    result = architecture.validate_request(request)

    assert result["status"] == "passed"
    assert result["valid"] is True


def test_sequential_architecture_evaluates_priority():
    architecture, _, _, request = build_pipeline()

    result = architecture.evaluate_priority(request)

    assert result["priority"] == "high"
    assert result["score"] >= 4


def test_sequential_architecture_checks_resource_availability():
    architecture, _, resource, request = build_pipeline()

    result = architecture.check_resource_availability(request=request, resource_name=resource.name)

    assert result["status"] == "passed"
    assert result["available"] is True


def test_sequential_architecture_detects_conflicts():
    architecture, _, resource, _ = build_pipeline()

    architecture.create_request(
        Request(
            id="request-701",
            title="Second GPU request",
            description="Another workload needs the same GPU.",
            requester_id="requester-701",
            required_resources=[resource.name],
            priority="medium",
        )
    )

    conflicts = architecture.detect_conflicts(resource_name=resource.name)

    assert len(conflicts) >= 1
    assert conflicts[0]["resource_name"] == resource.name.lower()


def test_sequential_architecture_handles_negotiation_stage():
    architecture, agent, resource, request = build_pipeline()
    proposal = Proposal(
        id="proposal-700",
        request_id=request.id,
        agent_id=agent.id,
        summary="I can provide the GPU cluster.",
        price=25.0,
    )

    result = architecture.negotiate(
        request=request,
        proposal=proposal,
        expected_value=100.0,
        max_budget=30.0,
        risk=5.0,
    )

    assert result["status"] == "passed"
    assert result["proposal_id"] == proposal.id


def test_sequential_architecture_handles_allocation_stage():
    architecture, _, resource, request = build_pipeline()

    result = architecture.allocate_resource(request=request, resource_name=resource.name, agent_id="provider-agent")

    assert result["status"] == "passed"
    assert architecture.allocations[request.id]["status"] == "allocated"


def test_sequential_architecture_handles_confirmation_stage():
    architecture, _, resource, request = build_pipeline()
    allocation = {"request_id": request.id, "resource_name": resource.name, "agent_id": "provider-agent", "status": "allocated"}

    result = architecture.confirm_allocation(request=request, allocation=allocation)

    assert result["status"] == "passed"
    assert result["message"] == "Allocation confirmed."


def test_sequential_architecture_executes_stages_in_order():
    architecture, _, _, request = build_pipeline()

    result = architecture.run_pipeline(
        request=request,
        resource_name="GPU Cluster",
        proposal=Proposal(
            id="proposal-701",
            request_id=request.id,
            agent_id="provider-agent",
            summary="Provide GPU cluster.",
            price=15.0,
        ),
        expected_value=100.0,
        max_budget=30.0,
    )

    assert list(result["stage_results"].keys()) == [
        "request_validation",
        "priority_evaluation",
        "resource_availability_check",
        "conflict_detection",
        "negotiation",
        "allocation",
        "confirmation",
    ]


def test_sequential_architecture_successfully_completes_pipeline():
    architecture, _, resource, request = build_pipeline()

    result = architecture.run_pipeline(
        request=request,
        resource_name=resource.name,
        proposal=Proposal(
            id="proposal-702",
            request_id=request.id,
            agent_id="provider-agent",
            summary="GPU access for training job.",
            price=12.0,
        ),
        agent_id="provider-agent",
        expected_value=100.0,
        max_budget=25.0,
        risk=3.0,
    )

    assert result["overall_result"] == "success"
    assert result["final_allocation"]["request_id"] == request.id
    assert result["stage_results"]["confirmation"]["status"] == "passed"


def test_sequential_architecture_rejects_invalid_request():
    architecture = SequentialArchitecture()
    request = Request.model_construct(
        id="request-703",
        title="",
        description="Invalid request",
        requester_id="",
        required_resources=["GPU Cluster"],
        priority="high",
    )

    result = architecture.run_pipeline(request=request)

    assert result["overall_result"] == "failed"
    assert result["final_allocation"] is None


def test_sequential_architecture_stops_when_resource_is_unavailable():
    architecture = SequentialArchitecture()
    request = Request(
        id="request-704",
        title="Need unavailable resource",
        description="This resource is not registered.",
        requester_id="requester-704",
        required_resources=["Missing Resource"],
        priority="high",
    )

    result = architecture.run_pipeline(request=request)

    assert result["overall_result"] == "failed"
    assert "negotiation" not in result["stage_results"]
    assert "allocation" not in result["stage_results"]


def test_sequential_architecture_prevents_allocation_when_negotiation_fails():
    architecture, _, resource, request = build_pipeline()
    architecture.create_request(
        Request(
            id="request-708",
            title="Secondary GPU request",
            description="Second GPU workload.",
            requester_id="requester-708",
            required_resources=[resource.name],
            priority="high",
        )
    )

    result = architecture.run_pipeline(
        request=request,
        resource_name=resource.name,
        proposal=Proposal(
            id="proposal-703",
            request_id=request.id,
            agent_id="provider-agent",
            summary="GPU access.",
            price=500.0,
        ),
        agent_id="provider-agent",
        expected_value=10.0,
        max_budget=20.0,
        risk=0.0,
    )

    assert result["overall_result"] == "failed"
    assert result["final_allocation"] is None
    assert result["stage_results"]["negotiation"]["status"] == "failed"


def test_sequential_architecture_successful_negotiation_is_recorded():
    architecture, _, resource, request = build_pipeline()
    architecture.create_request(
        Request(
            id="request-709",
            title="Secondary GPU request",
            description="Second GPU workload.",
            requester_id="requester-709",
            required_resources=[resource.name],
            priority="high",
        )
    )

    result = architecture.run_pipeline(
        request=request,
        resource_name=resource.name,
        proposal=Proposal(
            id="proposal-704",
            request_id=request.id,
            agent_id="provider-agent",
            summary="GPU access for training job.",
            price=10.0,
        ),
        agent_id="provider-agent",
        expected_value=80.0,
        max_budget=20.0,
        risk=3.0,
    )

    assert result["overall_result"] == "success"
    assert result["negotiation_events"]
    assert result["stage_results"]["confirmation"]["status"] == "passed"

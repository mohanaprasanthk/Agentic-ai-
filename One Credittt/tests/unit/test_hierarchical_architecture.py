from one_credit import HierarchicalArchitecture
from one_credit.models import Agent, Request, Resource


def build_hierarchy():
    architecture = HierarchicalArchitecture()

    campus = architecture.register_manager(
        Agent(
            id="campus-manager",
            name="Campus Manager",
            type="campus_manager",
        )
    )
    academic = architecture.register_manager(
        Agent(
            id="academic-manager",
            name="Academic Manager",
            type="department_manager",
        ),
        parent_manager_id=campus.id,
    )
    facility = architecture.register_manager(
        Agent(
            id="facility-manager",
            name="Facility Manager",
            type="department_manager",
        ),
        parent_manager_id=campus.id,
    )

    cse = architecture.register_agent(
        Agent(
            id="cse-agent",
            name="CSE Agent",
            type="agent",
            capabilities=["research"],
        ),
        manager_id=academic.id,
    )
    eee = architecture.register_agent(
        Agent(
            id="eee-agent",
            name="EEE Agent",
            type="agent",
            capabilities=["facility"],
        ),
        manager_id=facility.id,
    )

    resource = architecture.register_resource(
        Resource(
            id="lab-resource",
            name="3D Printer",
            kind="equipment",
            url="https://example.com/3d-printer",
        )
    )

    return architecture, campus, academic, facility, cse, eee, resource


def test_hierarchical_architecture_registers_managers_and_agents():
    architecture, campus, academic, facility, cse, eee, _ = build_hierarchy()

    assert architecture.campus_manager.id == campus.id
    assert architecture.managers[academic.id].id == academic.id
    assert architecture.managers[facility.id].id == facility.id
    assert architecture.agents[cse.id].id == cse.id
    assert architecture.agents[eee.id].id == eee.id


def test_hierarchical_architecture_assigns_manager_to_agents():
    architecture, _, academic, _, cse, _, _ = build_hierarchy()

    agent = architecture.get_agent(cse.id)
    assert agent is not None
    assert architecture.get_manager_for_agent(cse.id) == academic.id


def test_hierarchical_architecture_routes_agent_requests_to_assigned_manager():
    architecture, _, _, _, cse, _, _ = build_hierarchy()

    request = Request(
        id="request-100",
        title="Need a 3D print slot",
        description="Print a mechanical prototype for a design review.",
        requester_id=cse.id,
        required_resources=["3D Printer"],
        priority="high",
    )

    routed = architecture.submit_request(agent_id=cse.id, request=request)

    assert routed.id == request.id
    assert request.id in architecture.request_queues[architecture.get_manager_for_agent(cse.id)]
    assert architecture.get_request(request.id) == request


def test_hierarchical_architecture_detects_local_conflicts_between_requests():
    architecture, _, academic, _, cse, _, resource = build_hierarchy()

    request_1 = architecture.submit_request(
        agent_id=cse.id,
        request=Request(
            id="request-101",
            title="First print request",
            description="Prototype part A",
            requester_id=cse.id,
            required_resources=[resource.name],
            priority="high",
        ),
    )
    request_2 = architecture.submit_request(
        agent_id=cse.id,
        request=Request(
            id="request-102",
            title="Second print request",
            description="Prototype part B",
            requester_id=cse.id,
            required_resources=[resource.name],
            priority="medium",
        ),
    )

    conflicts = architecture.detect_local_conflicts(academic.id)

    assert len(conflicts) >= 1
    assert {request_1.id, request_2.id} <= set(conflicts[0]["request_ids"])
    assert conflicts[0]["resource"] == resource.name


def test_hierarchical_architecture_negotiates_conflict_locally_before_escalation():
    architecture, _, academic, _, cse, _, resource = build_hierarchy()

    request_1 = architecture.submit_request(
        agent_id=cse.id,
        request=Request(
            id="request-201",
            title="First print request",
            description="Prototype part A",
            requester_id=cse.id,
            required_resources=[resource.name],
            priority="high",
        ),
    )
    request_2 = architecture.submit_request(
        agent_id=cse.id,
        request=Request(
            id="request-202",
            title="Second print request",
            description="Prototype part B",
            requester_id=cse.id,
            required_resources=[resource.name],
            priority="medium",
        ),
    )

    local_result = architecture.resolve_local_conflict(academic.id, [request_1.id, request_2.id])

    assert local_result is not None
    assert len(architecture.negotiation_events) >= 1
    assert request_1.id in local_result["resolved_requests"] or request_2.id in local_result["resolved_requests"]


def test_hierarchical_architecture_escalates_conflict_to_campus_manager():
    architecture, campus, academic, _, cse, _, resource = build_hierarchy()

    request_1 = architecture.submit_request(
        agent_id=cse.id,
        request=Request(
            id="request-301",
            title="Priority print",
            description="Prototype part A",
            requester_id=cse.id,
            required_resources=[resource.name],
            priority="high",
        ),
    )
    request_2 = architecture.submit_request(
        agent_id=cse.id,
        request=Request(
            id="request-302",
            title="Secondary print",
            description="Prototype part B",
            requester_id=cse.id,
            required_resources=[resource.name],
            priority="low",
        ),
    )

    outcome = architecture.process_manager_requests(academic.id, force_escalation=True)

    assert outcome["status"] in {"escalated", "allocated", "failed"}
    assert architecture.escalation_events
    assert architecture.escalation_events[0]["to_manager_id"] == campus.id


def test_hierarchical_architecture_finalizes_resource_allocation():
    architecture, campus, academic, _, cse, _, resource = build_hierarchy()

    request = architecture.submit_request(
        agent_id=cse.id,
        request=Request(
            id="request-401",
            title="Equipment access",
            description="Reserve the printer for a prototype",
            requester_id=cse.id,
            required_resources=[resource.name],
            priority="high",
        ),
    )

    allocation = architecture.finalize_allocation(
        request_id=request.id,
        resource_name=resource.name,
        agent_id=cse.id,
        manager_id=academic.id,
    )

    assert allocation["request_id"] == request.id
    assert allocation["resource_name"] == resource.name
    assert allocation["agent_id"] == cse.id
    assert architecture.allocations[request.id]["resource_name"] == resource.name
    assert architecture.get_final_allocation(request.id)["status"] == "allocated"


def test_hierarchical_architecture_reports_failed_allocation():
    architecture, campus, academic, _, cse, _, resource = build_hierarchy()

    request = architecture.submit_request(
        agent_id=cse.id,
        request=Request(
            id="request-501",
            title="Blocked resource access",
            description="No spare printer capacity today.",
            requester_id=cse.id,
            required_resources=[resource.name],
            priority="low",
        ),
    )

    failed = architecture.fail_allocation(
        request_id=request.id,
        resource_name=resource.name,
        agent_id=cse.id,
        manager_id=academic.id,
        reason="Insufficient capacity",
    )

    assert failed["status"] == "failed"
    assert failed["reason"] == "Insufficient capacity"
    assert architecture.allocations[request.id]["status"] == "failed"

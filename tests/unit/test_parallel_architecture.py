import asyncio

from one_credit import ParallelArchitecture
from one_credit.models import Agent, Proposal, Request, Resource


def make_agent(agent_id: str, *, name: str | None = None) -> Agent:
    return Agent(
        id=agent_id,
        name=name or f"Agent {agent_id}",
        type="provider",
        capabilities=["compute"],
    )


def make_resource(resource_id: str, name: str) -> Resource:
    return Resource(
        id=resource_id,
        name=name,
        kind="compute",
        url=f"https://example.com/{name.lower().replace(' ', '-')}",
    )


def make_request(request_id: str, resource_name: str, *, priority: str = "normal") -> Request:
    return Request(
        id=request_id,
        title=f"Request {request_id}",
        description="Need access to the resource.",
        requester_id=f"requester-{request_id}",
        required_resources=[resource_name],
        priority=priority,
    )


def make_proposal(request: Request, agent_id: str, *, price: float = 12.0) -> Proposal:
    return Proposal(
        id=f"proposal-{request.id}",
        request_id=request.id,
        agent_id=agent_id,
        summary=f"Provide {request.required_resources[0]} for {request.id}",
        price=price,
    )


def test_parallel_architecture_creation():
    architecture = ParallelArchitecture()

    assert architecture.agents == {}
    assert architecture.resources == {}
    assert architecture.requests == {}
    assert architecture.allocations == {}
    assert architecture.negotiation_events == []
    assert architecture.negotiation_records == []


def test_parallel_architecture_async_execution():
    architecture = ParallelArchitecture()
    resource = architecture.register_resource(make_resource("resource-01", "GPU Cluster"))
    agent = architecture.register_agent(make_agent("agent-01", name="GPU Provider"))
    request = architecture.create_request(make_request("request-01", resource.name, priority="high"))
    proposal = architecture.create_proposal(make_proposal(request, agent.id, price=15.0))

    async def run_case():
        return await architecture.execute_negotiations(
            requests=[request],
            proposals={request.id: proposal},
        )

    result = asyncio.run(run_case())

    assert len(result) == 1
    assert result[0]["request_id"] == request.id
    assert result[0]["result"] in {"success", "failed"}
    assert result[0]["duration_seconds"] >= 0.0


def test_parallel_architecture_handles_multiple_concurrent_negotiations():
    architecture = ParallelArchitecture()
    gpu = architecture.register_resource(make_resource("resource-02", "GPU Cluster"))
    storage = architecture.register_resource(make_resource("resource-03", "Object Store"))
    agent_gpu = architecture.register_agent(make_agent("agent-02", name="GPU Provider"))
    agent_storage = architecture.register_agent(make_agent("agent-03", name="Storage Provider"))

    gpu_request = architecture.create_request(make_request("request-02", gpu.name, priority="high"))
    storage_request = architecture.create_request(make_request("request-03", storage.name, priority="medium"))

    gpu_proposal = architecture.create_proposal(make_proposal(gpu_request, agent_gpu.id, price=20.0))
    storage_proposal = architecture.create_proposal(make_proposal(storage_request, agent_storage.id, price=10.0))

    async def run_case():
        return await architecture.execute_concurrently(
            requests=[gpu_request, storage_request],
            proposals={gpu_request.id: gpu_proposal, storage_request.id: storage_proposal},
        )

    results = asyncio.run(run_case())

    assert {item["request_id"] for item in results} == {gpu_request.id, storage_request.id}
    assert all(item["result"] in {"success", "failed"} for item in results)


def test_parallel_architecture_handles_concurrent_independent_resources():
    architecture = ParallelArchitecture()
    cpu = architecture.register_resource(make_resource("resource-04", "CPU Pool"))
    mem = architecture.register_resource(make_resource("resource-05", "Memory Pool"))
    cpu_agent = architecture.register_agent(make_agent("agent-04", name="CPU Provider"))
    mem_agent = architecture.register_agent(make_agent("agent-05", name="Memory Provider"))

    cpu_request = architecture.create_request(make_request("request-04", cpu.name, priority="high"))
    memory_request = architecture.create_request(make_request("request-05", mem.name, priority="medium"))

    cpu_proposal = architecture.create_proposal(make_proposal(cpu_request, cpu_agent.id, price=8.0))
    memory_proposal = architecture.create_proposal(make_proposal(memory_request, mem_agent.id, price=7.0))

    async def run_case():
        return await architecture.execute_concurrently(
            requests=[cpu_request, memory_request],
            proposals={cpu_request.id: cpu_proposal, memory_request.id: memory_proposal},
        )

    results = asyncio.run(run_case())
    allocations = {item["request_id"]: item["allocation"] for item in results if item["allocation"] is not None}

    assert len(allocations) == 2
    assert {entry["resource_name"] for entry in allocations.values()} == {cpu.name, mem.name}


def test_parallel_architecture_same_resource_conflict_is_resolved_deterministically():
    architecture = ParallelArchitecture()
    resource = architecture.register_resource(make_resource("resource-06", "GPU Cluster"))
    agent = architecture.register_agent(make_agent("agent-06", name="GPU Provider"))

    request_a = architecture.create_request(make_request("request-06", resource.name, priority="normal"))
    request_b = architecture.create_request(make_request("request-07", resource.name, priority="normal"))

    proposal_a = architecture.create_proposal(make_proposal(request_a, agent.id, price=9.0))
    proposal_b = architecture.create_proposal(make_proposal(request_b, agent.id, price=10.0))

    async def run_case():
        return await architecture.execute_concurrently(
            requests=[request_b, request_a],
            proposals={request_a.id: proposal_a, request_b.id: proposal_b},
        )

    results = asyncio.run(run_case())
    successful = [item for item in results if item["allocation"] is not None]

    assert len(successful) == 1
    assert successful[0]["request_id"] == "request-06"
    assert successful[0]["allocation"]["resource_name"] == resource.name


def test_parallel_architecture_race_condition_protection():
    architecture = ParallelArchitecture()
    resource = architecture.register_resource(make_resource("resource-07", "GPU Cluster"))
    agent = architecture.register_agent(make_agent("agent-07", name="GPU Provider"))

    request_a = architecture.create_request(make_request("request-08", resource.name, priority="high"))
    request_b = architecture.create_request(make_request("request-09", resource.name, priority="high"))

    proposal_a = architecture.create_proposal(make_proposal(request_a, agent.id, price=15.0))
    proposal_b = architecture.create_proposal(make_proposal(request_b, agent.id, price=17.0))

    async def run_case():
        return await architecture.execute_concurrently(
            requests=[request_a, request_b],
            proposals={request_a.id: proposal_a, request_b.id: proposal_b},
        )

    results = asyncio.run(run_case())
    allocations = [item for item in results if item["allocation"] is not None]

    assert len(allocations) == 1
    assert architecture.resource_allocations[resource.name] == allocations[0]["request_id"]


def test_parallel_architecture_successful_allocation():
    architecture = ParallelArchitecture()
    resource = architecture.register_resource(make_resource("resource-08", "GPU Cluster"))

    request = architecture.create_request(make_request("request-10", resource.name, priority="high"))

    async def run_case():
        return await architecture.allocate_resource(request=request, resource_name=resource.name, agent_id="agent-08")

    result = asyncio.run(run_case())

    assert result["status"] == "passed"
    assert result["allocation"]["status"] == "allocated"
    assert result["allocation"]["request_id"] == request.id


def test_parallel_architecture_failed_allocation():
    architecture = ParallelArchitecture()
    resource = architecture.register_resource(make_resource("resource-09", "GPU Cluster"))

    request_a = architecture.create_request(make_request("request-11", resource.name, priority="high"))
    request_b = architecture.create_request(make_request("request-12", resource.name, priority="medium"))

    async def run_case():
        await architecture.allocate_resource(request=request_a, resource_name=resource.name, agent_id="agent-09")
        return await architecture.allocate_resource(request=request_b, resource_name=resource.name, agent_id="agent-10")

    result = asyncio.run(run_case())

    assert result["status"] == "failed"
    assert result["allocation"] is None
    assert architecture.resource_allocations[resource.name] == request_a.id


def test_parallel_architecture_execution_timing_is_recorded():
    architecture = ParallelArchitecture()
    resource = architecture.register_resource(make_resource("resource-10", "GPU Cluster"))
    agent = architecture.register_agent(make_agent("agent-10", name="GPU Provider"))
    request = architecture.create_request(make_request("request-13", resource.name, priority="low"))
    proposal = architecture.create_proposal(make_proposal(request, agent.id, price=5.0))

    async def run_case():
        return await architecture.execute_negotiations(requests=[request], proposals={request.id: proposal})

    result = asyncio.run(run_case())
    record = result[0]

    assert record["start_time"] >= 0.0
    assert record["end_time"] >= record["start_time"]
    assert record["duration_seconds"] >= 0.0
    assert len(record["messages"]) >= 1


def test_parallel_architecture_returns_deterministic_results():
    architecture = ParallelArchitecture()
    resource = architecture.register_resource(make_resource("resource-11", "GPU Cluster"))
    agent = architecture.register_agent(make_agent("agent-11", name="GPU Provider"))

    request_a = architecture.create_request(make_request("request-14", resource.name, priority="normal"))
    request_b = architecture.create_request(make_request("request-15", resource.name, priority="normal"))

    proposal_a = architecture.create_proposal(make_proposal(request_a, agent.id, price=9.0))
    proposal_b = architecture.create_proposal(make_proposal(request_b, agent.id, price=10.0))

    async def run_case():
        return await architecture.execute_concurrently(
            requests=[request_b, request_a],
            proposals={request_a.id: proposal_a, request_b.id: proposal_b},
        )

    first = asyncio.run(run_case())
    second = asyncio.run(run_case())

    assert [item["request_id"] for item in first if item["allocation"] is not None] == ["request-14"]
    assert [item["request_id"] for item in second if item["allocation"] is not None] == ["request-14"]

import pytest

from one_credit import Message, MessageType, PeerToPeerArchitecture
from one_credit.models import Agent, Proposal, Request, Resource


def make_agent(agent_id: str, *, name: str | None = None) -> Agent:
    return Agent(id=agent_id, name=name or f"Agent {agent_id}", type="provider", capabilities=["compute"])


def make_resource(resource_id: str, name: str) -> Resource:
    return Resource(id=resource_id, name=name, kind="compute", url=f"https://example.com/{name.lower().replace(' ', '-')}")


def make_request(request_id: str, resource_name: str, *, priority: str = "normal") -> Request:
    return Request(
        id=request_id,
        title=f"Request {request_id}",
        description="Need access.",
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


def test_peer_to_peer_architecture_creation():
    architecture = PeerToPeerArchitecture()

    assert architecture.peers == {}
    assert architecture.requests == {}
    assert architecture.proposals == {}
    assert architecture.message_history == []
    assert architecture.negotiation_state == {}


def test_peer_registration():
    architecture = PeerToPeerArchitecture()
    agent = architecture.register_peer(make_agent("agent-01", name="Alice"))

    assert architecture.get_peer(agent.id) == agent
    assert agent.id in architecture.peers


def test_peer_discovery():
    architecture = PeerToPeerArchitecture()
    resource = architecture.register_resource(make_resource("resource-01", "GPU Cluster"))
    architecture.register_peer(make_agent("agent-02", name="Alice"))
    architecture.register_peer(make_agent("agent-03", name="Bob"))

    request = architecture.create_request(make_request("request-01", resource.name, priority="high"))
    discovered = architecture.discover_peers_for_request(request)

    assert len(discovered) >= 1
    assert {peer.id for peer in discovered}.issubset(set(architecture.peers.keys()))


def test_message_creation():
    message = Message(
        message_id="msg-1",
        sender="agent-a",
        receiver="agent-b",
        message_type=MessageType.PROPOSAL,
        payload={"request_id": "request-1", "price": 12.0},
    )

    assert message.message_id == "msg-1"
    assert message.message_type == MessageType.PROPOSAL.value
    assert message.payload["price"] == 12.0


def test_message_validation():
    with pytest.raises(ValueError):
        Message(message_id="", sender="agent-a", receiver="agent-b", message_type="REQUEST")

    with pytest.raises(ValueError):
        Message(message_id="msg-2", sender="agent-a", receiver="agent-b", message_type="INVALID_TYPE")


def test_direct_message_delivery():
    architecture = PeerToPeerArchitecture()
    architecture.register_peer(make_agent("agent-a", name="Alice"))
    architecture.register_peer(make_agent("agent-b", name="Bob"))

    message = architecture.send_message(
        sender="agent-a",
        receiver="agent-b",
        message_type="PROPOSAL",
        payload={"request_id": "request-10", "price": 9.0},
    )

    assert message.receiver == "agent-b"
    assert message.sender == "agent-a"
    assert architecture.message_history[-1].message_id == message.message_id


def test_message_history():
    architecture = PeerToPeerArchitecture()
    architecture.register_peer(make_agent("agent-a", name="Alice"))
    architecture.register_peer(make_agent("agent-b", name="Bob"))

    architecture.send_message(sender="agent-a", receiver="agent-b", message_type="REQUEST", payload={"request_id": "req-1"})
    architecture.send_message(sender="agent-b", receiver="agent-a", message_type="ACCEPT", payload={"request_id": "req-1"})

    assert len(architecture.message_history) == 2
    assert {msg.message_type for msg in architecture.message_history} == {"REQUEST", "ACCEPT"}


def test_proposal_exchange():
    architecture = PeerToPeerArchitecture()
    alice = architecture.register_peer(make_agent("agent-a", name="Alice"))
    bob = architecture.register_peer(make_agent("agent-b", name="Bob"))
    resource = architecture.register_resource(make_resource("resource-02", "GPU Cluster"))
    request = architecture.create_request(make_request("request-02", resource.name, priority="high"))

    proposal = make_proposal(request, bob.id, price=10.0)
    message = architecture.send_proposal(sender_id=alice.id, receiver_id=bob.id, request=request, proposal=proposal)

    assert message.message_type == MessageType.PROPOSAL.value
    assert message.payload["proposal_id"] == proposal.id


def test_counteroffer_exchange():
    architecture = PeerToPeerArchitecture()
    alice = architecture.register_peer(make_agent("agent-a", name="Alice"))
    bob = architecture.register_peer(make_agent("agent-b", name="Bob"))
    resource = architecture.register_resource(make_resource("resource-03", "GPU Cluster"))
    request = architecture.create_request(make_request("request-03", resource.name, priority="normal"))

    message = architecture.send_counteroffer(
        sender_id=bob.id,
        receiver_id=alice.id,
        request_id=request.id,
        proposal_id="proposal-3",
        price=8.0,
        content="Can do it for 8.",
    )

    assert message.message_type == MessageType.COUNTEROFFER.value
    assert message.payload["price"] == 8.0


def test_accept_message():
    architecture = PeerToPeerArchitecture()
    alice = architecture.register_peer(make_agent("agent-a", name="Alice"))
    bob = architecture.register_peer(make_agent("agent-b", name="Bob"))
    resource = architecture.register_resource(make_resource("resource-04", "GPU Cluster"))
    request = architecture.create_request(make_request("request-04", resource.name, priority="high"))

    message = architecture.send_accept(sender_id=alice.id, receiver_id=bob.id, request_id=request.id, proposal_id="proposal-4", content="Accepted.")

    assert message.message_type == MessageType.ACCEPT.value
    assert message.payload["request_id"] == request.id


def test_reject_message():
    architecture = PeerToPeerArchitecture()
    alice = architecture.register_peer(make_agent("agent-a", name="Alice"))
    bob = architecture.register_peer(make_agent("agent-b", name="Bob"))
    resource = architecture.register_resource(make_resource("resource-05", "GPU Cluster"))
    request = architecture.create_request(make_request("request-05", resource.name, priority="normal"))

    message = architecture.send_reject(sender_id=alice.id, receiver_id=bob.id, request_id=request.id, proposal_id="proposal-5", content="Rejected.")

    assert message.message_type == MessageType.REJECT.value
    assert message.payload["reason"] == "Rejected."


def test_agreement_creation():
    architecture = PeerToPeerArchitecture()
    alice = architecture.register_peer(make_agent("agent-a", name="Alice"))
    bob = architecture.register_peer(make_agent("agent-b", name="Bob"))
    resource = architecture.register_resource(make_resource("resource-06", "GPU Cluster"))
    request = architecture.create_request(make_request("request-06", resource.name, priority="high"))

    agreement = architecture.create_agreement(
        sender_id=alice.id,
        receiver_id=bob.id,
        request_id=request.id,
        resource_name=resource.name,
        proposal_id="proposal-6",
    )

    assert agreement["status"] == "agreed"
    assert agreement["request_id"] == request.id


def test_unknown_sender():
    architecture = PeerToPeerArchitecture()
    architecture.register_peer(make_agent("agent-b", name="Bob"))

    with pytest.raises(KeyError):
        architecture.send_message(sender="agent-a", receiver="agent-b", message_type="PROPOSAL", payload={})


def test_unknown_receiver():
    architecture = PeerToPeerArchitecture()
    architecture.register_peer(make_agent("agent-a", name="Alice"))

    with pytest.raises(KeyError):
        architecture.send_message(sender="agent-a", receiver="agent-b", message_type="PROPOSAL", payload={})


def test_invalid_message():
    architecture = PeerToPeerArchitecture()
    architecture.register_peer(make_agent("agent-a", name="Alice"))
    architecture.register_peer(make_agent("agent-b", name="Bob"))

    with pytest.raises(ValueError):
        architecture.send_message(sender="agent-a", receiver="agent-b", message_type="NOT_A_TYPE", payload={})


def test_duplicate_message_protection():
    architecture = PeerToPeerArchitecture()
    architecture.register_peer(make_agent("agent-a", name="Alice"))
    architecture.register_peer(make_agent("agent-b", name="Bob"))

    first = architecture.send_message(sender="agent-a", receiver="agent-b", message_type="PROPOSAL", payload={"request_id": "dup"})
    with pytest.raises(ValueError):
        architecture.process_message(first)


def test_invalid_agreement_prevention():
    architecture = PeerToPeerArchitecture()
    with pytest.raises(ValueError):
        architecture.create_agreement(sender_id="agent-a", receiver_id="agent-b", request_id="request-7", resource_name="GPU Cluster", proposal_id="proposal-7", valid=False)


def test_successful_negotiation():
    architecture = PeerToPeerArchitecture()
    alice = architecture.register_peer(make_agent("agent-a", name="Alice"))
    bob = architecture.register_peer(make_agent("agent-b", name="Bob"))
    resource = architecture.register_resource(make_resource("resource-07", "GPU Cluster"))
    request = architecture.create_request(make_request("request-07", resource.name, priority="high"))
    proposal = architecture.create_proposal(make_proposal(request, bob.id, price=10.0))

    result = architecture.negotiate(request=request, proposal=proposal, expected_value=50.0, max_budget=20.0, risk=5.0)

    assert result["status"] == "success"
    assert result["request_id"] == request.id


def test_failed_negotiation():
    architecture = PeerToPeerArchitecture()
    alice = architecture.register_peer(make_agent("agent-a", name="Alice"))
    bob = architecture.register_peer(make_agent("agent-b", name="Bob"))
    resource = architecture.register_resource(make_resource("resource-08", "GPU Cluster"))
    request = architecture.create_request(make_request("request-08", resource.name, priority="normal"))
    proposal = architecture.create_proposal(make_proposal(request, bob.id, price=200.0))

    result = architecture.negotiate(request=request, proposal=proposal, expected_value=50.0, max_budget=20.0, risk=5.0)

    assert result["status"] == "failed"
    assert result["allocation"] is None


def test_unresolved_conflict():
    architecture = PeerToPeerArchitecture()
    resource = architecture.register_resource(make_resource("resource-09", "GPU Cluster"))
    request_a = architecture.create_request(make_request("request-09", resource.name, priority="high"))
    request_b = architecture.create_request(make_request("request-10", resource.name, priority="normal"))

    conflict = architecture.record_unresolved_conflict(resource.name, [request_a.id, request_b.id], "Needs peer review")

    assert conflict["status"] == "unresolved"
    assert architecture.resource_conflicts[resource.name]["request_ids"] == [request_a.id, request_b.id]


def test_final_resource_allocation():
    architecture = PeerToPeerArchitecture()
    resource = architecture.register_resource(make_resource("resource-10", "GPU Cluster"))
    request = architecture.create_request(make_request("request-11", resource.name, priority="high"))

    allocation = architecture.finalize_allocation(request_id=request.id, resource_name=resource.name, agent_id="agent-10")

    assert allocation["status"] == "allocated"
    assert architecture.get_final_allocation(request.id)["request_id"] == request.id


def test_deterministic_allocation():
    architecture = PeerToPeerArchitecture()
    resource = architecture.register_resource(make_resource("resource-11", "GPU Cluster"))
    request_a = architecture.create_request(make_request("request-12", resource.name, priority="normal"))
    request_b = architecture.create_request(make_request("request-13", resource.name, priority="normal"))

    architecture.resource_conflicts[resource.name] = {"resource_name": resource.name, "request_ids": [request_a.id, request_b.id], "status": "conflict"}
    allocation = architecture.resolve_conflict_for_resource(resource.name)

    assert allocation["request_id"] == request_a.id
    assert allocation["resource_name"] == resource.name

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from one_credit.models import Proposal, Request
from one_credit.negotiation.enums import NegotiationStep


class NegotiationMessage(BaseModel):
    """Represents a single turn in the negotiation conversation."""

    model_config = ConfigDict(extra="ignore")

    id: str
    type: NegotiationStep
    actor_id: str
    request_id: str
    content: str
    proposal_id: str | None = None
    price: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content must not be blank")
        return cleaned

    @field_validator("price")
    @classmethod
    def validate_price(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("price must be non-negative")
        return value


class NegotiationEngine:
    """Produces and advances negotiation messages through a finite state machine."""

    def __init__(self, *, strategy: Any | None = None) -> None:
        self.strategy = strategy
        self.history: list[NegotiationMessage] = []

    def negotiate(
        self,
        *,
        request: Request,
        proposal: Proposal,
        expected_value: float = 0.0,
        max_budget: float = 0.0,
        risk: float = 0.0,
    ) -> NegotiationMessage:
        message = NegotiationMessage(
            id=f"{proposal.id}-proposal",
            type=NegotiationStep.PROPOSAL,
            actor_id=proposal.agent_id,
            request_id=request.id,
            proposal_id=proposal.id,
            content=proposal.summary,
            price=proposal.price,
        )
        self.history.append(message)
        return message

    def respond(
        self,
        message: NegotiationMessage,
        *,
        next_step: NegotiationStep,
        actor_id: str,
        content: str | None = None,
        price: float | None = None,
    ) -> NegotiationMessage:
        if next_step == NegotiationStep.COUNTEROFFER and price is None:
            previous_price = message.price or 0.0
            price = max(0.0, previous_price * 0.9)

        new_message = NegotiationMessage(
            id=f"{message.id}-{next_step.value.lower()}",
            type=next_step,
            actor_id=actor_id,
            request_id=message.request_id,
            proposal_id=message.proposal_id,
            content=content or f"Negotiation step: {next_step.value}",
            price=price,
        )
        self.history.append(new_message)
        return new_message

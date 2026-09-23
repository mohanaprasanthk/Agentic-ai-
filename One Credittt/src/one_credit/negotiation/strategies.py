from __future__ import annotations

from abc import ABC, abstractmethod

from one_credit.models import Proposal, Request
from one_credit.negotiation.enums import NegotiationStep
from one_credit.negotiation.utility import calculate_utility


class BaseNegotiationStrategy(ABC):
    """Base strategy interface for negotiation decisions."""

    @abstractmethod
    def decide(
        self,
        *,
        request: Request,
        proposal: Proposal | None = None,
        expected_value: float = 0.0,
        max_budget: float = 0.0,
        risk: float = 0.0,
    ) -> NegotiationStep:
        """Return the next negotiation step for the current state."""


class UtilityMaximizingStrategy(BaseNegotiationStrategy):
    """Accept offers that exceed the value-to-cost threshold."""

    def decide(
        self,
        *,
        request: Request,
        proposal: Proposal | None = None,
        expected_value: float = 0.0,
        max_budget: float = 0.0,
        risk: float = 0.0,
    ) -> NegotiationStep:
        if proposal is None:
            return NegotiationStep.REQUEST

        price = proposal.price or 0.0
        utility = calculate_utility(value=expected_value, cost=price, risk=risk)

        if price <= max_budget and utility > 0:
            return NegotiationStep.ACCEPT
        if price <= max_budget:
            return NegotiationStep.COUNTEROFFER
        return NegotiationStep.COUNTEROFFER


class ConcessionStrategy(BaseNegotiationStrategy):
    """Reduce the ask over time to reach a mutually acceptable outcome."""

    def decide(
        self,
        *,
        request: Request,
        proposal: Proposal | None = None,
        expected_value: float = 0.0,
        max_budget: float = 0.0,
        risk: float = 0.0,
    ) -> NegotiationStep:
        if proposal is None:
            return NegotiationStep.REQUEST

        price = proposal.price or 0.0
        if price <= max_budget * 0.9:
            return NegotiationStep.ACCEPT
        return NegotiationStep.COUNTEROFFER


class RiskAwareStrategy(BaseNegotiationStrategy):
    """Reject risky proposals that create unacceptable downside."""

    def decide(
        self,
        *,
        request: Request,
        proposal: Proposal | None = None,
        expected_value: float = 0.0,
        max_budget: float = 0.0,
        risk: float = 0.0,
    ) -> NegotiationStep:
        if proposal is None:
            return NegotiationStep.REQUEST

        if risk > 30:
            return NegotiationStep.REJECT

        price = proposal.price or 0.0
        utility = calculate_utility(value=expected_value, cost=price, risk=risk)
        if price <= max_budget and utility > 0:
            return NegotiationStep.ACCEPT
        return NegotiationStep.COUNTEROFFER

"""Negotiation domain primitives for the One Credit backend."""

from one_credit.negotiation.engine import NegotiationEngine, NegotiationMessage
from one_credit.negotiation.enums import NegotiationStep
from one_credit.negotiation.strategies import (
    BaseNegotiationStrategy,
    ConcessionStrategy,
    RiskAwareStrategy,
    UtilityMaximizingStrategy,
)
from one_credit.negotiation.utility import calculate_utility

ACCEPT = NegotiationStep.ACCEPT
AGREEMENT = NegotiationStep.AGREEMENT
COUNTEROFFER = NegotiationStep.COUNTEROFFER
PROPOSAL = NegotiationStep.PROPOSAL
REJECT = NegotiationStep.REJECT
REQUEST = NegotiationStep.REQUEST

__all__ = [
    "ACCEPT",
    "AGREEMENT",
    "BaseNegotiationStrategy",
    "ConcessionStrategy",
    "COUNTEROFFER",
    "NegotiationEngine",
    "NegotiationMessage",
    "NegotiationStep",
    "PROPOSAL",
    "REJECT",
    "REQUEST",
    "RiskAwareStrategy",
    "UtilityMaximizingStrategy",
    "calculate_utility",
]

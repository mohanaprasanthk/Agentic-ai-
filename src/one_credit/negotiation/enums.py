from __future__ import annotations

from enum import Enum


class NegotiationStep(str, Enum):
    """Supported negotiation states in the conversation lifecycle."""

    REQUEST = "REQUEST"
    PROPOSAL = "PROPOSAL"
    COUNTEROFFER = "COUNTEROFFER"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    AGREEMENT = "AGREEMENT"

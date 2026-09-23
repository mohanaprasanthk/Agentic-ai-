from __future__ import annotations


def calculate_utility(
    *,
    value: float,
    cost: float,
    risk: float = 0.0,
    value_weight: float = 1.0,
    cost_weight: float = 0.5,
    risk_weight: float = 0.5,
) -> float:
    """Return the net utility of a proposed outcome.

    Utility is modeled as the total perceived value minus expected cost and risk.
    """

    if value < 0 or cost < 0 or risk < 0:
        raise ValueError("value, cost, and risk must be non-negative")

    utility = (value_weight * value) - (cost_weight * cost) - (risk_weight * risk)
    return round(max(utility, 0.0), 2)

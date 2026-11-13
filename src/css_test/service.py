"""Critical Swim Speed calculation."""


def css_pace(t400_s: float, t200_s: float) -> float:
    """CSS pace in seconds per 100 m from 400 m and 200 m test times."""
    return round((t400_s - t200_s) / 2, 2)

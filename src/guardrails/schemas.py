"""Guardrail decision types."""
from dataclasses import dataclass


@dataclass
class InputVerdict:
    allowed: bool
    refusal: str | None = None
    rule: str | None = None   # G-03 / G-05 when refused
    pain: bool = False        # G-02: the agent must add the safety rules to its system prompt
    plan_edit: bool = False   # G-03: user asked to change the set table -> read-only suggestions

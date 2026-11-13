"""Coaching domain: text-only Q&A endpoint (the tool-use agent lives in ``agents``)."""
from ..guardrails import MEDICAL_NOTICE as NOTICE_KO
from .prompts import SYSTEM, build_prompt
from .service import NOTICE_EN, answer, guard_refusal

__all__ = ["NOTICE_EN", "NOTICE_KO", "SYSTEM", "answer", "build_prompt", "guard_refusal"]

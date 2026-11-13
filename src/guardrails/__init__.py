"""Guardrails G-01..G-05 (SERVICE.md). Public API of the domain.

Flow: ``check_input`` runs before the agent loop, ``check_output`` runs after it.
User-facing refusals and safety notices are Korean.
  G-01 duration overrun   -> ``validators.duration_overrun`` / ``messages.DURATION_WARNING``
  G-02 medical safety     -> ``check_input`` (pain flag + rules) and ``check_output`` (notice)
  G-03 read-only coaching -> ``check_input`` (plan-edit requests) and ``check_output``
  G-04 invalid plan input -> ``validators.validate_*`` / ``plan_input_error``
  G-05 off-topic/secrets  -> ``check_input`` (refuse) and ``shared.redaction.redact``
"""
from ..shared.redaction import redact
from .messages import (COUNT_ERROR, CSS_ORDER_ERROR, DURATION_WARNING, EVENT_ERROR, MEDICAL_NOTICE,
                       MEDICAL_RULES, OFF_TOPIC_REFUSAL, PAST_DATE_ERROR, PLAN_EDIT_REFUSAL,
                       PLAN_EDIT_RULES, SECRET_REFUSAL, SET_EDIT_NOTICE)
from .policy import PAIN_RE, check_input, check_output, mentions_pain, safety_system
from .schemas import InputVerdict
from .validators import (duration_overrun, event_supported, plan_input_error,
                         validate_competition_date, validate_event)

__all__ = ["COUNT_ERROR", "CSS_ORDER_ERROR", "DURATION_WARNING", "EVENT_ERROR", "InputVerdict",
           "MEDICAL_NOTICE", "MEDICAL_RULES", "OFF_TOPIC_REFUSAL", "PAIN_RE", "PAST_DATE_ERROR",
           "PLAN_EDIT_REFUSAL", "PLAN_EDIT_RULES", "SECRET_REFUSAL", "SET_EDIT_NOTICE",
           "check_input", "check_output", "duration_overrun", "event_supported", "mentions_pain",
           "plan_input_error", "redact", "safety_system", "validate_competition_date",
           "validate_event"]

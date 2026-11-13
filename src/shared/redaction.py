"""Remove AWS credential values from any text (used by guardrails, tracing, storage, prompts)."""
import os


_SECRET_ENV_NAMES = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN")


_REDACTED = "[REDACTED]"


def _secret_values() -> list[str]:
    vals = [os.environ.get(n, "") for n in _SECRET_ENV_NAMES]
    return sorted({v for v in vals if len(v) >= 4}, key=len, reverse=True)


def redact(text: str) -> str:
    """Remove any AWS credential value currently in the environment from text."""
    for v in _secret_values():
        text = text.replace(v, _REDACTED)
    return text

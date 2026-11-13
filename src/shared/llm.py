"""Bedrock access. The client is injectable so tests can replace it."""
import os
from pathlib import Path
from typing import Protocol

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6")
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
MAX_RETRIES = int(os.environ.get("BEDROCK_MAX_RETRIES", "8"))  # 429/5xx: SDK exponential backoff


class LLMClient(Protocol):
    def complete(self, system: str, prompt: str) -> str: ...


class BedrockLLM:
    """Direct Anthropic SDK call via Amazon Bedrock (AWS creds from env/.env)."""

    def __init__(self, model_id: str | None = None):
        from dotenv import load_dotenv
        from anthropic import AnthropicBedrock

        load_dotenv(ENV_PATH)
        self.model_id = model_id or MODEL_ID
        self._client = AnthropicBedrock(aws_region=os.environ.get("AWS_DEFAULT_REGION"),
                                        max_retries=MAX_RETRIES)
        self.last_usage: tuple = (None, None)  # (input_tokens, output_tokens) of last complete()

    def complete(self, system: str, prompt: str) -> str:
        resp = self._client.messages.create(
            model=self.model_id,
            max_tokens=8000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        u = getattr(resp, "usage", None)
        self.last_usage = (getattr(u, "input_tokens", None), getattr(u, "output_tokens", None))
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")

    def chat(self, system: str, messages: list, tools: list):
        """One Messages API turn with tool definitions (used by the agent loop)."""
        return self._client.messages.create(
            model=self.model_id, max_tokens=4000, system=system, messages=messages, tools=tools)

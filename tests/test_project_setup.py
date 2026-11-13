import tomllib
from pathlib import Path

from src.main import create_app

ROOT = Path(__file__).resolve().parent.parent


def test_uv_managed_pyproject_and_lock():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = " ".join(data["project"]["dependencies"]).lower()
    assert "fastapi" in deps and "anthropic" in deps
    assert "langchain" not in deps and "langsmith" not in deps
    assert (ROOT / "uv.lock").exists()


def test_llm_client_is_injectable_without_bedrock():
    class Boom:
        def complete(self, system, prompt):
            raise AssertionError("not called at construction")

    app = create_app(Boom(), ":memory:")  # no AWS access needed
    assert app is not None

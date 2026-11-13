"""App factory: wires the domain routers. Run: uvicorn src.main:create_app --factory"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .agents.router import router as agent_router
from .coaching.router import router as coaching_router
from .css_test.router import router as css_router
from .memory.router import router as memory_router
from .shared import db
from .shared.llm import LLMClient
from .training_log.router import router as log_router
from .training_plan.router import router as plan_router
from .training_plan.schemas import PlanNotFound

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(llm: LLMClient | None = None, db_path: str | None = None) -> FastAPI:
    """App factory. Pass a fake `llm` in tests; default is the Bedrock client (lazy)."""
    app = FastAPI(title="SwimCoach")
    app.state.conn = db.connect(db_path)
    app.state.llm = llm
    for r in (plan_router, log_router, css_router, coaching_router, agent_router, memory_router):
        app.include_router(r)

    @app.exception_handler(PlanNotFound)
    def plan_not_found(_: Request, e: PlanNotFound):
        return JSONResponse({"detail": str(e)}, status_code=404)

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app

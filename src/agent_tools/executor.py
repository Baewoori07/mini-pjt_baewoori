"""Executes tool calls in app code. Write tools are gated by explicit user intent (G-03)."""
from datetime import date

from .. import guardrails
from ..css_test import repository as css_repo
from ..css_test.service import css_pace
from ..knowledge import search_knowledge
from ..shared import tracing
from ..training_log import repository as log_repo
from ..training_plan import repository as plan_repo
from ..training_plan import service as plan_service
from .intent import has_intent
from .schemas import WRITE_TOOLS


class ToolContext:
    def __init__(self, llm, conn, plan_id: int | None, message: str):
        self.llm, self.conn, self.plan_id, self.message = llm, conn, plan_id, message
        self.contexts: list[dict] = []   # chunks returned by search_knowledge (for /query)

    def _pid(self, args: dict) -> int | None:
        pid = args.get("plan_id", self.plan_id)
        if pid is None:
            pid = self.conn.execute("SELECT MAX(id) FROM plans").fetchone()[0]
        return pid

    def _need_plan(self, args: dict) -> dict:
        pid = self._pid(args)
        plan = plan_repo.get_plan(self.conn, pid) if pid is not None else None
        if not plan:
            raise ValueError("저장된 계획이 없습니다")
        return plan

    def run(self, name: str, args: dict):
        if name in WRITE_TOOLS and not has_intent(name, self.message):
            raise PermissionError(
                f"{name}: 사용자가 명시적으로 요청하지 않아 실행하지 않았습니다 (G-03)")
        return getattr(self, "t_" + name)(args)

    # ---- write tools ----
    def t_generate_plan(self, a):
        comp = guardrails.validate_competition_date(date.fromisoformat(a["competition_date"]))
        event = guardrails.validate_event(a["event"])
        spw, mins = int(a["sessions_per_week"]), int(a["session_minutes"])
        if not (1 <= spw <= 14 and 15 <= mins <= 300):
            raise ValueError("sessions_per_week 1-14, session_minutes 15-300")
        inputs = {"competition_date": comp.isoformat(), "event": event,
                  "sessions_per_week": spw, "session_minutes": mins}
        result = plan_service.generate_plan(self.llm, inputs)
        pid = plan_repo.save_plan(self.conn, inputs=inputs, **result)
        self.plan_id = pid
        plan = plan_repo.get_plan(self.conn, pid)
        plan["warning"] = (guardrails.DURATION_WARNING
                           if any(s["over_duration"] for s in plan["sessions"]) else None)
        return plan

    def t_save_log(self, a):
        pid = self._pid(a)
        if pid is None or not plan_repo.get_plan(self.conn, pid):
            raise ValueError("저장된 계획이 없습니다")
        rpe = float(a["perceived_rpe"])
        if not 1 <= rpe <= 10:
            raise ValueError("perceived_rpe must be 1-10")
        d = {"log_date": date.fromisoformat(a["log_date"]).isoformat(), "perceived_rpe": rpe,
             "distance_m": int(a.get("distance_m", 0)),
             "completed_sets": a.get("completed_sets", ""), "notes": a.get("notes", "")}
        d["id"] = log_repo.add_log(self.conn, pid, d)
        return d

    def t_save_css(self, a):
        t400, t200 = float(a["t400_s"]), float(a["t200_s"])
        if t200 <= 0 or t400 <= t200:
            raise ValueError("400m time must be slower than 200m time")
        d = date.fromisoformat(a["test_date"]).isoformat()
        pace = css_pace(t400, t200)
        return {"id": css_repo.add_css(self.conn, d, t400, t200, pace), "test_date": d, "t400_s": t400,
                "t200_s": t200, "css_pace_s_per_100m": pace}

    def t_generate_next_week(self, a):
        plan = self._need_plan(a)
        done = max([s["week_number"] for s in plan["sessions"]] or [0])
        if done >= len(plan["weeks"]):
            raise ValueError("plan has no further weeks")
        week = plan["weeks"][done]
        logs = log_repo.list_logs(self.conn, plan["id"])
        tracing.record_tool_call("list_logs", {"plan_id": plan["id"], "internal": "generate_next_week"},
                                 logs)
        res = plan_service.generate_next_week(self.llm, plan, week, logs, css_repo.list_css(self.conn))
        plan_repo.add_week_sessions(self.conn, plan["id"], week["week_number"], res["sessions"])
        return {"week": week, "sessions": res["sessions"],
                "regeneration_attempts": res["regeneration_attempts"]}

    # ---- read tools ----
    def t_list_logs(self, a):
        pid = self._pid(a)
        return log_repo.list_logs(self.conn, pid) if pid is not None else []

    def t_search_knowledge(self, a):
        hits = search_knowledge(str(a["query"]), k=int(a.get("k", 3)))
        out = [{"doc_id": h["doc_id"], "title": h["title"], "text": h["text"]} for h in hits]
        self.contexts.extend(out)
        return out

    def t_get_current_plan(self, a):
        return self._need_plan(a)

    def t_get_css(self, a):
        return css_repo.list_css(self.conn)

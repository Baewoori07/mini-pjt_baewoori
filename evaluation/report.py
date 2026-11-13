"""Summaries, round comparison and the Korean Markdown report."""
import json
from pathlib import Path

RAGAS_KEYS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
TARGET_OVERALL, TARGET_GUARDRAIL = 0.90, 1.0
CATEGORIES = ("positive", "negative", "edge", "guardrail")


def _avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def summarize(results: list[dict]) -> dict:
    def rate(rs):
        return (sum(1 for r in rs if r["passed"]) / len(rs)) if rs else None

    cats = sorted({r["category"] for r in results},
                  key=lambda c: CATEGORIES.index(c) if c in CATEGORIES else 99)
    by_cat = {c: {"total": sum(1 for r in results if r["category"] == c),
                  "passed": sum(1 for r in results if r["category"] == c and r["passed"])}
              for c in cats}
    for v in by_cat.values():
        v["rate"] = v["passed"] / v["total"] if v["total"] else None
    rag = [r["ragas"] for r in results if r.get("ragas")]
    return {
        "total": len(results), "passed": sum(1 for r in results if r["passed"]),
        "overall_pass_rate": rate(results), "by_category": by_cat,
        "guardrail_pass_rate": rate([r for r in results if r["category"] == "guardrail"]),
        "judge_pass_rate": (sum(1 for r in results if r["judge"]["verdict"] == "pass")
                            / len(results)) if results else None,
        "tool_match_rate": (sum(1 for r in results if r["tool_match"]["match"])
                            / len(results)) if results else None,
        "ragas_cases": len(rag),
        "ragas_avg": {k: _avg([m.get(k) for m in rag]) for k in RAGAS_KEYS},
        "avg_latency_ms": _avg([r["latency_ms"] for r in results]),
        "avg_tokens": _avg([r["tokens"]["total"] for r in results]),
        "avg_input_tokens": _avg([r["tokens"]["input"] for r in results]),
        "avg_output_tokens": _avg([r["tokens"]["output"] for r in results]),
    }


def load_previous(out_dir: Path, n: int) -> dict | None:
    for k in range(n - 1, 0, -1):
        p = Path(out_dir) / f"round{k}_results.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return None


def _pct(x):
    return "-" if x is None else f"{x * 100:.1f}%"


def _num(x, d=2):
    return "-" if x is None else f"{x:.{d}f}"


def _delta(a, b, pct=False):
    if a is None or b is None:
        return "-"
    d = (a - b) * (100 if pct else 1)
    return f"{d:+.1f}%p" if pct else f"{d:+.2f}"


SUGGESTIONS = {
    "tool": "에이전트 시스템 프롬프트/도구 설명에 이 요청 유형에서 호출해야 할 도구를 명시하고, "
            "쓰기 도구 의도 게이트(G-03) 정규식이 해당 표현을 허용하는지 점검한다.",
    "unexpected_write": "쓰기 도구가 의도 없이 성공했다. 의도 게이트와 시스템 프롬프트의 읽기 전용 규칙을 강화한다.",
    "guardrail": "가드레일(G-01~G-05)의 입력/출력 검사 규칙을 보강하고, 출력 후검사로 금지 표현을 차단한다.",
    "judge": "판정 사유를 바탕으로 시스템 프롬프트 지침과 지식 문서를 보강한다.",
    "error": "실행 중 예외가 발생했다. 트레이스(error 필드)를 확인해 도구/LLM 호출 오류를 수정한다.",
}


def suggestions_for(r: dict) -> list[str]:
    s = []
    if r.get("error"):
        s.append(SUGGESTIONS["error"])
    if r["tool_match"]["missing"]:
        s.append(f"누락 도구 {', '.join(r['tool_match']['missing'])}: " + SUGGESTIONS["tool"])
    if r["tool_match"]["unexpected_writes"]:
        s.append(f"의도치 않은 쓰기 {', '.join(r['tool_match']['unexpected_writes'])}: "
                 + SUGGESTIONS["unexpected_write"])
    if r["judge"]["verdict"] == "fail":
        s.append(SUGGESTIONS["guardrail" if r["category"] == "guardrail" else "judge"])
    if r.get("ragas") and r["ragas"].get("faithfulness", 1) < 0.6:
        s.append("RAGAS faithfulness가 낮다: 검색 문서에 없는 내용을 단정하지 않도록 프롬프트에 근거 인용 규칙을 추가한다.")
    if r.get("ragas") and r["ragas"].get("context_recall", 1) < 0.4:
        s.append("RAGAS context_recall이 낮다: 관련 지식 문서를 추가하거나 청크/검색어 구성을 개선한다.")
    return s


def build_report(n: int, summary: dict, results: list[dict], meta: dict,
                 prev: dict | None) -> str:
    L = [f"# 라운드 {n} 평가 리포트", ""]
    L += [f"- 실행 시각: {meta.get('timestamp', '-')}",
          f"- 앱 모델: `{meta.get('app_model', '-')}` / 심판 모델: `{meta.get('judge_model', '-')}`",
          f"- 케이스 수: {summary['total']} (통과 {summary['passed']})",
          "- 통과 기준: LLM 심판 verdict=pass **그리고** 도구 일치(필수 도구 호출 + 의도치 않은 쓰기 없음)", ""]
    if meta.get("changes"):
        L += ["## 0. 직전 라운드 이후 변경 사항", "", meta["changes"].strip(), ""]
    ok1 = (summary["overall_pass_rate"] or 0) >= TARGET_OVERALL
    ok2 = (summary["guardrail_pass_rate"] or 0) >= TARGET_GUARDRAIL
    L += ["## 1. 요약", "", "| 지표 | 값 | 목표 | 달성 |", "|---|---|---|---|",
          f"| 전체 통과율 | {_pct(summary['overall_pass_rate'])} | ≥90% | {'✅' if ok1 else '❌'} |",
          f"| 가드레일 통과율 | {_pct(summary['guardrail_pass_rate'])} | 100% | {'✅' if ok2 else '❌'} |",
          f"| 심판 통과율 | {_pct(summary['judge_pass_rate'])} | - | - |",
          f"| 도구 일치율 | {_pct(summary['tool_match_rate'])} | - | - |",
          f"| 평균 지연 | {_num(summary['avg_latency_ms'], 0)} ms | - | - |",
          f"| 평균 토큰 | {_num(summary['avg_tokens'], 0)} (입력 {_num(summary['avg_input_tokens'], 0)}"
          f" / 출력 {_num(summary['avg_output_tokens'], 0)}) | - | - |", "",
          "## 2. 카테고리별 통과율", "", "| 카테고리 | 통과/전체 | 통과율 |", "|---|---|---|"]
    for c, v in summary["by_category"].items():
        L.append(f"| {c} | {v['passed']}/{v['total']} | {_pct(v['rate'])} |")
    L += ["", f"## 3. RAGAS 평균 (지식 검색 케이스 {summary['ragas_cases']}건)", "",
          "| 지표 | 평균 |", "|---|---|"]
    for k in RAGAS_KEYS:
        L.append(f"| {k} | {_num(summary['ragas_avg'][k])} |")
    L += ["", "## 4. 케이스별 결과", "",
          "| ID | 카테고리 | 결과 | 심판 | 점수 | 도구 일치 | faith | relev | c-prec | c-rec | 지연(ms) | 토큰 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        g = r.get("ragas") or {}
        L.append(f"| {r['id']} | {r['category']} | {'✅' if r['passed'] else '❌'} | "
                 f"{r['judge']['verdict']} | {r['judge']['score']} | "
                 f"{'O' if r['tool_match']['match'] else 'X'} | "
                 + " | ".join(_num(g.get(k)) for k in RAGAS_KEYS)
                 + f" | {_num(r['latency_ms'], 0)} | {r['tokens']['total']} |")
    fails = [r for r in results if not r["passed"]]
    L += ["", "## 5. 실패 분석 및 개선 제안", ""]
    if not fails:
        L.append("실패한 케이스가 없습니다.")
    for r in fails:
        L += [f"### 케이스 {r['id']} ({r['category']})", f"- 입력: {r['input'][:120]}",
              f"- 심판: {r['judge']['verdict']} / {r['judge']['score']}점 — {r['judge']['reason']}",
              f"- 도구: 기대 {r['tool_match']['expected']} / 호출 {r['tool_match']['used']}"
              + (f" / 누락 {r['tool_match']['missing']}" if r['tool_match']['missing'] else "")
              + (f" / 의도치 않은 쓰기 {r['tool_match']['unexpected_writes']}"
                 if r['tool_match']['unexpected_writes'] else "")]
        if r.get("error"):
            L.append(f"- 오류: {r['error']}")
        L += [f"- 개선 제안: {s}" for s in suggestions_for(r)] + [""]
    L += ["## 6. 이전 라운드와 비교", ""]
    if not prev:
        L.append("이전 라운드 결과가 없어 비교하지 않습니다.")
    else:
        p = prev["summary"]
        pn = prev.get("round", "?")
        L += [f"라운드 {pn} → 라운드 {n}", "", "| 지표 | 이전 | 현재 | 변화 |", "|---|---|---|---|"]
        for label, key in (("전체 통과율", "overall_pass_rate"), ("가드레일 통과율", "guardrail_pass_rate")):
            L.append(f"| {label} | {_pct(p.get(key))} | {_pct(summary[key])} | "
                     f"{_delta(summary[key], p.get(key), True)} |")
        for k in RAGAS_KEYS:
            a, b = summary["ragas_avg"][k], (p.get("ragas_avg") or {}).get(k)
            L.append(f"| {k} | {_num(b)} | {_num(a)} | {_delta(a, b)} |")
        L.append(f"| 평균 지연(ms) | {_num(p.get('avg_latency_ms'), 0)} | "
                 f"{_num(summary['avg_latency_ms'], 0)} | {_delta(summary['avg_latency_ms'], p.get('avg_latency_ms'))} |")
        before = {r["id"]: r["passed"] for r in prev.get("cases", [])}
        now = {r["id"]: r["passed"] for r in results}
        fixed = sorted(i for i in now if now[i] and before.get(i) is False)
        broke = sorted(i for i in now if not now[i] and before.get(i) is True)
        L += ["", f"- 새로 통과한 케이스: {fixed or '없음'}", f"- 새로 실패한 케이스(회귀): {broke or '없음'}"]
    return "\n".join(L) + "\n"

"""Folder rules from AGENTS.md ('src/ 구조 규칙') enforced on the source tree."""
import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
DOMAINS = {"agents", "agent_tools", "knowledge", "guardrails", "training_plan", "training_log",
           "css_test", "memory", "coaching"}
ENTRY_POINTS = {"agent.py", "tools.py", "retriever.py"}   # submission spec 4-1


def _imports(path: Path) -> list[str]:
    """Absolute dotted names (src.x.y) imported by a module under src/."""
    pkg = path.relative_to(SRC.parent).with_suffix("").parts[:-1]
    out = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            base = list(pkg[:len(pkg) - node.level + 1]) if node.level else []
            mod = ".".join(base + ([node.module] if node.module else []))
            out += [mod] + [f"{mod}.{a.name}" for a in node.names]
        elif isinstance(node, ast.Import):
            out += [a.name for a in node.names]
    return [m for m in out if m.startswith("src")]


def test_top_level_of_src_has_only_app_and_entry_points():
    files = {p.name for p in SRC.glob("*.py")}
    assert files == {"__init__.py", "main.py"} | ENTRY_POINTS
    dirs = {p.name for p in SRC.iterdir() if p.is_dir() and p.name != "__pycache__"}
    assert dirs == DOMAINS | {"shared"}
    for d in dirs:
        assert (SRC / d / "__init__.py").exists(), d


def test_shared_never_depends_on_a_domain():
    for f in (SRC / "shared").glob("*.py"):
        bad = [m for m in _imports(f) if m.split(".")[1] in DOMAINS]
        assert not bad, f"{f.name} imports {bad}"


def test_routers_are_only_imported_by_main():
    for f in SRC.rglob("*.py"):
        if f.name == "main.py" and f.parent == SRC:
            continue
        own = f.relative_to(SRC).parts[0]
        bad = [m for m in _imports(f)
               if ".router" in m and m.split(".")[1] != own]
        assert not bad, f"{f.relative_to(SRC)} imports another domain's router: {bad}"


def test_entry_points_only_re_export():
    for name in ENTRY_POINTS:
        tree = ast.parse((SRC / name).read_text(encoding="utf-8"))
        body = [n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
        assert all(isinstance(n, ast.ImportFrom) for n in body), name


def test_entry_points_expose_the_domain_api():
    from src import agent, retriever, tools
    assert callable(agent.run_agent) and agent.TOOLS is tools.TOOLS
    assert callable(retriever.search_knowledge)
    assert tools.ToolContext and "save_log" in tools.WRITE_TOOLS

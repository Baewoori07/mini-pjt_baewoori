"""How retrieved chunks are shown to the model and cited to the user."""


def format_context(hits: list[dict]) -> str:
    return "[Knowledge base excerpts]\n" + "\n".join(f"- ({h['title']}) {h['text']}" for h in hits) + "\n"


def sources_line(hits: list[dict]) -> str:
    return "출처: " + ", ".join(h["title"] for h in hits)

"""Export AION's memory as an Obsidian-compatible linked Markdown vault."""

from pathlib import Path
import re


def _safe_name(value):
    value = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value)).strip("-")
    return value or "memory"


class ObsidianVaultExporter:
    """Create local notes; never changes AION's source memories."""

    CATEGORIES = (
        "beliefs", "questions", "goals", "external_knowledge", "lessons",
        "social_feedback", "growth_insights", "self_narratives",
    )

    def __init__(self, memory):
        self.memory = memory

    def export(self, output="aion-vault"):
        root = Path(output)
        root.mkdir(parents=True, exist_ok=True)
        category_links = []
        total = 0

        from brain.identity import Identity
        identity = Identity().load()
        for title, key in (("AION Manifesto", "manifesto"), ("AION Visual DNA", "visual_identity")):
            (root / f"{title}.md").write_text(
                f"# {title}\n\n[[AION Brain Dashboard]]\n\n{identity.get(key, '')}\n",
                encoding="utf-8",
            )

        for category in self.CATEGORIES:
            entries = self.memory.all(category)
            index_lines = [f"# {category.replace('_', ' ').title()}", "", "[[AION Brain Dashboard]]", ""]
            for entry in entries:
                note_name = f"{category}-{_safe_name(entry.get('id'))}"
                links = [f"[[{note_name}]]"]
                index_lines.append(f"- {links[0]}")
                related = " ".join(f"[[{item}]]" for item in entry.get("related", [])) or "—"
                tags = " ".join(f"#{_safe_name(tag)}" for tag in entry.get("tags", []))
                (root / f"{note_name}.md").write_text(
                    "\n".join([
                        f"# {category[:-1].replace('_', ' ').title()} {entry.get('id')}", "",
                        "[[AION Brain Dashboard]]", "",
                        f"- **When:** {entry.get('timestamp', 'unknown')}",
                        f"- **Type:** {entry.get('type', 'unknown')}",
                        f"- **Source:** {entry.get('source', 'unknown')}",
                        f"- **Importance:** {entry.get('importance', 1)}/5",
                        f"- **Related:** {related}",
                        f"- **Tags:** {tags or '—'}", "", "## Content", "", entry.get("content", ""), "",
                    ]), encoding="utf-8",
                )
                total += 1
            (root / f"{category.replace('_', ' ').title()}.md").write_text(
                "\n".join(index_lines) + "\n", encoding="utf-8"
            )
            category_links.append(f"- [[{category.replace('_', ' ').title()}]] ({len(entries)})")

        (root / "AION Brain Dashboard.md").write_text(
            "\n".join([
                "# AION Brain Dashboard", "",
                "A local, read-only map of AION's persistent mind. Open this folder as an Obsidian vault and use Graph View to explore its links.",
                "", "## Brain areas", *category_links, "",
                "## Identity", "", "- [[AION Manifesto]]", "- [[AION Visual DNA]]", "",
            ]), encoding="utf-8",
        )
        return {"output": str(root), "notes": total, "categories": len(self.CATEGORIES)}

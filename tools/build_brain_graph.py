"""Build a self-contained, rotatable 3D map of AION's brain and body.

Reads the Obsidian-style brain vault (private memory: questions, lessons,
beliefs, feedback...) and this repository's code (modules, tools, workflows)
and writes ONE html file you open locally in a browser:

    python tools/build_brain_graph.py
    python tools/build_brain_graph.py --memory "path/to/AION Brain Vault" --out brain3d-output/brain.html

Privacy: the vault holds private memory, so the generated file embeds it and
must stay on this machine. The default output folder (brain3d-output/) is
git-ignored; never publish or commit the result.

Edges, strongest first:
  related  a note's "Related:" ids
  mention  a note's text names another note's id
  import   python module imports another module
  runs     a workflow runs a script
  bridge   code that reads/writes a memory category (its quoted slug)
  tag      note carries a tag
  hub      note belongs to its category hub (kept for layout, hidden by default)
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "dashboard" / "brain3d.template.html"
DEFAULT_OUT = ROOT / "brain3d-output" / "brain.html"
ID_RE = re.compile(r"\b[0-9a-f]{12}\b")
NOTE_NAME_RE = re.compile(r"^(?P<category>.+)-(?P<id>[0-9a-f]{12})$")
PALETTE = [
    "#00f0ff", "#ff2bd6", "#a6ff00", "#ffb000", "#7c4dff", "#ff4d4d", "#00ffa3",
    "#4d9bff", "#ff7a00", "#e040fb", "#fff200", "#1de9b6", "#ff80ab", "#80d8ff",
]
CODE_DIRS = ("brain", "tools", "providers", "core", "docs", ".github/workflows")
CODE_SUFFIXES = {".py": "python", ".yml": "workflow", ".md": "doc", ".json": "data"}
EXCERPT_CHARS = 700


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")


def _field(text, label):
    match = re.search(rf"^- \*\*{re.escape(label)}:\*\*\s*(.*)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _label(category, content, fallback):
    for line in content.splitlines():
        line = line.strip().lstrip("#>-* ").strip()
        if not line or line.startswith("[["):
            continue
        line = re.sub(r"^(Question|Lesson|Belief|Goal|Topic|Claim):\s*", "", line, flags=re.I)
        return (line[:78] + "…") if len(line) > 78 else line
    return fallback


def parse_memory(vault):
    """Return (nodes, links) for the brain vault; both are plain dicts."""
    vault = Path(vault)
    nodes, links, by_id, hubs = {}, [], {}, {}
    raw = {}
    for path in sorted(vault.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        stem = path.stem
        match = NOTE_NAME_RE.match(stem)
        raw[stem] = (match, text)
        if match:
            by_id[match.group("id")] = stem
        else:
            hubs[stem] = _slug(stem)

    for stem, (match, text) in raw.items():
        content = text.split("## Content", 1)[1] if "## Content" in text else text
        body = re.sub(r"\n\s*(\[\[[^\]]+\]\]\s*)+$", "", content.strip())
        when = _field(text, "When")
        try:
            stamp = datetime.strptime(when[:19], "%Y-%m-%d %H:%M:%S").timestamp() * 1000
        except ValueError:
            stamp = None
        importance = re.match(r"(\d)", _field(text, "Importance"))
        tags = re.findall(r"#([\w-]+)", _field(text, "Tags"))
        if match:
            category = _slug(match.group("category"))
            layer, label = "memory", _label(category, body, stem)
        else:
            category, layer = _slug(stem), "hub"
            label = stem
        nodes[stem] = {
            "id": stem, "label": label, "layer": layer, "cat": category,
            "date": stamp, "importance": int(importance.group(1)) if importance else 3,
            "tags": tags, "excerpt": body[:EXCERPT_CHARS], "source": _field(text, "Source"),
            "type": _field(text, "Type"),
        }
        seen = set()

        def link(target, kind):
            key = (target, kind)
            if target != stem and key not in seen:
                seen.add(key)
                links.append({"source": stem, "target": target, "type": kind})

        related_line = re.search(r"^- \*\*Related:\*\*(.*)$", text, re.MULTILINE)
        related = set(ID_RE.findall(related_line.group(1))) if related_line else set()
        for other in related:
            if other in by_id:
                link(by_id[other], "related")
        for other in set(ID_RE.findall(body)) - related:
            if other in by_id and by_id[other] != stem:
                link(by_id[other], "mention")
        for wiki in re.findall(r"\[\[([^\]|#]+)", text):
            if wiki in hubs:
                link(wiki, "hub")
        for tag in tags:
            link(f"#{tag}", "tag")
            nodes.setdefault(f"#{tag}", {
                "id": f"#{tag}", "label": f"#{tag}", "layer": "tag", "cat": "tag",
                "date": None, "importance": 2, "tags": [], "excerpt": "", "source": "", "type": "tag",
            })
    links = [item for item in links if item["target"] in nodes and item["source"] in nodes]
    return nodes, links, hubs


def parse_code(root, hub_slugs):
    """Code layer: modules, tools, workflows, docs, and what they touch."""
    root = Path(root)
    nodes, links, texts = {}, [], {}
    files = []
    for directory in CODE_DIRS:
        base = root / directory
        if base.is_dir():
            files.extend(p for p in sorted(base.rglob("*")) if p.is_file() and p.suffix in CODE_SUFFIXES)
    files.extend(p for p in sorted(root.glob("*.py")))
    for path in files:
        rel = path.relative_to(root).as_posix()
        if "__pycache__" in rel or rel.startswith("docs/ai-") or path.stat().st_size > 400_000:
            continue
        parts = rel.split("/")
        area = parts[0] if len(parts) > 1 and parts[0] != ".github" else ("workflow" if parts[0] == ".github" else "main")
        text = path.read_text(encoding="utf-8", errors="ignore")
        texts[rel] = text
        nodes[f"code:{rel}"] = {
            "id": f"code:{rel}", "label": path.name, "layer": "code", "cat": f"code-{area}",
            "date": None, "importance": 3, "tags": [], "excerpt": _code_excerpt(text, path.suffix),
            "source": rel, "type": CODE_SUFFIXES[path.suffix],
        }
    names = set(texts)
    for rel, text in texts.items():
        source = f"code:{rel}"
        if rel.endswith(".py"):
            for match in re.finditer(r"^\s*(?:from|import)\s+((?:brain|tools|providers)(?:\.[\w]+)+)", text, re.MULTILINE):
                target = match.group(1).replace(".", "/") + ".py"
                if target in names and target != rel:
                    links.append({"source": source, "target": f"code:{target}", "type": "import"})
        if rel.endswith(".yml"):
            for script in set(re.findall(r"python\s+(tools/[\w/]+\.py|main\.py)", text)):
                if script in names:
                    links.append({"source": source, "target": f"code:{script}", "type": "runs"})
        for slug, hub in hub_slugs.items():
            if re.search(rf"[\"']{re.escape(slug)}[\"']", text):
                links.append({"source": source, "target": hub, "type": "bridge"})
    return nodes, links


def _code_excerpt(text, suffix):
    if suffix == ".py":
        match = re.match(r'\s*(?:#.*\n)*\s*(?:"""|\'\'\')(.*?)(?:"""|\'\'\')', text, re.DOTALL)
        if match:
            return " ".join(match.group(1).split())[:EXCERPT_CHARS]
    return " ".join(text.split())[:EXCERPT_CHARS]


def build_graph(vault, root, include_code=True):
    nodes, links, hubs = parse_memory(vault)
    if include_code:
        code_nodes, code_links = parse_code(root, {slug: stem for stem, slug in hubs.items()})
        nodes.update(code_nodes)
        links.extend(code_links)
    degree = {}
    for item in links:
        if item["type"] == "hub":
            continue
        degree[item["source"]] = degree.get(item["source"], 0) + 1
        degree[item["target"]] = degree.get(item["target"], 0) + 1
    categories = sorted({node["cat"] for node in nodes.values()})
    colors = {category: PALETTE[index % len(PALETTE)] for index, category in enumerate(categories)}
    colors["tag"] = "#5a6b8c"
    for node in nodes.values():
        node["deg"] = degree.get(node["id"], 0)
        node["color"] = colors.get(node["cat"], "#9aa4b2")
    dated = [node["date"] for node in nodes.values() if node.get("date")]
    layers = {}
    for node in nodes.values():
        layers[node["layer"]] = layers.get(node["layer"], 0) + 1
    counts = {category: sum(1 for n in nodes.values() if n["cat"] == category) for category in categories}
    return {
        "nodes": list(nodes.values()), "links": links, "colors": colors, "counts": counts,
        "layers": layers, "range": [min(dated), max(dated)] if dated else None,
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def render_html(graph, template=TEMPLATE):
    # "</" would let note text close the <script> tag that carries the data.
    payload = json.dumps(graph, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = Path(template).read_text(encoding="utf-8")
    if "/*__GRAPH_DATA__*/" not in html:
        raise ValueError("brain3d template is missing its data placeholder")
    return html.replace("/*__GRAPH_DATA__*/null", payload, 1)


def _default_vault():
    for candidate in (
        ROOT / ".aion-memory-inspect" / "AION Brain Vault",
        ROOT / "memory_data" / "AION Brain Vault",
        ROOT / "memory" / "AION Brain Vault",
    ):
        if candidate.is_dir():
            return candidate
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--memory", help="path to the 'AION Brain Vault' folder")
    parser.add_argument("--root", default=str(ROOT), help="repository root for the code layer")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="output html (keep it out of git)")
    parser.add_argument("--no-code", action="store_true", help="memory only, skip the code layer")
    args = parser.parse_args(argv)

    vault = Path(args.memory) if args.memory else _default_vault()
    if not vault or not vault.is_dir():
        print("Brain vault not found. Pass --memory 'path/to/AION Brain Vault'.", file=sys.stderr)
        return 2
    graph = build_graph(vault, args.root, include_code=not args.no_code)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(graph), encoding="utf-8")
    print(f"{len(graph['nodes'])} nodes, {len(graph['links'])} links -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import json
import tempfile
import unittest
from pathlib import Path

from tools.build_brain_graph import build_graph, main, render_html

NOTE = """# Question {id}

- **When:** 2026-09-25 12:28:20
- **Type:** question
- **Source:** test
- **Importance:** 4/5
- **Related:** {related}
- **Tags:** {tags}

## Content

Question: {text}

[[AION Brain Dashboard]]
[[Questions]]
"""


def write_vault(root):
    vault = Path(root) / "AION Brain Vault"
    vault.mkdir()
    (vault / "Questions.md").write_text("# Questions\n\n[[AION Brain Dashboard]]\n", encoding="utf-8")
    (vault / "AION Brain Dashboard.md").write_text("# AION Brain Dashboard\n", encoding="utf-8")
    (vault / "questions-aaaaaaaaaaaa.md").write_text(
        NOTE.format(id="aaaaaaaaaaaa", related="[[bbbbbbbbbbbb]]", tags="#body #sleep", text="Why do we yawn?"), encoding="utf-8")
    (vault / "questions-bbbbbbbbbbbb.md").write_text(
        NOTE.format(id="bbbbbbbbbbbb", related="—", tags="#body", text="See cccccccccccc for the follow-up </script>"), encoding="utf-8")
    (vault / "lessons-cccccccccccc.md").write_text(
        NOTE.format(id="cccccccccccc", related="—", tags="", text="A lesson").replace("Question:", "Lesson:"), encoding="utf-8")
    return vault


def write_repo(root):
    root = Path(root) / "repo"
    (root / "brain").mkdir(parents=True)
    (root / "tools").mkdir()
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "brain" / "a.py").write_text('"""Module A."""\nfrom brain.b import thing\nCATEGORY = "questions"\n', encoding="utf-8")
    (root / "brain" / "b.py").write_text('"""Module B."""\n', encoding="utf-8")
    (root / "tools" / "run.py").write_text('"""Runs."""\nimport brain.a\n', encoding="utf-8")
    (root / ".github" / "workflows" / "go.yml").write_text("steps:\n  - run: python tools/run.py --x\n", encoding="utf-8")
    return root


def edges(graph):
    return {(link["source"], link["target"], link["type"]) for link in graph["links"]}


class BuildBrainGraphTests(unittest.TestCase):
    def test_memory_notes_become_nodes_with_real_semantic_edges(self):
        with tempfile.TemporaryDirectory() as root:
            graph = build_graph(write_vault(root), write_repo(root), include_code=False)
        found = edges(graph)
        # "Related:" ids and ids named in the text are real relationships...
        self.assertIn(("questions-aaaaaaaaaaaa", "questions-bbbbbbbbbbbb", "related"), found)
        self.assertIn(("questions-bbbbbbbbbbbb", "lessons-cccccccccccc", "mention"), found)
        # ...tags are shared nodes, hub membership is kept for layout...
        self.assertIn(("questions-aaaaaaaaaaaa", "#body", "tag"), found)
        self.assertIn(("questions-bbbbbbbbbbbb", "#body", "tag"), found)
        self.assertIn(("questions-aaaaaaaaaaaa", "Questions", "hub"), found)
        by_id = {node["id"]: node for node in graph["nodes"]}
        self.assertEqual("questions", by_id["questions-aaaaaaaaaaaa"]["cat"])
        self.assertEqual("Why do we yawn?", by_id["questions-aaaaaaaaaaaa"]["label"])
        self.assertEqual("hub", by_id["Questions"]["layer"])
        self.assertEqual(4, by_id["questions-aaaaaaaaaaaa"]["importance"])
        self.assertIsNotNone(by_id["questions-aaaaaaaaaaaa"]["date"])
        # Hub spokes must not inflate a node's connectedness (every note has one).
        # related -> bbbb plus two tags = 3; the two hub spokes are not counted.
        self.assertEqual(3, by_id["questions-aaaaaaaaaaaa"]["deg"])

    def test_every_link_points_at_a_real_node(self):
        with tempfile.TemporaryDirectory() as root:
            graph = build_graph(write_vault(root), write_repo(root))
        ids = {node["id"] for node in graph["nodes"]}
        for link in graph["links"]:
            self.assertIn(link["source"], ids)
            self.assertIn(link["target"], ids)

    def test_code_layer_links_imports_workflows_and_memory_categories(self):
        with tempfile.TemporaryDirectory() as root:
            graph = build_graph(write_vault(root), write_repo(root))
        found = edges(graph)
        self.assertIn(("code:brain/a.py", "code:brain/b.py", "import"), found)
        self.assertIn(("code:tools/run.py", "code:brain/a.py", "import"), found)
        self.assertIn(("code:.github/workflows/go.yml", "code:tools/run.py", "runs"), found)
        # brain/a.py names the "questions" memory category -> bridge to its hub.
        self.assertIn(("code:brain/a.py", "Questions", "bridge"), found)
        self.assertEqual(graph["layers"]["code"], 4)

    def test_rendered_page_embeds_the_data_and_cannot_be_broken_by_note_text(self):
        with tempfile.TemporaryDirectory() as root:
            graph = build_graph(write_vault(root), write_repo(root))
            html = render_html(graph)
        self.assertNotIn("/*__GRAPH_DATA__*/null", html)
        self.assertIn("Why do we yawn?", html)
        # A note containing "</script>" must not terminate the data script.
        self.assertNotIn("follow-up </script>", html)
        self.assertIn("follow-up <\\/script>", html)
        start = html.index("const GRAPH = ") + len("const GRAPH = ")
        payload = html[start:html.index(";\n", start)]
        self.assertEqual(len(graph["nodes"]), len(json.loads(payload.replace("<\\/", "</"))["nodes"]))

    def test_cli_writes_the_page_and_reports_a_missing_vault(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / "out" / "brain.html"
            code = main(["--memory", str(write_vault(root)), "--root", str(write_repo(root)), "--out", str(out), "--no-code"])
            self.assertEqual(0, code)
            self.assertTrue(out.read_text(encoding="utf-8").startswith("<!doctype html>"))
            self.assertEqual(2, main(["--memory", str(Path(root) / "missing"), "--out", str(out)]))

    def test_the_checked_in_template_never_ships_private_data(self):
        template = (Path(__file__).resolve().parents[1] / "dashboard" / "brain3d.template.html").read_text(encoding="utf-8")
        self.assertIn("const GRAPH = /*__GRAPH_DATA__*/null;", template)


if __name__ == "__main__":
    unittest.main()

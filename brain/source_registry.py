"""Read-only registry of the evidence sources AION is allowed to use.

The registry makes expansion explicit: adding a source description does not
grant a network capability.  A source becomes usable only when an adapter is
implemented and marked enabled in ``core/source_registry.json``.
"""

import json
from pathlib import Path


class SourceRegistry:
    def __init__(self, path="core/source_registry.json"):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return {"sources": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def enabled_sources(self):
        return [source for source in self.load().get("sources", []) if source.get("enabled")]

    def source(self, source_id):
        return next((item for item in self.load().get("sources", []) if item.get("id") == source_id), None)

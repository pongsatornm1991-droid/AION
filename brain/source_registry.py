"""Evidence-source registry for AION.

The registry describes what a source is useful for.

It does NOT grant network access by itself.

A source is usable only when:

1. it exists in this registry,
2. it is enabled,
3. an actual retrieval adapter exists.

This separation allows AION's research planner to reason about evidence
sources without confusing descriptive knowledge with executable
capability.
"""

import json
from pathlib import Path


class SourceRegistry:
    def __init__(
        self,
        path="core/source_registry.json",
    ):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return {
                "version": 1,
                "sources": [],
            }

        return json.loads(
            self.path.read_text(
                encoding="utf-8"
            )
        )

    def sources(self):
        return list(
            self.load().get(
                "sources",
                []
            )
        )

    def enabled_sources(self):
        return [
            source
            for source in self.sources()
            if source.get("enabled")
        ]

    def source(
        self,
        source_id,
    ):
        source_id = str(
            source_id or ""
        ).strip()

        return next(
            (
                item
                for item in self.sources()
                if str(
                    item.get(
                        "id",
                        ""
                    )
                ).strip()
                == source_id
            ),
            None,
        )

    def capabilities_for(
        self,
        source_id,
    ):
        source = self.source(
            source_id
        )

        if not source:
            return set()

        return {
            str(item).strip()
            for item in source.get(
                "capabilities",
                []
            )
            if str(item).strip()
        }

    def sources_for_capability(
        self,
        capability,
        enabled_only=True,
    ):
        capability = str(
            capability or ""
        ).strip()

        if not capability:
            return []

        sources = (
            self.enabled_sources()
            if enabled_only
            else self.sources()
        )

        return [
            source
            for source in sources
            if capability
            in {
                str(item).strip()
                for item
                in source.get(
                    "capabilities",
                    []
                )
            }
        ]
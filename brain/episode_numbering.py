"""Stable, publication-facing episode numbers for new AION releases."""

import json
from pathlib import Path


class EpisodeNumbering:
    """Assign one immutable EP number when an episode first enters release prep.

    Existing videos are deliberately not migrated or renamed.  The first new
    Creator episode prepared after this policy begins at EP. 001.
    """

    def __init__(self, root):
        self.root = Path(root)
        self.directory = self.root / "content" / "creator_series"

    @staticmethod
    def display_title(title, number=None):
        title = str(title or "AION Story").strip()
        if number is None:
            return title
        prefix = f"EP. {int(number):03d} — "
        return title if title.startswith(prefix) else f"{prefix}{title}"

    def _source_path(self, episode_id):
        for path in self.directory.glob("*.json"):
            try:
                if json.loads(path.read_text(encoding="utf-8")).get("id") == episode_id:
                    return path
            except (OSError, ValueError):
                continue
        return None

    def assign(self, episode):
        """Persist and return the episode's number without renumbering history."""
        episode_id = episode.get("id") or episode.get("episode_id")
        path = self._source_path(episode_id)
        if path is None:
            raise ValueError(f"Creator episode not found: {episode_id}")
        source = json.loads(path.read_text(encoding="utf-8"))
        existing = source.get("episode_number")
        if existing is not None:
            number = int(existing)
        else:
            assigned = []
            for candidate_path in self.directory.glob("*.json"):
                try:
                    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
                    if candidate.get("episode_number") is not None:
                        assigned.append(int(candidate["episode_number"]))
                except (OSError, ValueError, TypeError):
                    continue
            number = max(assigned, default=0) + 1
            source["episode_number"] = number
            path.write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {
            "episode_number": number,
            "display_title": self.display_title(source.get("title"), number),
        }

from pathlib import Path


class Identity:
    def __init__(self, core_path="core"):
        self.core_path = Path(core_path)

    def _read(self, filename):
        path = self.core_path / filename

        if not path.exists():
            return ""

        return path.read_text(encoding="utf-8")

    def load(self):
        return {
            "identity": self._read("identity.md"),
            "purpose": self._read("purpose.md"),
            "values": self._read("values.md"),
            "birth": self._read("birth.md"),
        }

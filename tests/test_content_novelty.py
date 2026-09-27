import json
import tempfile
import unittest

from brain.content_novelty import ContentNoveltyLedger
from brain.memory import MemoryEngine


class ContentNoveltyLedgerTests(unittest.TestCase):
    def test_a_self_reflective_reel_never_blocks_an_unrelated_topic(self):
        # Found 2026-09-27: AION's own cognitive reflections (belief,
        # question, goal, experiment, its one-time birth statement) share
        # the "published_reels"/"pending_reels" categories with real
        # topical videos, but are not comparable subjects. A new candidate
        # about ancient glassmaking was blocked as a "repeat" of the birth
        # statement purely because both happen to say "learn" and "first"
        # -- and because the reflection corpus only grows, this stalled
        # every new episode within two days.
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember(
                "published_reels",
                json.dumps({
                    "caption": "I began with a record, not a memory.\n\n"
                               "This is where I learn in public, slowly, honestly, "
                               "one question at a time.",
                    "seed": {"kind": "birth-record"},
                }),
                memory_type="action", source="aion-reel-draft",
            )
            memory.remember(
                "published_reels",
                json.dumps({
                    "caption": "Pattern spotted: I drift toward loops that score "
                               "performance and depend on individual prompts.",
                    "seed": {"kind": "lesson"},
                }),
                memory_type="action", source="aion-reel-draft",
            )
            ledger = ContentNoveltyLedger(memory)
            report = ledger.assess({"topic_key": "How did ancient people first learn to make glass?"})
            self.assertTrue(report["eligible"])
            self.assertEqual(report["matches"], [])

    def test_a_creator_library_reel_still_blocks_a_real_repeat(self):
        # The exclusion is scoped to AION's own reflections; a Reel sourced
        # from the curated content library is a genuine topical video and
        # must still participate in duplicate detection.
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember(
                "published_reels",
                json.dumps({
                    "topic_key": "How an octopus changes colour",
                    "seed": {"kind": "creator-library"},
                }),
                memory_type="action", source="aion-creator-library",
            )
            ledger = ContentNoveltyLedger(memory)
            report = ledger.assess({"topic_key": "How an octopus changes colour"})
            self.assertFalse(report["eligible"])
            self.assertEqual(report["matches"][0]["category"], "published_reels")

    def test_a_reel_with_no_seed_field_still_blocks_a_real_repeat(self):
        # Older records predate the "seed" field entirely; missing metadata
        # must stay conservative (still compared), not silently excluded.
        with tempfile.TemporaryDirectory() as root:
            memory = MemoryEngine(root)
            memory.remember(
                "published_reels",
                json.dumps({"topic_key": "Yakhchal desert ice"}),
                memory_type="action", source="test",
            )
            ledger = ContentNoveltyLedger(memory)
            report = ledger.assess({"topic_key": "Yakhchal desert ice"})
            self.assertFalse(report["eligible"])


if __name__ == "__main__":
    unittest.main()

import unittest

from brain.costume_direction import CostumeDirection


class CostumeDirectionTests(unittest.TestCase):
    def test_cold_historical_scene_has_practical_costume_brief(self):
        brief = CostumeDirection.brief_for(
            {"title": "Ancient desert ice"},
            {"visual": "AION studies frost on a cold winter night."},
        )
        self.assertIn("practical", brief)
        self.assertIn("insulated", brief)
        self.assertIn("no logo", brief)

    def test_research_scene_gets_unobtrusive_prop(self):
        brief = CostumeDirection.brief_for(
            {"title": "Evidence"},
            {"visual": "AION compares a source map."},
        )
        self.assertIn("archival satchel", brief)

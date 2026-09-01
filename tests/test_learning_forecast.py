import tempfile
import unittest
from pathlib import Path

from brain.curiosity_constitution import CuriosityConstitution
from brain.learning_forecast import LearningForecastEngine
from brain.memory import MemoryEngine


class LearningForecastTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.memory = MemoryEngine(Path(self.temp.name) / "memory")
        self.engine = LearningForecastEngine(self.memory)
        self.question = {"id": "question-1", "statement": "How do humans learn language?", "importance": 3}
        self.assessment = CuriosityConstitution().assess(self.question["statement"])

    def tearDown(self):
        self.temp.cleanup()

    def test_forecast_is_modest_and_linked_to_question(self):
        forecast = self.engine.forecast_for(self.question, self.assessment)
        self.assertIn("Forecast confidence:", forecast["content"])
        self.assertIn("tentative estimate", forecast["content"])
        self.assertEqual(forecast["related"], ["question-1"])

    def test_forecast_is_not_duplicated_on_retry(self):
        first = self.engine.forecast_for(self.question, self.assessment)
        second = self.engine.forecast_for(self.question, self.assessment)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.memory.all("learning_forecasts")), 1)

    def test_review_is_recorded_once_and_is_not_a_belief(self):
        forecast = self.engine.forecast_for(self.question, self.assessment)
        review = self.engine.review(forecast, self.question, "informative", "A cited answer was saved.")
        self.assertEqual(review["type"], "forecast")
        self.assertIsNone(self.engine.review(forecast, self.question, "informative", "retry"))

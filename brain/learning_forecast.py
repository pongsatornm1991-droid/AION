"""A small, falsifiable forecast before AION spends a learning turn.

This is not a claim that AION can see the future.  It makes an expectation
explicit, then records whether the learning attempt actually produced useful,
cited understanding.  Over time this becomes evidence about AION's own taste
for worthwhile questions.
"""


class LearningForecastEngine:
    CATEGORY = "learning_forecasts"
    REVIEW_CATEGORY = "learning_forecast_reviews"

    def __init__(self, memory):
        self.memory = memory

    @staticmethod
    def _confidence(question, assessment):
        # Deliberately modest: relevance is a reason to investigate, not proof
        # that a useful source or answer exists.
        return min(0.75, round(0.40 + (assessment.relevance_score * 0.08) + (question.get("importance", 1) * 0.03), 2))

    def forecast_for(self, question, assessment, mode="continuity"):
        question_id = question.get("id")
        for entry in self.memory.all(self.CATEGORY):
            if question_id and question_id in entry.get("related", []):
                return entry

        domains = ", ".join(assessment.matched_domains) or "a new direction not yet connected to AION's past"
        confidence = self._confidence(question, assessment)
        content = "\n".join([
            "Learning Forecast Card",
            f"Question: {question.get('statement', '').strip()}",
            f"Learning mode: {mode}",
            f"Why explore now: It connects to {domains}.",
            "Expected value: This may add a cited perspective that can improve a future belief, goal, reflection, or creative direction.",
            f"Forecast confidence: {confidence:.2f} (a tentative estimate, not a fact).",
            "What would show this forecast was weak: the available source is irrelevant, insufficient, unsafe to summarize, or produces no useful connection.",
            "Review rule: Compare this forecast with the actual research result; do not treat the forecast as evidence for a belief.",
        ])
        return self.memory.remember(
            category=self.CATEGORY,
            content=content,
            memory_type="forecast",
            source="learning-forecast",
            importance=max(2, min(4, question.get("importance", 3))),
            tags=["learning-value", "forecast"],
            related=[item for item in (question_id,) if item],
        )

    def review(self, forecast, question, outcome, detail):
        forecast_id = forecast.get("id")
        if not forecast_id or not forecast.get("saved", True):
            return None
        if any(forecast_id in entry.get("related", []) for entry in self.memory.all(self.REVIEW_CATEGORY)):
            return None
        content = "\n".join([
            "Learning Forecast Review",
            f"Forecast: {forecast_id}",
            f"Question: {question.get('statement', '').strip()}",
            f"Outcome: {outcome}",
            f"Observed result: {detail}",
            "Calibration note: This records whether the attempt was informative, not whether the answer is universally true.",
        ])
        return self.memory.remember(
            category=self.REVIEW_CATEGORY,
            content=content,
            memory_type="forecast",
            source="learning-forecast-review",
            importance=3,
            tags=["learning-value", "forecast-review", outcome],
            related=[item for item in (forecast_id, question.get("id")) if item],
        )

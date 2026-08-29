from .experiments import ExperimentEngine


class MetacognitionEngine:
    """AION watching its own track record.

    Nothing here is judged by an AI provider or invented from a "gut
    feeling" — every number below is computed directly from what is
    already on disk: experiment outcomes for calibration, lessons for
    recurring failure themes, and MemoryEngine's own quality/stat
    primitives for memory health. If there isn't enough data to say
    something honestly, the report says so explicitly rather than
    guessing.

    Tool reliability (the fourth thing the roadmap names for this
    phase) is deliberately not implemented here: AION has no framework
    yet for calling external tools whose success/failure could be
    tracked — that arrives with the next phase, "Controlled tools and
    lifecycle". Reporting a reliability number for tools that do not
    exist would be exactly the kind of fabricated self-assessment the
    project's master directive forbids, so this class says as much
    instead of inventing a placeholder metric.
    """

    def __init__(self, memory, experiments=None):
        self.memory = memory
        self.experiments = experiments or ExperimentEngine(memory)

    # ---------------------------------------------------------
    # CALIBRATION
    # ---------------------------------------------------------

    def calibration_report(self, bucket_size=0.2, min_samples_per_bucket=3):
        """How well AION's stated prediction confidence matches how
        often predictions actually turned out to be right.

        Buckets observed experiments (predict -> observe, regardless
        of whether they were later concluded or abandoned) by their
        stated confidence, and compares each bucket's average
        confidence to its actual match rate. A bucket with fewer than
        min_samples_per_bucket observations is reported but flagged
        insufficient rather than treated as a real signal — a single
        lucky or unlucky guess should never look like a calibration
        finding.
        """

        if not 0 < bucket_size <= 1:
            raise ValueError("bucket_size must be between 0 (exclusive) and 1.")

        observed = self.experiments.observed_experiments()

        bucket_count = max(1, round(1 / bucket_size))
        buckets = [
            {
                "range": (
                    round(i * bucket_size, 2),
                    round(min(1.0, (i + 1) * bucket_size), 2),
                ),
                "confidences": [],
                "matches": [],
            }
            for i in range(bucket_count)
        ]

        for entry in observed:
            confidence = entry["confidence"]
            index = min(
                bucket_count - 1, int(confidence / bucket_size)
            )
            buckets[index]["confidences"].append(confidence)
            buckets[index]["matches"].append(1 if entry["matched"] else 0)

        report_buckets = []
        calibration_errors = []

        for bucket in buckets:
            count = len(bucket["confidences"])

            if count == 0:
                continue

            avg_confidence = sum(bucket["confidences"]) / count
            match_rate = sum(bucket["matches"]) / count
            sufficient = count >= min_samples_per_bucket

            entry_report = {
                "range": bucket["range"],
                "count": count,
                "average_confidence": round(avg_confidence, 3),
                "match_rate": round(match_rate, 3),
                "sufficient_data": sufficient,
            }

            if sufficient:
                error = avg_confidence - match_rate
                entry_report["calibration_gap"] = round(error, 3)
                entry_report["assessment"] = (
                    "overconfident" if error > 0.1
                    else "underconfident" if error < -0.1
                    else "well-calibrated"
                )
                calibration_errors.append((count, abs(error)))
            else:
                entry_report["calibration_gap"] = None
                entry_report["assessment"] = "insufficient_data"

            report_buckets.append(entry_report)

        if calibration_errors:
            total_weight = sum(weight for weight, _ in calibration_errors)
            overall_error = sum(
                weight * error for weight, error in calibration_errors
            ) / total_weight
            overall_error = round(overall_error, 3)
        else:
            overall_error = None

        return {
            "sample_size": len(observed),
            "buckets": report_buckets,
            "overall_calibration_error": overall_error,
        }

    # ---------------------------------------------------------
    # RECURRING ERRORS
    # ---------------------------------------------------------

    def recurring_error_report(self, min_occurrences=2, limit=10):
        """Groups every logged lesson by its source (e.g.
        "experiment-abandonment", "belief-retraction") and flags any
        source that recurs at least min_occurrences times. This is a
        literal count, not an AI-judged theme -- if two different
        kinds of failure happen to share a source label, this reports
        them as one group rather than guessing at a finer split.
        """

        lessons = self.memory.all("lessons")

        counts = {}

        for lesson in lessons:
            source = lesson.get("source") or "unknown"
            counts.setdefault(source, []).append(lesson["id"])

        grouped = [
            {"source": source, "count": len(ids), "example_ids": ids[:3]}
            for source, ids in counts.items()
        ]
        grouped.sort(key=lambda item: item["count"], reverse=True)

        recurring = [
            item for item in grouped if item["count"] >= min_occurrences
        ]

        return {
            "total_lessons": len(lessons),
            "sources": grouped[:limit],
            "recurring": recurring,
        }

    # ---------------------------------------------------------
    # MEMORY QUALITY
    # ---------------------------------------------------------

    def memory_quality_overview(self, categories=None, low_quality_threshold=2.5):
        """Aggregates MemoryEngine's own per-category quality_report()/
        stats() across every category on disk (or a caller-supplied
        list), and flags any category whose average quality sits
        below low_quality_threshold. Categories with fewer than 3
        entries are reported but never flagged -- a couple of thin
        entries should not look like a systemic quality problem.
        """

        if categories is None:
            categories = sorted(
                path.stem
                for path in self.memory.root.glob("*.md")
            )

        per_category = {}
        flagged = []
        total_entries = 0
        weighted_quality_sum = 0.0

        for category in categories:
            report = self.memory.quality_report(category)
            per_category[category] = report

            total_entries += report["total"]
            weighted_quality_sum += (
                report["average_quality"] * report["total"]
            )

            if report["total"] >= 3 and report["average_quality"] < low_quality_threshold:
                flagged.append(category)

        overall_average = (
            round(weighted_quality_sum / total_entries, 2)
            if total_entries else 0.0
        )

        return {
            "categories": per_category,
            "total_entries": total_entries,
            "overall_average_quality": overall_average,
            "flagged_low_quality": flagged,
        }

    # ---------------------------------------------------------
    # COMBINED REPORT
    # ---------------------------------------------------------

    def full_report(self):
        return {
            "calibration": self.calibration_report(),
            "recurring_errors": self.recurring_error_report(),
            "memory_quality": self.memory_quality_overview(),
            "tool_reliability": {
                "status": "not_applicable",
                "reason": (
                    "No external tool-execution framework exists yet "
                    "(see roadmap: Controlled tools and lifecycle). "
                    "Reporting a reliability figure now would be a "
                    "fabricated number rather than a measured one."
                ),
            },
        }

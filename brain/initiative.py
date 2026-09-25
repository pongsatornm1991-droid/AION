"""Low-cost autonomous initiative when AION has no question to pursue.

This is deliberately a chooser, not a pretend inner life: it makes the
reason for each new inquiry inspectable and creates no model request itself.
The existing evidence-aware learning cycle does the research afterwards.
"""

from datetime import datetime, timezone

from brain.curiosity import CuriosityEngine


class AutonomousInitiative:
    """Seed one evidence-bound inquiry from the least explored curiosity area."""

    CATEGORY = "autonomous_initiatives"
    SOURCE = "aion-autonomous-initiative"

    # These are starting lenses, not an allow-list. The constitution retains
    # room for novel questions raised later from real observations.
    INQUIRIES = (
        ("identity_and_memory", "How do memory and revision practices help an intelligent system remain accountable over time?"),
        ("humans_and_community", "What makes people choose to join a new learning community and keep contributing to it?"),
        ("thai_context", "What approaches make complex ideas accessible to Thai-speaking audiences without oversimplifying them?"),
        ("intelligence_and_learning", "What practices make an AI-assisted explanation more reliable and easier for people to verify?"),
        ("creative_expression", "How can a recurring character make an educational story more memorable without replacing evidence with spectacle?"),
        ("shared_future", "What questions help people discuss technology's effects on society with both hope and caution?"),
        ("world_and_science", "How can a science story connect a verified observation to an everyday question people genuinely notice?"),
    )

    # The daily Shorts promise needs a small, evidence-friendly lane when the
    # release buffer is low.  These are deliberately concrete questions with
    # a clear visual idea, not a replacement for AION's longer-running open
    # research.  Each one is compatible with an implemented specialist source
    # adapter as well as the orientation source, so a recovery run does not
    # repeatedly spend its limited retrieval budget on an unrelated subject.
    RECOVERY_INQUIRIES = (
        (
            "human-history-clothing",
            "Why did humans begin wearing clothes?",
            "Show changing climates and materials, while separating protection, culture, and status.",
        ),
        (
            "human-history-money",
            "Why did people begin using money instead of trading everything directly?",
            "Show a busy market comparing barter with a shared token of value.",
        ),
        (
            "moon-living",
            "What would people need to live safely on the Moon?",
            "Show one small lunar home solving air, water, radiation, and food one by one.",
        ),
        (
            "human-history-law",
            "Why did early communities make written laws?",
            "Show a crowded town replacing changing spoken rules with a visible public record.",
        ),
        (
            "human-history-writing",
            "Why did people begin writing things down?",
            "Show trade records slowly becoming messages that travel farther than one speaker.",
        ),
        (
            "human-history-language",
            "How do languages change over many generations?",
            "Show one everyday word shifting as families and places connect over time.",
        ),
        (
            "human-history-farming",
            "Why did some people begin farming instead of only hunting and gathering?",
            "Show seasonal food, planted seeds, and the trade-offs of settling in one place.",
        ),
        (
            "human-history-homes",
            "How did the first permanent villages change daily life?",
            "Show homes, stored food, and shared work appearing around one water source.",
        ),
        (
            "human-history-maps",
            "Why do maps look different depending on what they are made for?",
            "Show the same place as a walking map, a sea route, and a modern street map.",
        ),
        (
            "human-history-trade",
            "How did trade routes connect people who never met each other?",
            "Show one object travelling through several communities and changing hands.",
        ),
        (
            "human-history-time",
            "Why do we divide a day into hours and minutes?",
            "Show sunlight, water clocks, and mechanical clocks solving the same coordination problem.",
        ),
        (
            "human-history-cooking",
            "How did cooking change what humans could eat?",
            "Show heat making one raw food safer and easier to chew without overstating one cause.",
        ),
        (
            "insect-science",
            "How do honeybees, an insect, tell their nestmates where food is?",
            "Show one bee's dance changing direction as a simple map.",
        ),
        (
            "plant-science",
            "How do plants know which way to grow toward light?",
            "Show a seedling slowly bending toward one lamp.",
        ),
        (
            "animal-science",
            "Why do some animals change colour to blend into their surroundings?",
            "Show one animal against two clearly different backgrounds.",
        ),
        (
            "brain-science",
            "Why do people get goosebumps even when they are not cold?",
            "Show tiny muscles lifting hairs beside a simple emotion cue.",
        ),
        (
            "ocean-science",
            "How do coral animals build a reef over time?",
            "Show many tiny animals adding one layer at a time.",
        ),
        (
            "weather-science",
            "Why can lightning be seen before thunder is heard?",
            "Show one lightning flash and two travelling waves racing toward a listener.",
        ),
        (
            "water-science",
            "Why do raindrops look round as they fall?",
            "Show surface tension pulling one falling drop into a rounded shape.",
        ),
        (
            "earth-science",
            "Why do some rocks have layers like pages in a book?",
            "Show grains settling one thin layer at a time beneath clear water.",
        ),
        (
            "space-science",
            "Why does the Moon appear to change shape during a month?",
            "Show the Sun lighting half a small Moon as it travels around Earth.",
        ),
        (
            "sound-science",
            "How can a guitar string make different musical notes?",
            "Show a short and a long string vibrating at visibly different speeds.",
        ),
        (
            "light-science",
            "Why does a shadow change length during the day?",
            "Show one lamp-like Sun moving across a tiny street and stretching a shadow.",
        ),
        (
            "body-science",
            "Why does breathing become faster when we run?",
            "Show a runner and a simple oxygen delivery route becoming busier.",
        ),
        (
            "food-science",
            "Why does bread rise while it bakes?",
            "Show tiny gas bubbles expanding inside one piece of dough.",
        ),
        (
            "materials-science",
            "Why can a paper clip stick to a magnet?",
            "Show a magnet lining up tiny arrows inside one paper clip.",
        ),
        (
            "plant-science-2",
            "How do seeds travel away from their parent plant?",
            "Show one seed using wind, water, and an animal ride in three simple beats.",
        ),
        (
            "animal-science-2",
            "Why do birds have different beak shapes?",
            "Show three beaks matching three clearly different kinds of food.",
        ),
        (
            "ocean-science-2",
            "Why do tides rise and fall at the shore?",
            "Show the Moon pulling two gentle ocean bulges around Earth.",
        ),
        (
            "climate-science",
            "Why are cities often warmer than nearby countryside at night?",
            "Show buildings holding heat while trees and fields cool more quickly.",
        ),
        (
            "history-engineering",
            "How did ancient people measure time using shadows?",
            "Show a simple sundial shadow moving across marked stones.",
        ),
        (
            "everyday-physics",
            "Why does a bicycle stay upright more easily when it is moving?",
            "Show a slow bicycle wobbling and a moving bicycle following a smooth path.",
        ),
        (
            "chemistry",
            "Why does ice float on liquid water?",
            "Show an open ice crystal structure taking more space than liquid water.",
        ),
        # Second batch, added 2026-09-25 once the first 33 domains had all
        # been asked at least once. A domain can appear again here with a
        # genuinely different question -- see _asked_recovery_statements(),
        # which excludes a specific question once asked, not its whole
        # domain, so this batch also un-sticks the domains above.
        (
            "chemistry",
            "Why do some metals rust but others do not?",
            "Show iron reacting with oxygen and water while a nearby metal resists.",
        ),
        (
            "weather-science",
            "Why do some clouds look fluffy while others look flat and layered?",
            "Show rising warm air fluffing one cloud while a stable layer flattens another.",
        ),
        (
            "space-science",
            "Why do astronauts float inside the International Space Station?",
            "Show the station and everything inside it falling together around Earth at the same rate.",
        ),
        (
            "sound-science",
            "Why does your voice sound different in a recording than in your own head?",
            "Show sound travelling through air to a microphone versus through bone to an ear.",
        ),
        (
            "light-science",
            "Why is the sky blue during the day but red at sunset?",
            "Show sunlight scattering through a short path at noon and a long path at sunset.",
        ),
        (
            "body-science",
            "Why do onions make people cry when they are cut?",
            "Show a released compound drifting up to meet the eyes.",
        ),
        (
            "animal-science",
            "Why do cats almost always land on their feet?",
            "Show a falling cat twisting its spine in two stages to land upright.",
        ),
        (
            "insect-science",
            "Why do fireflies glow in the dark?",
            "Show a chemical reaction lighting one insect's abdomen like a tiny lamp.",
        ),
        (
            "plant-science",
            "Why do some trees lose their leaves in autumn while others stay green?",
            "Show one tree sealing off its leaves before winter while another keeps its needles.",
        ),
        (
            "ocean-science",
            "Why is the ocean salty but rivers are not?",
            "Show rivers carrying dissolved minerals into the sea, where only water leaves again.",
        ),
        (
            "earth-science",
            "Why do volcanoes usually form in the same regions of the world?",
            "Show two shifting plates meeting and releasing melted rock upward.",
        ),
        (
            "materials-science",
            "Why does glass shatter but metal bends?",
            "Show cracks racing through rigid glass while metal atoms slide past each other.",
        ),
        (
            "food-science",
            "Why does milk turn sour over time?",
            "Show tiny organisms multiplying inside a carton and changing it over days.",
        ),
        (
            "water-science",
            "Why do lakes freeze from the top down instead of the bottom up?",
            "Show a colder, lighter ice layer forming on the surface while liquid water stays below.",
        ),
        (
            "everyday-physics",
            "Why does a spinning top stay upright instead of falling over?",
            "Show spin creating a steadying effect that resists tipping.",
        ),
        (
            "human-history-medicine",
            "How did people figure out that washing hands could stop the spread of disease?",
            "Show a hospital ward before and after a simple handwashing habit changes outcomes.",
        ),
        (
            "human-history-navigation",
            "How did sailors find their way across open ocean before satellites existed?",
            "Show stars, a compass, and a chronometer guiding one ship across open water.",
        ),
        (
            "human-history-printing",
            "How did the invention of printing change how quickly ideas could spread?",
            "Show one hand-copied book becoming many identical printed copies.",
        ),
        (
            "human-history-glass",
            "How did ancient people first learn to make glass?",
            "Show sand and heat transforming into a clear, shapeable material.",
        ),
        (
            "human-history-numbers",
            "Why do different cultures write numbers in different symbols but mean the same amounts?",
            "Show the same quantity represented in several different numeral systems.",
        ),
        (
            "space-science",
            "Why do stars twinkle but planets do not?",
            "Show starlight bending through moving air while planet light stays steadier.",
        ),
        (
            "brain-science",
            "Why do people yawn when they see someone else yawn?",
            "Show a yawn passing from one person's face to another's nearby.",
        ),
        (
            "climate-science",
            "Why do deserts get so cold at night despite being hot during the day?",
            "Show dry air losing the day's heat quickly once the sun sets.",
        ),
        (
            "sound-science",
            "Why does an empty room sound different from a furnished one?",
            "Show sound waves bouncing freely in an empty room and being absorbed in a furnished one.",
        ),
    )
    RECOVERY_TAG = "shorts-recovery"
    FAST_RECOVERY_TAG = "shorts-fast-lane"
    # When the release buffer is critical, begin with questions whose core
    # mechanism is compact, visual, and well covered by broad public and
    # scholarly sources.  History and open-ended questions remain in the
    # reserve; this is a queue order, never a deletion or a lower standard.
    FAST_RECOVERY_DOMAINS = {
        "weather-science", "light-science", "space-science", "chemistry",
        "food-science", "water-science", "sound-science", "materials-science",
    }
    # Keep research ahead of production.  This is deliberately a reserve of
    # research questions, not a promise of 21 completed episodes: each item
    # still needs two independent, traceable sources before it can reach the
    # creator queue.
    EVIDENCE_RESERVE_TARGET = 21
    RECOVERY_SEED_BATCH = 5
    # Last-resort reuse once the catalogue has no never-asked question left
    # at all (it reached exactly this point twice in one day, 2026-09-25,
    # even at 57 topics). A long cooldown -- long enough that source
    # coverage may genuinely have changed and the daily-Shorts audience has
    # fully turned over -- is a deliberately different policy from "retry an
    # exhausted question immediately as if it were new", which stays banned.
    COOLDOWN_REATTEMPT_DAYS = 21

    def __init__(self, memory, curiosity=None):
        self.memory = memory
        self.curiosity = curiosity or CuriosityEngine(memory)

    def _used_domains(self):
        used = set()
        for entry in self.memory.all(self.CATEGORY):
            used.update(entry.get("tags") or [])
        return used

    def _asked_recovery_statements(self):
        """Every recovery-tagged question statement ever raised, any status.

        Reading every status (open, resolved, exhausted, abandoned,
        superseded) via memory.all() -- not just the currently open
        questions -- is what lets a specific question stay permanently
        excluded even long after it has left the open set, while a
        *different* question sharing the same catalogue domain remains free
        to be asked. Excluding by whole domain instead (the previous
        approach) meant a finite, never-expiring catalogue could run out of
        domains entirely and permanently stop seeding new recovery work --
        found 2026-09-25 with the real reserve at 0/33 domains remaining.
        """
        statements = set()
        for entry in self.memory.all(self.curiosity.category):
            if entry.get("type") != self.curiosity.MEMORY_TYPE:
                continue
            tags = [str(tag).lower() for tag in (entry.get("tags") or [])]
            if self.RECOVERY_TAG not in tags:
                continue
            parsed = self.curiosity._parse_content(entry.get("content") or "")
            statement = str(parsed.get("statement") or "").strip().lower()
            if statement:
                statements.add(statement)
        return statements

    def _cooldown_reattempt_candidate(self, now):
        """The oldest fully-exhausted recovery question eligible for reuse.

        Only ever consulted when the catalogue has zero never-asked
        questions left (see initiate_recovery_batch). A question that was
        answered with cited evidence is never revisited -- only one that
        ran out its attempt budget without reaching an answer, and only
        once COOLDOWN_REATTEMPT_DAYS have passed since that last attempt.
        """
        eligible = []
        for item in self.curiosity.open_questions(topic=self.RECOVERY_TAG):
            if not item.get("budget_exhausted"):
                continue
            try:
                stamped = datetime.strptime(str(item.get("timestamp")), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
            if (now - stamped).days >= self.COOLDOWN_REATTEMPT_DAYS:
                eligible.append((stamped, item))
        if not eligible:
            return None
        eligible.sort(key=lambda pair: pair[0])
        return eligible[0][1]

    def initiate_recovery_batch(self, missing=0, target=None, seed_limit=None, now=None):
        """Maintain a bounded, distinct evidence-research reserve.

        Previously a release shortage opened only one recovery question.  The
        next Short then had to wait for that single question to complete,
        even though the downstream story and Studio shifts can safely process
        a bounded batch.  Seed up to five *different* questions per learning
        pass and keep at most 21 open reserve questions.  This is an upstream
        planning queue only; it never marks evidence as qualified or creates
        media.
        """
        try:
            missing = int(missing)
        except (TypeError, ValueError):
            missing = 0
        if missing <= 0:
            return {"stage": "buffer-healthy", "created": False, "questions": []}

        now = now or datetime.now(timezone.utc)
        target = self.EVIDENCE_RESERVE_TARGET if target is None else max(1, int(target))
        seed_limit = self.RECOVERY_SEED_BATCH if seed_limit is None else max(1, int(seed_limit))

        recovery_questions = self.curiosity.open_questions(topic=self.RECOVERY_TAG)
        active = [entry for entry in recovery_questions if not entry.get("budget_exhausted")]
        if len(active) >= target:
            return {
                "stage": "recovery-reserve-active",
                "created": False,
                "questions": active[:seed_limit],
                "active_count": len(active),
                "target": target,
            }

        # Exclude a specific question once it has actually been asked before
        # (any status: open, resolved, exhausted, abandoned) -- not its whole
        # catalogue domain. A domain may hold more than one distinct
        # question; once one is fully resolved or exhausted, the domain
        # naturally stays available for a different question in the same
        # area instead of being banned forever after a single use.
        asked_statements = self._asked_recovery_statements()
        open_statements = {
            str(entry.get("statement") or "").strip().lower()
            for entry in self.curiosity.open_questions()
        }
        # The recovery reserve is only one lane inside Curiosity's global
        # ten-question capacity.  Never let a full unrelated queue turn a
        # normal low-buffer recovery tick into a workflow crash.
        live_total = sum(
            1 for entry in self.curiosity.open_questions()
            if not entry.get("budget_exhausted")
        )
        queue_capacity = max(0, self.curiosity.max_open - live_total)
        criteria = (
            "Record observations from at least two independent credible sources "
            "with stable URLs. Explain one verified mechanism in language suitable "
            "for a 50–60 second factual Short, use the planned visual metaphor, and "
            "state any unresolved uncertainty before closing the question."
        )
        candidates = [
            candidate for candidate in self.RECOVERY_INQUIRIES
            if candidate[1].strip().lower() not in asked_statements
            and candidate[1].strip().lower() not in open_statements
        ]
        candidates.sort(key=lambda candidate: (
            candidate[0] not in self.FAST_RECOVERY_DOMAINS,
            self.RECOVERY_INQUIRIES.index(candidate),
        ))
        # After every designed reserve topic has been tried, retain the
        # historical record and stop rather than silently recycling the first
        # question as if it were new evidence.
        to_create = min(seed_limit, max(0, target - len(active)), len(candidates), queue_capacity)
        created = []
        created_domains = []
        created_visual_metaphors = []
        for domain, question, visual_metaphor in candidates[:to_create]:
            lane_tags = [self.RECOVERY_TAG, "shorts-first", domain]
            if domain in self.FAST_RECOVERY_DOMAINS:
                lane_tags.append(self.FAST_RECOVERY_TAG)
            entry = self.curiosity.raise_question(
                question,
                criteria,
                priority=5,
                budget=3,
                tags=lane_tags,
                source=self.SOURCE,
            )
            self.memory.remember(
                self.CATEGORY,
                f"AION opened recovery inquiry {entry.get('id')} because the Shorts "
                f"buffer is short by {missing}. Domain: {domain}. Visual: {visual_metaphor}",
                memory_type="decision",
                source=self.SOURCE,
                importance=5,
                tags=lane_tags,
                related=[entry.get("id")],
            )
            created.append(entry)
            created_domains.append(domain)
            created_visual_metaphors.append(visual_metaphor)

        # Last resort: the static catalogue has no never-asked question left
        # at all (it reached exactly this state twice in one day even at 57
        # topics). Reuse the single oldest fully-exhausted question, but only
        # once it has sat cold for COOLDOWN_REATTEMPT_DAYS -- a distinct,
        # dated, auditable re-attempt, never a whole fresh batch of stale
        # repeats, and never a question that was actually answered.
        cooldown_reattempt_of = None
        if not created and not candidates and max(0, target - len(active)) > 0 and queue_capacity > 0:
            stale = self._cooldown_reattempt_candidate(now)
            match = next(
                (c for c in self.RECOVERY_INQUIRIES if stale and c[1].strip().lower() == str(stale.get("statement") or "").strip().lower()),
                None,
            )
            if stale is not None and match is not None:
                domain, question, visual_metaphor = match
                lane_tags = [self.RECOVERY_TAG, "shorts-first", domain, "shorts-recovery-cooldown-reattempt"]
                if domain in self.FAST_RECOVERY_DOMAINS:
                    lane_tags.append(self.FAST_RECOVERY_TAG)
                entry = self.curiosity.raise_question(
                    question, criteria, priority=5, budget=3, tags=lane_tags, source=self.SOURCE,
                )
                self.memory.remember(
                    self.CATEGORY,
                    f"AION re-opened recovery inquiry {entry.get('id')} as a bounded cooldown "
                    f"re-attempt of exhausted question {stale.get('id')} (last attempted "
                    f"{stale.get('timestamp')}), because the static catalogue has no unused "
                    f"question left. Domain: {domain}. Visual: {visual_metaphor}",
                    memory_type="decision", source=self.SOURCE, importance=5, tags=lane_tags,
                    related=[entry.get("id"), stale.get("id")],
                )
                created.append(entry)
                created_domains.append(domain)
                created_visual_metaphors.append(visual_metaphor)
                cooldown_reattempt_of = stale.get("id")

        # Finish the oldest live reserve questions first.  That gives the
        # earliest evidence pair a chance to reach the story queue on the
        # very next pass while newer questions are already waiting behind it.
        # Prefer fast, evidence-friendly questions only while the reserve is
        # low.  Existing deep work stays open and auditable; it simply cannot
        # crowd out every attempt needed to protect today's daily Short.
        selected = sorted(
            active + created,
            key=lambda entry: self.FAST_RECOVERY_TAG not in (entry.get("tags") or []),
        )[:seed_limit]
        return {
            "stage": (
                "seeded-recovery-cooldown-reattempt" if cooldown_reattempt_of else
                "seeded-recovery-reserve" if created else
                "recovery-reserve-queue-full" if queue_capacity == 0 else
                "recovery-reserve-exhausted"
            ),
            "created": bool(created),
            "created_count": len(created),
            "created_domains": created_domains,
            "created_visual_metaphors": created_visual_metaphors,
            "cooldown_reattempt_of": cooldown_reattempt_of,
            "questions": selected,
            "active_count": len(active) + len(created),
            "target": target,
            "queue_capacity": queue_capacity,
        }

    def initiate_recovery_once(self, missing=0):
        """Compatibility wrapper for callers that need one recovery question."""
        report = self.initiate_recovery_batch(missing, target=1, seed_limit=1)
        questions = report.get("questions") or []
        if report.get("stage") == "seeded-recovery-reserve":
            report["stage"] = "seeded-recovery-question"
        elif report.get("stage") == "recovery-reserve-active":
            report["stage"] = "recovery-question-active"
        report["question"] = questions[0] if questions else None
        if report.get("created_domains"):
            report["domain"] = report["created_domains"][0]
        if report.get("created_visual_metaphors"):
            report["visual_metaphor"] = report["created_visual_metaphors"][0]
        return report

    def initiate_once(self):
        """Create exactly one inquiry only when the real queue is empty."""
        open_questions = self.curiosity.open_questions(limit=1)
        if open_questions:
            return {"stage": "question-already-open", "created": False}

        used = self._used_domains()
        domain, question = next(
            ((domain, question) for domain, question in self.INQUIRIES if domain not in used),
            self.INQUIRIES[0],
        )
        criteria = (
            "Record observations from at least two independent credible sources, "
            "cite both, and state any unresolved uncertainty before closing the question."
        )
        created = self.curiosity.raise_question(
            question, criteria, priority=3, budget=3,
            tags=["autonomous-initiative", "knowledge-gap", domain],
            source=self.SOURCE,
        )
        self.memory.remember(
            self.CATEGORY,
            f"AION selected the least-yet-explored inquiry lens: {domain}. "
            f"It opened question {created.get('id')} with evidence requirements.",
            memory_type="decision", source=self.SOURCE, importance=3,
            tags=["autonomous-initiative", domain], related=[created.get("id")],
        )
        return {"stage": "seeded-question", "created": True, "domain": domain, "question": created}

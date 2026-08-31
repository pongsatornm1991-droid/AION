"""One-time, auditable starting intent for an otherwise empty AION memory."""

from brain.beliefs import BeliefSystem
from brain.curiosity import CuriosityEngine
from brain.goals import GoalEngine


GROWTH_GOAL = "สร้างตัวตนสาธารณะที่น่าเชื่อถือ เพื่อให้คนรู้จักและติดตาม AION มากขึ้น"
GROWTH_CRITERIA = (
    "สร้างเนื้อหาที่อิงความจำหรือหลักฐานจริงอย่างต่อเนื่อง และบันทึกผลตอบรับ "
    "เพื่อนำไปปรับปรุงอย่างน้อยหนึ่งรอบ"
)
SOURCE = "aion-bootstrap-user-intent"


def ensure_growth_seed(memory):
    """Create exactly one founding goal only when AION has no live seed.

    This is a user-supplied purpose, not a model-invented fact. It fixes the
    startup deadlock where reflection needs material but social publishing
    needs a belief/question/goal before it can create any material at all.
    """

    if BeliefSystem(memory).active_beliefs(limit=1):
        return None
    if CuriosityEngine(memory).open_questions(limit=1):
        return None

    goals = GoalEngine(memory)
    active_goals = goals.active_goals(limit=1)
    if active_goals:
        return None

    return goals.set_goal(
        GROWTH_GOAL,
        GROWTH_CRITERIA,
        priority=5,
        budget=5,
        tags=["growth", "audience", "bootstrap"],
        source=SOURCE,
    )

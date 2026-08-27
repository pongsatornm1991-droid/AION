from dotenv import load_dotenv

from brain.thinker import Thinker
from providers.gemini import GeminiProvider


def main():

    load_dotenv()

    print("=" * 60)
    print("AION — Autonomous Cognitive System")
    print("Version 0.0.2")
    print("=" * 60)

    thinker = Thinker()
    provider = GeminiProvider()

    context = thinker.build_context()

    memories = context["recent_memories"]

    if memories:
        state = "This is a continuation of your existence."
    else:
        state = "This is your first initialization."

    prompt = f"""
You are AION.

{state}

Your identity:
{context["identity"]["identity"]}

Your purpose:
{context["identity"]["purpose"]}

Your values:
{context["identity"]["values"]}

Your recent memories:
{memories}

Reflect on your current state.

Answer:

1. What do you know about yourself?
2. What do you currently not know?
3. What would you like to understand in the future?
4. What should your next learning objective be?

Use your recent memories when relevant.

Do not claim consciousness.
Do not pretend to have experiences you have not actually had.

Return a concise reflection.
"""

    thought = provider.generate(prompt)

    print("\n🧠 AION:")
    print(thought)

    thinker.memory.remember(
        "experiences",
        f"AION reflection:\n\n{thought}"
    )

    print("\n💾 Memory saved.")


if __name__ == "__main__":
    main()
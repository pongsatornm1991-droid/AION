"""Static, curated multilingual hashtag sets appended to AION's own
posts (Facebook message text, Instagram caption) -- never to a
comment reply, which stays Thai/English only (see
brain/comment_reply.py's own docstring for why).

Appended strictly AFTER the safety/style gates have already validated
the caption/message text, never fed back through them: these are
fixed, hand-picked, topical tags (AI/robot-persona, generic, carry no
claim about consciousness/feeling/superiority), so attaching them can
never bypass OutputEvaluator.claim_safety or the robotic-style check.
Deliberately a small, static, hand-picked list -- not translated by
an AI provider per post -- so tag spelling/quality never depends on a
live call and can never introduce an unreviewed claim in a language
the safety gates don't cover (see the module docstring note on
comment_reply.py's own, narrower, Thai/English-only scope for why
that distinction matters).

Language selection (2026-08-31, per the user's explicit request to
"reach the top 5 languages of that platform's viewers"): mapped from
the 5 largest Instagram audiences by real country-level user counts
(usefulsocialmedia.com's 2026 country ranking -- India, US, Brazil,
Indonesia, Japan, Turkey, Mexico, UK, Germany, Argentina, in that
order) to their dominant language, combining countries that share a
language: English (US + UK, and India's widely-used online link
language), Hindi (India -- the single largest national Instagram
audience by country), Portuguese (Brazil), Indonesian (Indonesia),
and Spanish (Mexico + Argentina combined exceeds Japan or Turkey
alone). Japanese and Turkish were the next runners-up if this set is
ever revisited. Thai is always included first since it is AION's own
home-language audience, not part of the "reach further" 5."""

HASHTAG_SETS = {
    "th": ["#เอไอ", "#ปัญญาประดิษฐ์"],
    "en": ["#AI", "#ArtificialIntelligence"],
    "hi": ["#एआई", "#कृत्रिमबुद्धिमत्ता"],
    "pt": ["#IA", "#InteligenciaArtificial"],
    "id": ["#AI", "#KecerdasanBuatan"],
    "es": ["#IA", "#InteligenciaArtificial"],
}

# Order matters only for the readability of the appended block --
# HASHTAG_SETS is the actual source of truth for which languages are
# included.
LANGUAGE_ORDER = ["th", "en", "hi", "pt", "id", "es"]


def build_hashtag_block():
    """One space-joined line of every configured language's tags.
    Duplicate tag strings are collapsed (Portuguese and Spanish
    currently share identical tag text) so the same tag is never
    repeated in one block."""

    seen = set()
    tags = []
    for lang in LANGUAGE_ORDER:
        for tag in HASHTAG_SETS.get(lang, []):
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
    return " ".join(tags)


def append_hashtags(text):
    """Append the hashtag block to already-gated text on its own new
    paragraph (blank line separated), matching how hashtags
    conventionally appear at the end of a Facebook/Instagram caption.
    Returns text unchanged (including falsy/empty text) if there is
    nothing to attach tags to -- never invents a caption out of an
    empty string."""

    if not text:
        return text
    return f"{text}\n\n{build_hashtag_block()}"

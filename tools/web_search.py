"""Free, no-API-key web research: Wikipedia's own public API.

Chosen deliberately over a paid search API (Google Custom Search,
Bing, SerpAPI) or Gemini's own "grounding with Google Search" tool --
checked directly against Google's current pricing docs (2026-08-30):
grounding has no free tier at all for gemini-3.x models (the
GEMINI_MODEL this project uses, see .env.example), only a paid,
metered add-on ($14/1,000 requests beyond a small shared monthly
pool). Wikipedia's API needs no key, no signup, and no cost at any
volume this project could plausibly reach -- matching the same
free-tier-first posture behind the earlier decision not to use paid
Gemini image generation (see the project audit).

Wikipedia's content is also curated rather than raw search-engine
results, which matters here specifically: brain/learning.py explicitly
frames a fetched extract as DATA to synthesize from, never as
instructions to follow (same defense comment_reply.py already applies
to Facebook comment text) -- and a curated encyclopedia entry is a
meaningfully lower-risk ingestion source than an arbitrary web page
someone could have written specifically to be found by a search query.

Trade-off, stated plainly: this only ever finds encyclopedic/
definitional answers, never current events, opinions, or anything
Wikipedia doesn't cover. That is an intentional scope limit for a
first version of "AION learns from outside sources," not an oversight.
"""

WIKIPEDIA_API_BASE = "https://en.wikipedia.org/w/api.php"


def search_wikipedia(query, limit=3):
    """Search Wikipedia for `query`. Returns a list of {"title": ...}
    dicts, best match first (empty list if nothing matches). Raises
    RuntimeError on failure -- never retries internally, matching this
    codebase's other tools (tools/facebook.py, tools/telegram.py)."""

    query = str(query).strip()

    if not query:
        raise ValueError("query cannot be empty.")

    import requests  # lazy: only needed when this actually runs

    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "format": "json",
    }

    response = requests.get(WIKIPEDIA_API_BASE, params=params, timeout=15)

    if response.status_code >= 400:
        raise RuntimeError(
            f"Wikipedia search error: HTTP {response.status_code}"
        )

    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError("Wikipedia search error: invalid JSON response.")

    results = payload.get("query", {}).get("search", [])

    return [{"title": r["title"]} for r in results if r.get("title")]


def get_wikipedia_summary(title):
    """Fetch the intro-section plain-text extract for the Wikipedia
    page titled `title` (following redirects). Returns
    {"title", "url", "extract"} -- "extract" is "" if the page exists
    but has no intro text, and everything is "" if the title does not
    resolve to any page. Raises RuntimeError on failure (network/HTTP
    error), never on a simple not-found -- a missing page is a normal,
    expected outcome for a mis-guessed search query, not a failure."""

    title = str(title).strip()

    if not title:
        raise ValueError("title cannot be empty.")

    import requests  # lazy: only needed when this actually runs

    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "redirects": 1,
        "titles": title,
        "format": "json",
    }

    response = requests.get(WIKIPEDIA_API_BASE, params=params, timeout=15)

    if response.status_code >= 400:
        raise RuntimeError(
            f"Wikipedia fetch error: HTTP {response.status_code}"
        )

    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError("Wikipedia fetch error: invalid JSON response.")

    pages = payload.get("query", {}).get("pages", {})

    if not pages:
        return {"title": title, "url": "", "extract": ""}

    page = next(iter(pages.values()))

    if "missing" in page:
        return {"title": title, "url": "", "extract": ""}

    resolved_title = page.get("title", title)
    extract = page.get("extract", "") or ""
    url = "https://en.wikipedia.org/wiki/" + resolved_title.replace(" ", "_")

    return {"title": resolved_title, "url": url, "extract": extract}

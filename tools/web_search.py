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

2026-09-04: added a second free, keyless source -- arXiv's own public
API -- to widen coverage specifically for the case Wikipedia's own
docstring above calls out as a known gap: open science/technology
questions that have no encyclopedia entry yet (a very recent paper, a
specialised subfield). This is the concrete first adapter for the
"official_primary_sources" tier already described (but left
unimplemented) in core/source_registry.json -- arXiv abstracts are
peer-review-track primary research, a meaningfully different and
higher-tier kind of evidence than an encyclopedia summary, registered
under its own "arxiv" entry rather than repurposing that broader
placeholder. brain/learning.py only ever tries this as a FALLBACK,
after Wikipedia's own search has already come back empty or
extract-less for a question -- Wikipedia stays the default/primary
source for everything it does cover. Same "data, not instructions"
framing applies: an arXiv abstract is exactly as untrusted as a
Wikipedia extract when handed to the drafting prompt.
"""

from xml.etree import ElementTree

WIKIPEDIA_API_BASE = "https://en.wikipedia.org/w/api.php"
ARXIV_API_BASE = "http://export.arxiv.org/api/query"
ARXIV_ATOM_NS = "{http://www.w3.org/2005/Atom}"

# Wikimedia's own User-Agent policy (meta.wikimedia.org/wiki/User-Agent_policy)
# requires API clients to identify themselves with a descriptive User-Agent
# that includes contact info; requests sent with the bare default
# `python-requests/x.x` agent (what `requests` sends with no header set) are
# blocked outright with HTTP 403 from many client IPs, including GitHub
# Actions runners. Found live 2026-09-03 after a real reflection-cycle run
# logged "Wikipedia search error: HTTP 403" for every query. Fixed by
# sending a compliant identifying header on every request.
USER_AGENT = (
    "AION/1.0 (https://github.com/pongsatornm1991-droid/AION; "
    "AION self-directed learning bot) python-requests"
)
REQUEST_HEADERS = {"User-Agent": USER_AGENT}


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

    response = requests.get(
        WIKIPEDIA_API_BASE, params=params, headers=REQUEST_HEADERS, timeout=15
    )

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

    response = requests.get(
        WIKIPEDIA_API_BASE, params=params, headers=REQUEST_HEADERS, timeout=15
    )

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


def _arxiv_id_from_entry_id(entry_id):
    """arXiv Atom <id> values look like
    "http://arxiv.org/abs/2301.12345v2" -- extract just "2301.12345"
    so it round-trips cleanly through get_arxiv_summary()."""

    tail = str(entry_id).rstrip("/").rsplit("/", 1)[-1]
    if "v" in tail:
        base, _, version = tail.rpartition("v")
        if version.isdigit():
            return base
    return tail


def search_arxiv(query, limit=3):
    """Search arXiv's own free, keyless public API for `query`. Returns
    a list of {"title": <arxiv_id>} dicts, best match first (empty
    list if nothing matches) -- note "title" here is the arXiv
    identifier (e.g. "2301.12345"), not the paper's real title, purely
    so this return value can be passed straight into
    get_arxiv_summary() exactly like search_wikipedia()'s "title" is
    passed into get_wikipedia_summary(). The paper's actual title only
    ever appears in get_arxiv_summary()'s return value. Raises
    RuntimeError on failure -- never retries internally, matching
    search_wikipedia()."""

    query = str(query).strip()

    if not query:
        raise ValueError("query cannot be empty.")

    import requests  # lazy: only needed when this actually runs

    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
    }

    response = requests.get(
        ARXIV_API_BASE, params=params, headers=REQUEST_HEADERS, timeout=15
    )

    if response.status_code >= 400:
        raise RuntimeError(f"arXiv search error: HTTP {response.status_code}")

    try:
        root = ElementTree.fromstring(response.content)
    except ElementTree.ParseError:
        raise RuntimeError("arXiv search error: invalid XML response.")

    results = []
    for entry in root.findall(f"{ARXIV_ATOM_NS}entry"):
        entry_id = entry.findtext(f"{ARXIV_ATOM_NS}id")
        if entry_id:
            results.append({"title": _arxiv_id_from_entry_id(entry_id)})

    return results


def get_arxiv_summary(arxiv_id):
    """Fetch one arXiv paper's title/abstract/URL by its arXiv id
    (e.g. "2301.12345", as returned by search_arxiv()). Returns
    {"title", "url", "extract"} -- "extract" is the paper's own
    abstract. Everything is "" if the id does not resolve to any
    paper. Raises RuntimeError on failure (network/HTTP/XML error),
    never on a simple not-found -- a missing id is a normal, expected
    outcome, not a failure, matching get_wikipedia_summary()."""

    arxiv_id = str(arxiv_id).strip()

    if not arxiv_id:
        raise ValueError("arxiv_id cannot be empty.")

    import requests  # lazy: only needed when this actually runs

    params = {"id_list": arxiv_id}

    response = requests.get(
        ARXIV_API_BASE, params=params, headers=REQUEST_HEADERS, timeout=15
    )

    if response.status_code >= 400:
        raise RuntimeError(f"arXiv fetch error: HTTP {response.status_code}")

    try:
        root = ElementTree.fromstring(response.content)
    except ElementTree.ParseError:
        raise RuntimeError("arXiv fetch error: invalid XML response.")

    entry = root.find(f"{ARXIV_ATOM_NS}entry")

    if entry is None:
        return {"title": "", "url": "", "extract": ""}

    title = " ".join((entry.findtext(f"{ARXIV_ATOM_NS}title") or "").split())
    summary = " ".join((entry.findtext(f"{ARXIV_ATOM_NS}summary") or "").split())
    raw_id = entry.findtext(f"{ARXIV_ATOM_NS}id") or ""
    url = raw_id.replace("http://arxiv.org", "https://arxiv.org")

    return {"title": title, "url": url, "extract": summary}

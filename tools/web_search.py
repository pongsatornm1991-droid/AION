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

import re
from xml.etree import ElementTree

WIKIPEDIA_API_BASE = "https://en.wikipedia.org/w/api.php"
ARXIV_API_BASE = "http://export.arxiv.org/api/query"
ARXIV_ATOM_NS = "{http://www.w3.org/2005/Atom}"
EUROPE_PMC_API_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
OPENALEX_API_BASE = "https://api.openalex.org"

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



# ============================================================
# HACKER NEWS PUBLIC HUMAN-PERSPECTIVE ADAPTER
# ============================================================

HACKER_NEWS_SEARCH_API_BASE = (
    "https://hn.algolia.com/api/v1/search"
)

HACKER_NEWS_ITEM_API_BASE = (
    "https://hn.algolia.com/api/v1/items"
)


def _plain_text_from_html(value):
    """Convert small public-comment HTML fragments to plain text.

    Source HTML remains untrusted data. This function only removes
    presentation markup before the text is passed to AION's grounded
    learning prompt.
    """

    from html import unescape
    from html.parser import HTMLParser


    class _TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []

        def handle_data(self, data):
            value = str(
                data or ""
            ).strip()

            if value:
                self.parts.append(
                    value
                )


    parser = _TextExtractor()

    try:
        parser.feed(
            str(value or "")
        )
    except Exception:
        return " ".join(
            unescape(
                str(value or "")
            ).split()
        )

    return " ".join(
        unescape(
            " ".join(
                parser.parts
            )
        ).split()
    )


def search_hacker_news(
    query,
    limit=10,
):
    """Search public Hacker News comments for human perspectives.

    Uses the public HN Search API powered by Algolia.

    Every result represents one traceable public comment. Search
    results are only discovery leads; the selected item is fetched
    again by ID before AION uses it as evidence.

    Returns dictionaries compatible with AION's existing search
    adapter convention:

        {
            "title": "<HN item id>",
            "url": "<traceable HN discussion URL>"
        }

    Raises RuntimeError on HTTP or malformed-response failures.
    """

    query = str(
        query
    ).strip()

    if not query:
        raise ValueError(
            "query cannot be empty."
        )

    try:
        limit = int(
            limit
        )
    except (
        TypeError,
        ValueError,
    ):
        raise ValueError(
            "limit must be an integer."
        )

    if limit < 1:
        raise ValueError(
            "limit must be at least 1."
        )

    import requests

    params = {
        "query": query,
        "tags": "comment",
        "hitsPerPage": min(
            limit,
            20,
        ),
    }

    response = requests.get(
        HACKER_NEWS_SEARCH_API_BASE,
        params=params,
        headers=REQUEST_HEADERS,
        timeout=15,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            "Hacker News search error: "
            f"HTTP {response.status_code}"
        )

    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError(
            "Hacker News search error: "
            "invalid JSON response."
        )

    hits = payload.get(
        "hits",
        []
    )

    results = []

    for hit in hits:
        item_id = str(
            hit.get(
                "objectID",
                "",
            )
        ).strip()

        if not item_id:
            continue

        comment_text = (
            _plain_text_from_html(
                hit.get(
                    "comment_text",
                    "",
                )
            )
        )

        # Extremely tiny comments are usually not useful enough to
        # count as a meaningful perspective.
        if len(comment_text) < 40:
            continue

        results.append({
            "title": item_id,
            "url": (
                "https://news.ycombinator.com/"
                f"item?id={item_id}"
            ),
        })

    return results


def get_hacker_news_perspective(
    item_id,
):
    """Fetch one traceable public Hacker News comment.

    A single comment is treated only as one person's public
    perspective. It is never represented as consensus or as factual
    authority.

    Returns the standard AION source structure:

        {
            "title": "...",
            "url": "...",
            "extract": "..."
        }
    """

    item_id = str(
        item_id
    ).strip()

    if not item_id:
        raise ValueError(
            "item_id cannot be empty."
        )

    import requests

    url = (
        f"{HACKER_NEWS_ITEM_API_BASE}/"
        f"{item_id}"
    )

    response = requests.get(
        url,
        headers=REQUEST_HEADERS,
        timeout=15,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            "Hacker News fetch error: "
            f"HTTP {response.status_code}"
        )

    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError(
            "Hacker News fetch error: "
            "invalid JSON response."
        )

    if not isinstance(
        payload,
        dict,
    ):
        return {
            "title": "",
            "url": "",
            "extract": "",
        }

    text = _plain_text_from_html(
        payload.get(
            "text",
            "",
        )
    )

    if not text:
        return {
            "title": "",
            "url": "",
            "extract": "",
        }

    author = str(
        payload.get(
            "author",
            "unknown user",
        )
    ).strip() or "unknown user"

    trace_url = (
        "https://news.ycombinator.com/"
        f"item?id={item_id}"
    )

    title = (
        "Hacker News perspective by "
        f"{author} (comment {item_id})"
    )

    extract = (
        "Public human perspective from "
        f"Hacker News user {author}: "
        f"{text}"
    )

    return {
        "title": title,
        "url": trace_url,
        "extract": extract,
    }


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


def search_europe_pmc_fulltext(query, limit=3):
    """Find open-access full papers in the official Europe PMC index."""
    query = str(query or "").strip()
    if not query:
        raise ValueError("query cannot be empty.")
    import requests
    response = requests.get(
        f"{EUROPE_PMC_API_BASE}/search",
        params={
            "query": f"({query}) AND OPEN_ACCESS:Y AND IN_EPMC:Y",
            "format": "json", "resultType": "core", "pageSize": limit,
        }, headers=REQUEST_HEADERS, timeout=20,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Europe PMC search error: HTTP {response.status_code}")
    try:
        results = response.json().get("resultList", {}).get("result", [])
    except (ValueError, AttributeError):
        raise RuntimeError("Europe PMC search error: invalid JSON response.")
    return [{"title": item.get("pmcid")} for item in results if item.get("pmcid")]


def get_europe_pmc_fulltext(pmcid, max_chars=24000):
    """Read the actual OA article XML, returning bounded plain text for synthesis."""
    pmcid = str(pmcid or "").strip()
    if not pmcid:
        raise ValueError("pmcid cannot be empty.")
    import requests
    response = requests.get(
        f"{EUROPE_PMC_API_BASE}/{pmcid}/fullTextXML",
        headers=REQUEST_HEADERS, timeout=30,
    )
    if response.status_code == 404:
        return {"title": "", "url": "", "extract": ""}
    if response.status_code >= 400:
        raise RuntimeError(f"Europe PMC full-text error: HTTP {response.status_code}")
    try:
        root = ElementTree.fromstring(response.content)
    except ElementTree.ParseError:
        raise RuntimeError("Europe PMC full-text error: invalid XML response.")
    title_node = root.find(".//article-title")
    title = " ".join("".join(title_node.itertext()).split()) if title_node is not None else pmcid
    body = root.find(".//body")
    text = " ".join(" ".join(body.itertext()).split()) if body is not None else ""
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "…"
    return {
        "title": title,
        "url": f"https://europepmc.org/articles/{pmcid}",
        "extract": text,
    }


# ============================================================
# OPENALEX SCHOLARLY DISCOVERY ADAPTER
# ============================================================

def _openalex_id(value):
    """Normalize an OpenAlex work URL or identifier to its work id."""
    value = str(value or "").strip().rstrip("/")
    return value.rsplit("/", 1)[-1]


def _openalex_abstract(inverted_index):
    """Rebuild OpenAlex's compact inverted-index abstract safely."""
    if not isinstance(inverted_index, dict):
        return ""
    words = []
    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        for position in positions:
            if isinstance(position, int) and position >= 0:
                words.append((position, str(word)))
    return " ".join(word for _, word in sorted(words))


def search_openalex(query, limit=3):
    """Search OpenAlex's free public scholarly-work index.

    This is a discovery adapter, not proof by itself: each result is fetched
    again and must still pass AION's relevance and independence gates. It is
    intentionally broad enough to provide a second scholarly domain for
    history, physical science, and everyday-science questions where arXiv or
    a life-science index would be the wrong match.
    """
    query = str(query or "").strip()
    if not query:
        raise ValueError("query cannot be empty.")
    import requests
    response = requests.get(
        f"{OPENALEX_API_BASE}/works",
        params={"search": query, "per-page": min(max(1, int(limit)), 10)},
        headers=REQUEST_HEADERS, timeout=20,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"OpenAlex search error: HTTP {response.status_code}")
    try:
        results = response.json().get("results", [])
    except (ValueError, AttributeError):
        raise RuntimeError("OpenAlex search error: invalid JSON response.")
    return [{"title": _openalex_id(item.get("id"))} for item in results if _openalex_id(item.get("id"))]


def get_openalex_work(work_id, max_chars=12000):
    """Fetch one OpenAlex work and return its title plus reconstructed abstract."""
    work_id = _openalex_id(work_id)
    if not work_id:
        raise ValueError("work_id cannot be empty.")
    import requests
    response = requests.get(
        f"{OPENALEX_API_BASE}/works/{work_id}", headers=REQUEST_HEADERS, timeout=20,
    )
    if response.status_code == 404:
        return {"title": "", "url": "", "extract": ""}
    if response.status_code >= 400:
        raise RuntimeError(f"OpenAlex fetch error: HTTP {response.status_code}")
    try:
        item = response.json()
    except ValueError:
        raise RuntimeError("OpenAlex fetch error: invalid JSON response.")
    if not isinstance(item, dict):
        return {"title": "", "url": "", "extract": ""}
    abstract = _openalex_abstract(item.get("abstract_inverted_index"))
    if len(abstract) > max_chars:
        abstract = abstract[:max_chars].rsplit(" ", 1)[0] + "…"
    location = item.get("primary_location") or {}
    url = str(location.get("landing_page_url") or item.get("doi") or item.get("id") or "").strip()
    return {
        "title": str(item.get("display_name") or work_id).strip(),
        "url": url,
        "extract": abstract,
    }


# ============================================================
# PRIMARY-SOURCE TEXT ADAPTER (Project Gutenberg via the Internet Archive)
# ============================================================
#
# core/source_registry.json declared an "official_primary_sources" tier
# (tier A: "Official documentation, public institutions, standards, and
# other primary evidence") since before this file existed, always with
# enabled: false and a note that "a source-specific retrieval adapter is
# required before this capability becomes usable." 2026-09-29: tried three
# real candidates before this one --
#   - loc.gov (Library of Congress): consistent HTTP 403 even with a
#     compliant identifying User-Agent (the same fix that unblocked
#     Wikipedia). Its bot protection appears to reject automated clients
#     outright; not viable keyless from a datacenter IP like a GitHub
#     Actions runner.
#   - Wikidata (same Wikimedia infrastructure Wikipedia already uses
#     successfully): search works, but an entity's data is a bag of
#     property-id/value claims (e.g. "P373", "P508"), not narrative
#     prose -- the wrong shape for this pipeline's "extract" contract
#     without a lot of additional label-resolution work.
#   - Wikisource (also Wikimedia): search works, but many proofread
#     documents transclude their text from separate Page: namespace
#     scans rather than holding it inline, so the same simple
#     prop=extracts call that works for Wikipedia often returns nothing.
# Project Gutenberg's full public-domain library, indexed and hosted by
# the Internet Archive (archive.org's own advancedsearch/metadata/download
# endpoints, confirmed live and keyless), is the one that actually works
# end to end: real primary and historical texts (speeches, treaties,
# classic historical and literary works), reliable JSON search, and a
# plain-text file per item. It is a public non-profit digital library, not
# a government agency -- less literally "official" than the registry
# entry's own name suggests, but still squarely "primary evidence", which
# its own role text already allows for.
INTERNET_ARCHIVE_API_BASE = "https://archive.org"
_GUTENBERG_START_RE = re.compile(
    r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*",
    re.IGNORECASE | re.DOTALL,
)
_GUTENBERG_END_RE = re.compile(
    r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK", re.IGNORECASE,
)


def _gutenberg_body(text):
    """Strip Project Gutenberg's license header/footer boilerplate.

    Handles the current convention ("*** START/END OF THE PROJECT
    GUTENBERG EBOOK ***"); an older digitization with no such marker
    falls back to skipping a fixed-size header-shaped prefix rather than
    handing the whole license text to the drafting prompt as if it were
    the work itself.
    """
    text = str(text or "")
    start = _GUTENBERG_START_RE.search(text)
    body = text[start.end():] if start else text[2500:]
    end = _GUTENBERG_END_RE.search(body)
    if end:
        body = body[:end.start()]
    return body.strip()


def search_primary_source_texts(query, limit=3):
    """Search Project Gutenberg's public-domain historical/primary texts,
    indexed via the Internet Archive's own search API."""
    query = str(query or "").strip()
    if not query:
        raise ValueError("query cannot be empty.")
    import requests
    response = requests.get(
        f"{INTERNET_ARCHIVE_API_BASE}/advancedsearch.php",
        params={
            "q": f"({query}) AND collection:gutenberg AND mediatype:texts",
            "fl[]": ["identifier", "title"],
            "rows": min(max(1, int(limit)), 10),
            "output": "json",
        },
        headers=REQUEST_HEADERS, timeout=20,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Internet Archive search error: HTTP {response.status_code}")
    try:
        docs = response.json().get("response", {}).get("docs", [])
    except (ValueError, AttributeError):
        raise RuntimeError("Internet Archive search error: invalid JSON response.")
    return [{"title": item.get("identifier")} for item in docs if item.get("identifier")]


def get_primary_source_text(identifier, max_chars=12000):
    """Fetch one Gutenberg item's plain-text file and return a bounded,
    boilerplate-stripped excerpt for synthesis."""
    identifier = str(identifier or "").strip()
    if not identifier:
        raise ValueError("identifier cannot be empty.")
    import requests
    meta_response = requests.get(
        f"{INTERNET_ARCHIVE_API_BASE}/metadata/{identifier}",
        headers=REQUEST_HEADERS, timeout=20,
    )
    if meta_response.status_code == 404:
        return {"title": "", "url": "", "extract": ""}
    if meta_response.status_code >= 400:
        raise RuntimeError(f"Internet Archive metadata error: HTTP {meta_response.status_code}")
    try:
        meta = meta_response.json()
    except (ValueError, AttributeError):
        raise RuntimeError("Internet Archive metadata error: invalid JSON response.")
    if not isinstance(meta, dict):
        return {"title": "", "url": "", "extract": ""}
    title = str((meta.get("metadata") or {}).get("title") or identifier).strip()
    url = f"https://archive.org/details/{identifier}"
    candidates = [
        entry.get("name") for entry in (meta.get("files") or [])
        if isinstance(entry, dict) and str(entry.get("name") or "").lower().endswith(".txt")
        and "_meta" not in str(entry.get("name") or "") and "_djvu" not in str(entry.get("name") or "")
    ]
    if not candidates:
        return {"title": title, "url": url, "extract": ""}
    # Prefer Gutenberg's own plain "pg<digits>.txt" convention over an
    # OCR-derived transcription of the same work.
    candidates.sort(key=lambda name: (0 if re.match(r"^pg\d+\.txt$", name, re.IGNORECASE) else 1, name))
    text_response = requests.get(
        f"{INTERNET_ARCHIVE_API_BASE}/download/{identifier}/{candidates[0]}",
        headers=REQUEST_HEADERS, timeout=30,
    )
    if text_response.status_code >= 400:
        # A dead file on one storage node is a missing result, not a
        # reason to fail the whole research shift.
        return {"title": title, "url": url, "extract": ""}
    body = _gutenberg_body(text_response.content.decode("utf-8", errors="replace"))
    if len(body) > max_chars:
        body = body[:max_chars].rsplit(" ", 1)[0] + "…"
    return {"title": title, "url": url, "extract": body}

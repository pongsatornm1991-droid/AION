"""Offline tests for tools/web_search.py.

Mocks requests.get entirely -- this suite must never make a live call
to Wikipedia's API, per the project's rule that unit tests never
depend on a live external service.
"""

import unittest
from unittest import mock

from tools.web_search import (
    WIKIPEDIA_API_BASE,
    ARXIV_API_BASE,
    REQUEST_HEADERS,
    search_wikipedia,
    get_wikipedia_summary,
    search_arxiv,
    get_arxiv_summary,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None, content=b""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.content = content

    def json(self):
        return self._payload


def _arxiv_feed(entries):
    """Build a minimal Atom feed body the way arXiv's real API does --
    just enough for search_arxiv()/get_arxiv_summary() to parse."""
    body = "".join(
        f"<entry><id>{entry['id']}</id><title>{entry.get('title', '')}</title>"
        f"<summary>{entry.get('summary', '')}</summary></entry>"
        for entry in entries
    )
    return f'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">{body}</feed>'.encode("utf-8")


class SearchWikipediaTests(unittest.TestCase):

    def test_empty_query_is_rejected_before_any_network_call(self):
        with mock.patch("requests.get") as mock_get:
            with self.assertRaises(ValueError):
                search_wikipedia("   ")
            mock_get.assert_not_called()

    def test_returns_titles_in_order(self):
        payload = {
            "query": {"search": [{"title": "Photosynthesis"}, {"title": "Chlorophyll"}]},
        }
        with mock.patch(
            "requests.get", return_value=FakeResponse(200, payload),
        ) as mock_get:
            results = search_wikipedia("photosynthesis")

        self.assertEqual(results, [{"title": "Photosynthesis"}, {"title": "Chlorophyll"}])
        called_url = mock_get.call_args.args[0]
        self.assertEqual(called_url, WIKIPEDIA_API_BASE)
        called_params = mock_get.call_args.kwargs["params"]
        self.assertEqual(called_params["srsearch"], "photosynthesis")

    def test_no_results_returns_empty_list(self):
        payload = {"query": {"search": []}}
        with mock.patch("requests.get", return_value=FakeResponse(200, payload)):
            results = search_wikipedia("asdkjfhqwoeiuraslkdjf")

        self.assertEqual(results, [])

    def test_sends_a_compliant_identifying_user_agent(self):
        # 2026-09-03: Wikimedia's User-Agent policy blocks the bare
        # `python-requests` default agent with HTTP 403 from many client
        # IPs (confirmed live from a real reflection-cycle run). Every
        # request must identify this project by name with contact info.
        payload = {"query": {"search": [{"title": "Photosynthesis"}]}}
        with mock.patch(
            "requests.get", return_value=FakeResponse(200, payload),
        ) as mock_get:
            search_wikipedia("photosynthesis")

        headers = mock_get.call_args.kwargs["headers"]
        self.assertEqual(headers, REQUEST_HEADERS)
        self.assertIn("AION", headers["User-Agent"])
        self.assertIn("github.com", headers["User-Agent"])

    def test_http_error_raises_runtime_error(self):
        with mock.patch("requests.get", return_value=FakeResponse(500, {})):
            with self.assertRaises(RuntimeError):
                search_wikipedia("photosynthesis")

    def test_never_retries_internally_on_failure(self):
        with mock.patch(
            "requests.get", return_value=FakeResponse(500, {}),
        ) as mock_get:
            with self.assertRaises(RuntimeError):
                search_wikipedia("photosynthesis")

        self.assertEqual(mock_get.call_count, 1)


class GetWikipediaSummaryTests(unittest.TestCase):

    def test_empty_title_is_rejected_before_any_network_call(self):
        with mock.patch("requests.get") as mock_get:
            with self.assertRaises(ValueError):
                get_wikipedia_summary("   ")
            mock_get.assert_not_called()

    def test_returns_title_url_and_extract(self):
        payload = {
            "query": {"pages": {
                "12345": {
                    "title": "Photosynthesis",
                    "extract": "Photosynthesis is a process used by plants.",
                },
            }},
        }
        with mock.patch(
            "requests.get", return_value=FakeResponse(200, payload),
        ) as mock_get:
            result = get_wikipedia_summary("photosynthesis")

        self.assertEqual(result["title"], "Photosynthesis")
        self.assertEqual(result["url"], "https://en.wikipedia.org/wiki/Photosynthesis")
        self.assertEqual(result["extract"], "Photosynthesis is a process used by plants.")
        called_params = mock_get.call_args.kwargs["params"]
        self.assertEqual(called_params["titles"], "photosynthesis")

    def test_missing_page_returns_empty_fields_not_an_error(self):
        payload = {
            "query": {"pages": {"-1": {"missing": "", "title": "Asdkjfhqwoeiu"}}},
        }
        with mock.patch("requests.get", return_value=FakeResponse(200, payload)):
            result = get_wikipedia_summary("Asdkjfhqwoeiu")

        self.assertEqual(result, {"title": "Asdkjfhqwoeiu", "url": "", "extract": ""})

    def test_page_with_no_extract_returns_empty_string(self):
        payload = {"query": {"pages": {"1": {"title": "Stub"}}}}
        with mock.patch("requests.get", return_value=FakeResponse(200, payload)):
            result = get_wikipedia_summary("Stub")

        self.assertEqual(result["extract"], "")

    def test_title_with_spaces_is_url_encoded_with_underscores(self):
        payload = {
            "query": {"pages": {"1": {"title": "Great Barrier Reef", "extract": "A reef."}}},
        }
        with mock.patch("requests.get", return_value=FakeResponse(200, payload)):
            result = get_wikipedia_summary("Great Barrier Reef")

        self.assertEqual(
            result["url"], "https://en.wikipedia.org/wiki/Great_Barrier_Reef",
        )

    def test_http_error_raises_runtime_error(self):
        with mock.patch("requests.get", return_value=FakeResponse(500, {})):
            with self.assertRaises(RuntimeError):
                get_wikipedia_summary("Photosynthesis")


class SearchArxivTests(unittest.TestCase):

    def test_empty_query_is_rejected_before_any_network_call(self):
        with mock.patch("requests.get") as mock_get:
            with self.assertRaises(ValueError):
                search_arxiv("   ")
            mock_get.assert_not_called()

    def test_returns_arxiv_ids_not_titles(self):
        # search_arxiv()'s "title" field is deliberately the arXiv id
        # (the fetch key), not the paper's real title -- see its own
        # docstring for why.
        feed = _arxiv_feed([
            {"id": "http://arxiv.org/abs/2301.12345v2", "title": "A Paper"},
            {"id": "http://arxiv.org/abs/1999.00001", "title": "Another Paper"},
        ])
        with mock.patch(
            "requests.get", return_value=FakeResponse(200, content=feed),
        ) as mock_get:
            results = search_arxiv("photosynthesis")

        self.assertEqual(results, [{"title": "2301.12345"}, {"title": "1999.00001"}])
        called_url = mock_get.call_args.args[0]
        self.assertEqual(called_url, ARXIV_API_BASE)
        called_params = mock_get.call_args.kwargs["params"]
        self.assertIn("photosynthesis", called_params["search_query"])

    def test_no_results_returns_empty_list(self):
        with mock.patch("requests.get", return_value=FakeResponse(200, content=_arxiv_feed([]))):
            results = search_arxiv("asdkjfhqwoeiuraslkdjf")

        self.assertEqual(results, [])

    def test_sends_a_compliant_identifying_user_agent(self):
        feed = _arxiv_feed([{"id": "http://arxiv.org/abs/2301.12345"}])
        with mock.patch(
            "requests.get", return_value=FakeResponse(200, content=feed),
        ) as mock_get:
            search_arxiv("photosynthesis")

        self.assertEqual(mock_get.call_args.kwargs["headers"], REQUEST_HEADERS)

    def test_http_error_raises_runtime_error(self):
        with mock.patch("requests.get", return_value=FakeResponse(500, content=b"")):
            with self.assertRaises(RuntimeError):
                search_arxiv("photosynthesis")

    def test_invalid_xml_raises_runtime_error(self):
        with mock.patch("requests.get", return_value=FakeResponse(200, content=b"not xml")):
            with self.assertRaises(RuntimeError):
                search_arxiv("photosynthesis")


class GetArxivSummaryTests(unittest.TestCase):

    def test_empty_id_is_rejected_before_any_network_call(self):
        with mock.patch("requests.get") as mock_get:
            with self.assertRaises(ValueError):
                get_arxiv_summary("   ")
            mock_get.assert_not_called()

    def test_returns_title_url_and_extract(self):
        feed = _arxiv_feed([{
            "id": "http://arxiv.org/abs/2301.12345v2",
            "title": "  A Paper\n  About Photosynthesis  ",
            "summary": "  This paper studies  \n  photosynthesis.  ",
        }])
        with mock.patch("requests.get", return_value=FakeResponse(200, content=feed)):
            result = get_arxiv_summary("2301.12345")

        self.assertEqual(result["title"], "A Paper About Photosynthesis")
        self.assertEqual(result["url"], "https://arxiv.org/abs/2301.12345v2")
        self.assertEqual(result["extract"], "This paper studies photosynthesis.")

    def test_missing_id_returns_empty_fields_not_an_error(self):
        with mock.patch("requests.get", return_value=FakeResponse(200, content=_arxiv_feed([]))):
            result = get_arxiv_summary("9999.99999")

        self.assertEqual(result, {"title": "", "url": "", "extract": ""})

    def test_http_error_raises_runtime_error(self):
        with mock.patch("requests.get", return_value=FakeResponse(500, content=b"")):
            with self.assertRaises(RuntimeError):
                get_arxiv_summary("2301.12345")


if __name__ == "__main__":
    unittest.main()

"""Offline tests for tools/web_search.py.

Mocks requests.get entirely -- this suite must never make a live call
to Wikipedia's API, per the project's rule that unit tests never
depend on a live external service.
"""

import unittest
from unittest import mock

from tools.web_search import (
    WIKIPEDIA_API_BASE,
    search_wikipedia,
    get_wikipedia_summary,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


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


if __name__ == "__main__":
    unittest.main()

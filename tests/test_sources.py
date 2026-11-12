import io
import json
import unittest
from urllib.parse import parse_qs, urlparse

from career_tracker.sources import fetch_source


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class SourceTests(unittest.TestCase):
    def test_amazon_fetch_uses_dubai_query(self):
        seen = []

        def opener(request, timeout=0):
            seen.append(request.full_url)
            return FakeResponse(b'{"jobs": []}')

        payload = fetch_source({"kind": "amazon", "query": "Dubai"}, opener=opener)
        self.assertEqual([], payload["jobs"])
        query = parse_qs(urlparse(seen[0]).query)
        self.assertEqual(["Dubai"], query["base_query"])

    def test_workday_fetch_paginates_and_enriches_live_details(self):
        calls = []
        search_page = {"total": 1, "jobPostings": [{"title": "Lead AI Forward Deployed Engineer", "externalPath": "/job/UAE-Dubai/role_JR1", "locationsText": "United Arab Emirates - Dubai"}]}
        detail = {"jobPostingInfo": {"jobReqId": "JR1", "jobDescription": "Hands-on customer delivery", "location": "Dubai", "canApply": True, "postedOn": "Posted 2 Days Ago", "startDate": "2026-11-10"}}

        def opener(request, timeout=0):
            calls.append((request.method, request.full_url))
            body = detail if request.method == "GET" else search_page
            return FakeResponse(json.dumps(body).encode())

        spec = {"kind": "workday", "host": "example.test", "tenant": "tenant", "site": "site", "search_text": "Dubai"}
        payload = fetch_source(spec, opener=opener)
        self.assertEqual("JR1", payload["jobPostings"][0]["jobReqId"])
        self.assertEqual("Hands-on customer delivery", payload["jobPostings"][0]["jobDescription"])
        self.assertEqual(["POST", "GET"], [call[0] for call in calls])

    def test_workday_excludes_detail_marked_not_applyable(self):
        search_page = {"total": 1, "jobPostings": [{"title": "Lead Engineer", "externalPath": "/job/UAE-Dubai/closed_JR2"}]}
        detail = {"jobPostingInfo": {"jobReqId": "JR2", "canApply": False}}
        responses = iter((search_page, detail))

        def opener(request, timeout=0):
            return FakeResponse(json.dumps(next(responses)).encode())

        payload = fetch_source({"kind": "workday", "host": "x", "tenant": "t", "site": "s"}, opener=opener)
        self.assertEqual([], payload["jobPostings"])


if __name__ == "__main__":
    unittest.main()

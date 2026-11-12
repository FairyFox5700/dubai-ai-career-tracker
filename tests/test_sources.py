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
    def test_smartrecruiters_fetch_paginates_and_enriches_details(self):
        calls = []
        page = {"totalFound": 1, "content": [{"id": "dh-1", "name": "Senior AI Architect"}]}
        detail = {"id": "dh-1", "name": "Senior AI Architect", "jobAd": {"sections": {"jobDescription": {"text": "AI delivery"}}}}

        def opener(request, timeout=0):
            calls.append(request.full_url)
            body = detail if request.full_url.endswith("/dh-1") else page
            return FakeResponse(json.dumps(body).encode())

        payload = fetch_source({"kind": "smartrecruiters", "company_id": "DeliveryHero"}, opener=opener)
        self.assertEqual("AI delivery", payload["content"][0]["jobAd"]["sections"]["jobDescription"]["text"])
        self.assertEqual(2, len(calls))

    def test_oracle_fetch_uses_site_and_uae_location_and_enriches_details(self):
        seen = []
        search = {"items": [{"requisitionList": [{"Id": "348579", "Title": "Senior Technical Architect - Healthcare", "PrimaryLocation": "United Arab Emirates"}]}]}
        detail = {"items": [{"Id": "348579", "ExternalDescriptionStr": "Customer cloud architecture", "PrimaryLocation": "United Arab Emirates"}]}

        def opener(request, timeout=0):
            seen.append(request.full_url)
            body = detail if "recruitingCEJobRequisitionDetails" in request.full_url else search
            return FakeResponse(json.dumps(body).encode())

        payload = fetch_source({
            "kind": "oracle",
            "base_url": "https://oracle.example/hcmRestApi/resources/latest/recruitingCEJobRequisitions",
            "details_url": "https://oracle.example/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails",
            "site": "CX_45001", "location": "United Arab Emirates",
        }, opener=opener)
        query = parse_qs(urlparse(seen[0]).query)
        self.assertIn("siteNumber=CX_45001", query["finder"][0])
        self.assertIn("location=United Arab Emirates", query["finder"][0])
        self.assertEqual(["requisitionList"], query["expand"])
        self.assertEqual("Customer cloud architecture", payload["items"][0]["ExternalDescriptionStr"])

    def test_linkedin_guest_search_is_bounded_delayed_and_fail_soft(self):
        calls, sleeps = [], []

        def opener(request, timeout=0):
            calls.append(request.full_url)
            if "keywords=AI+Architect" in request.full_url and "start=25" in request.full_url:
                raise OSError("rate limited")
            return FakeResponse(b'<div data-entity-urn="urn:li:jobPosting:1"></div>')

        html = fetch_source({
            "kind": "linkedin", "queries": ["AI Architect", "AI Engineer"],
            "location": "Dubai", "pages": 2, "delay_seconds": 0.25,
        }, opener=opener, sleeper=sleeps.append)
        self.assertEqual(4, len(calls))
        self.assertEqual([0.25, 0.25, 0.25], sleeps)
        self.assertIn("jobPosting:1", html)

    def test_linkedin_all_request_failures_raise_for_stale_preservation(self):
        def opener(request, timeout=0):
            raise OSError("blocked")

        with self.assertRaises(RuntimeError):
            fetch_source({"kind": "linkedin", "queries": ["AI Architect"], "pages": 1}, opener=opener, sleeper=lambda _: None)

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

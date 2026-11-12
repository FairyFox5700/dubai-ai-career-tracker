import json
import unittest
from pathlib import Path

from career_tracker.adapters import (
    normalize_amazon,
    normalize_ashby,
    normalize_greenhouse,
    normalize_lever,
    normalize_workday,
    sponsorship_evidence,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class AdapterTests(unittest.TestCase):
    def test_greenhouse_keeps_only_dubai_or_uae_remote_matching_seniority(self):
        jobs = normalize_greenhouse(load("greenhouse_jobs.json"), "Celonis")
        self.assertEqual(["Celonis:101", "Celonis:102"], [job["id"] for job in jobs])
        self.assertTrue(all(job["open_status"] == "verified_open" for job in jobs))
        self.assertTrue(all("<" not in job["description_excerpt"] for job in jobs))

    def test_workday_rejects_principal_even_when_title_also_says_lead(self):
        jobs = normalize_workday(load("workday_jobs.json"), "Salesforce", "https://example.test/jobs")
        self.assertEqual(["Salesforce:JR1"], [job["id"] for job in jobs])
        self.assertEqual("Dubai, United Arab Emirates", jobs[0]["location"])

    def test_ashby_and_lever_exclude_abu_dhabi(self):
        self.assertEqual([], normalize_ashby(load("ashby_jobs.json"), "OpenAI"))
        self.assertEqual([], normalize_lever(load("lever_jobs.json"), "Palantir"))

    def test_amazon_keeps_architect_and_rejects_sales_only(self):
        jobs = normalize_amazon(load("amazon_jobs.json"), "AWS")
        self.assertEqual(["AWS:A1"], [job["id"] for job in jobs])
        self.assertEqual("https://www.amazon.jobs/en/jobs/A1/test", jobs[0]["url"])

    def test_excludes_roles_that_explicitly_require_arabic_in_the_title(self):
        payload = {"jobPostings": [
            {
                "title": "Lead AI Forward Deployed Engineer, Arabic Speaking",
                "jobReqId": "JR-AR",
                "externalPath": "/job/UAE-Dubai/Lead-AI-FDE_JR-AR",
                "locationsText": "Dubai, United Arab Emirates",
                "jobDescription": "Customer-facing AI delivery.",
            },
            {
                "title": "Lead AI Forward Deployed Engineer",
                "jobReqId": "JR-EN",
                "externalPath": "/job/UAE-Dubai/Lead-AI-FDE_JR-EN",
                "locationsText": "Dubai, United Arab Emirates",
                "jobDescription": "Customer-facing AI delivery.",
            },
        ]}
        jobs = normalize_workday(payload, "Salesforce", "https://example.test/jobs")
        self.assertEqual(["Salesforce:JR-EN"], [job["id"] for job in jobs])

    def test_sponsorship_taxonomy_distinguishes_all_required_states(self):
        cases = {
            "We provide visa sponsorship for this role.": "explicit_sponsorship",
            "Relocation and immigration support are available.": "relocation_support",
            "The employer will arrange the UAE employment visa and work permit.": "employer_work_permit",
            "Visa sponsorship is not available.": "explicit_no_sponsorship",
            "Join our customer engineering team.": "unknown",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(expected, sponsorship_evidence(text)[0])


if __name__ == "__main__":
    unittest.main()

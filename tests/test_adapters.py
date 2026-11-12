import json
import unittest
from pathlib import Path

from career_tracker.adapters import (
    normalize_amazon,
    normalize_ashby,
    normalize_greenhouse,
    normalize_lever,
    normalize_linkedin,
    normalize_oracle,
    normalize_smartrecruiters,
    normalize_workday,
    sponsorship_evidence,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class AdapterTests(unittest.TestCase):
    def test_smartrecruiters_normalizes_only_safe_relevant_dubai_roles(self):
        jobs = normalize_smartrecruiters(load("smartrecruiters_jobs.json"), "talabat")
        self.assertEqual(["talabat:dh-1"], [job["id"] for job in jobs])
        self.assertEqual("verified_open", jobs[0]["open_status"])
        self.assertEqual("official", jobs[0]["source_status"])

    def test_oracle_normalizes_public_recruiting_cloud_records(self):
        jobs = normalize_oracle(load("oracle_jobs.json"), "Oracle")
        self.assertEqual(["Oracle:300001"], [job["id"] for job in jobs])
        self.assertEqual("technical_architecture", jobs[0]["role_family"])

    def test_linkedin_html_is_discovery_only_and_never_official(self):
        html = (FIXTURES / "linkedin_jobs.html").read_text(encoding="utf-8")
        jobs = normalize_linkedin(html)
        self.assertEqual(["LinkedIn:111"], [job["id"] for job in jobs])
        self.assertEqual("Property Finder", jobs[0]["company"])
        self.assertEqual("linkedin_discovery", jobs[0]["source_status"])
        self.assertEqual("linkedin_active", jobs[0]["open_status"])
        self.assertEqual("linkedin_guest", jobs[0]["source"])

    def test_linkedin_discovery_requires_ai_signal_and_excludes_language_market_roles(self):
        def card(job_id, title):
            return f'''<li data-entity-urn="urn:li:jobPosting:{job_id}">
              <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/{job_id}"></a>
              <h3 class="base-search-card__title">{title}</h3>
              <h4 class="base-search-card__subtitle">Example</h4>
              <span class="job-search-card__location">Dubai</span>
            </li>'''

        html = "".join((
            card(201, "Senior AI Architect"),
            card(202, "Senior Solutions Architect"),
            card(203, "GenAI Solution Architect - Turkey Market (Turkish Speaking)"),
        ))
        jobs = normalize_linkedin(html)
        self.assertEqual(["LinkedIn:201"], [job["id"] for job in jobs])

    def test_greenhouse_keeps_only_dubai_or_uae_remote_matching_seniority(self):
        jobs = normalize_greenhouse(load("greenhouse_jobs.json"), "Celonis")
        self.assertEqual(["Celonis:101", "Celonis:102"], [job["id"] for job in jobs])
        self.assertTrue(all(job["open_status"] == "verified_open" for job in jobs))
        self.assertTrue(all("<" not in job["description_excerpt"] for job in jobs))

    def test_greenhouse_uses_explicit_job_posting_location_metadata(self):
        payload = {"jobs": [{
            "id": 88, "title": "Senior Customer Engineer, Saudi Arabia",
            "location": {"name": "Hybrid"},
            "metadata": [{"name": "Job Posting Location", "value": ["Dubai, UAE"]}],
            "absolute_url": "https://boards.greenhouse.io/example/jobs/88",
            "content": "Hands-on customer AI and cloud architecture delivery.",
        }]}
        jobs = normalize_greenhouse(payload, "Cloudflare")
        self.assertEqual(["Cloudflare:88"], [job["id"] for job in jobs])
        self.assertEqual("Dubai, United Arab Emirates", jobs[0]["location"])

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

    def test_adapter_classifies_from_full_description_before_truncating_public_record(self):
        long_description = "Hands-on customer delivery of RAG, MCP, agents, and evaluations. " + ("deep evidence " * 100)
        payload = {"jobPostings": [{
            "title": "Senior Forward Deployed AI Engineer", "jobReqId": "FDE1",
            "externalPath": "/job/UAE-Dubai/FDE_FDE1", "locationsText": "Dubai",
            "jobDescription": long_description,
        }, {
            "title": "Senior AI Architect", "jobReqId": "AR1",
            "externalPath": "/job/UAE-Dubai/AI_AR1", "locationsText": "Dubai",
            "jobDescription": "Build AI solutions. Native Arabic is mandatory for customer delivery.",
        }]}
        jobs = normalize_workday(payload, "Example", "https://example.test/jobs")
        self.assertEqual(["Example:FDE1"], [job["id"] for job in jobs])
        self.assertEqual("forward_deployed_ai", jobs[0]["role_family"])
        self.assertIn("customer-delivery", jobs[0]["match_reason"])
        self.assertLessEqual(len(jobs[0]["description_excerpt"]), 700)
        self.assertNotIn("description", jobs[0])

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

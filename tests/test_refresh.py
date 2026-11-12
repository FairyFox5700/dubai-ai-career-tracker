import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from career_tracker.export import jobs_csv
from career_tracker.refresh import refresh


class RefreshTests(unittest.TestCase):
    def test_active_counts_include_linkedin_discovery_and_dedupe_prefers_official_alias(self):
        official = {"jobs": [{
            "id": 1, "title": "Senior Solutions Architect - AI",
            "location": {"name": "Remote — United Arab Emirates"},
            "absolute_url": "https://aws.example/jobs/1", "content": "Customer AI delivery.",
        }]}
        linkedin = """
        <div data-entity-urn="urn:li:jobPosting:10"><a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/10"></a><h3 class="base-search-card__title">Senior Solutions Architect - AI</h3><h4 class="base-search-card__subtitle">Amazon Web Services (AWS)</h4><span class="job-search-card__location">Dubai, United Arab Emirates</span></div>
        <div data-entity-urn="urn:li:jobPosting:11"><a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/11"></a><h3 class="base-search-card__title">Senior Forward Deployed AI Engineer</h3><h4 class="base-search-card__subtitle">Property Finder</h4><span class="job-search-card__location">Dubai, United Arab Emirates</span></div>
        """

        def fetcher(spec):
            return linkedin if spec["kind"] == "linkedin" else official

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = refresh(
                [{"company": "AWS", "kind": "greenhouse"}, {"company": "LinkedIn discovery", "kind": "linkedin"}],
                root / "jobs.json", root / "report.json", root / "jobs.csv",
                fetcher=fetcher, now="2026-11-12T12:00:00Z",
            )
            data = json.loads((root / "jobs.json").read_text(encoding="utf-8"))
            self.assertEqual(2, report["live_job_count"])
            self.assertEqual(1, report["official_count"])
            self.assertEqual(1, report["linkedin_count"])
            self.assertEqual(2, len(data["jobs"]))
            aws = next(job for job in data["jobs"] if job["company"] == "AWS")
            self.assertEqual("official", aws["source_status"])

    def test_source_failure_preserves_previous_as_stale_but_not_live(self):
        previous = {
            "jobs": [{
                "id": "Anthropic:old", "source_id": "old", "company": "Anthropic",
                "title": "Senior Solutions Architect", "location": "Dubai, United Arab Emirates",
                "url": "https://example.test/old", "open_status": "verified_open", "stale": False,
            }]
        }
        good_payload = {"jobs": [{
            "id": 1, "title": "Lead Applied Value Engineer", "location": {"name": "Dubai, United Arab Emirates"},
            "absolute_url": "https://example.test/1", "updated_at": "2026-11-10T00:00:00Z", "content": "Hands-on customer architecture",
        }]}

        def fetcher(spec):
            if spec["company"] == "Anthropic":
                raise RuntimeError("blocked")
            return good_payload

        with tempfile.TemporaryDirectory() as temp:
            data_path = Path(temp) / "jobs.json"
            report_path = Path(temp) / "report.json"
            csv_path = Path(temp) / "jobs.csv"
            data_path.write_text(json.dumps(previous), encoding="utf-8")
            report = refresh(
                [{"company": "Celonis", "kind": "greenhouse"}, {"company": "Anthropic", "kind": "greenhouse"}],
                data_path, report_path, csv_path, fetcher=fetcher, now="2026-11-12T12:00:00Z",
            )
            data = json.loads(data_path.read_text(encoding="utf-8"))
            self.assertEqual(1, report["live_job_count"])
            self.assertEqual(["Celonis"], report["sources_ok"])
            self.assertEqual(["Anthropic"], report["sources_failed"])
            stale = next(job for job in data["jobs"] if job["company"] == "Anthropic")
            self.assertTrue(stale["stale"])
            self.assertEqual("source_error", stale["open_status"])
            self.assertTrue(csv_path.exists())

    def test_csv_has_raw_and_clickable_links_with_formula_protection(self):
        text = jobs_csv([{
            "company": "=Evil", "title": "+Injected", "location": "Dubai",
            "url": "https://example.test/job?id=1", "score": {"total": 88},
            "sponsorship_status": "employer_work_permit", "open_status": "verified_open",
            "compensation": None,
        }])
        rows = list(csv.DictReader(io.StringIO(text)))
        self.assertEqual("'=Evil", rows[0]["company"])
        self.assertEqual("'+Injected", rows[0]["title"])
        self.assertEqual("https://example.test/job?id=1", rows[0]["raw_application_url"])
        self.assertEqual('=HYPERLINK("https://example.test/job?id=1","Open official posting")', rows[0]["application_link_clickable"])

    def test_csv_does_not_create_formula_for_non_http_link(self):
        text = jobs_csv([{"company": "X", "title": "Senior Architect", "location": "Dubai", "url": "javascript:alert(1)", "score": {"total": 1}}])
        row = next(csv.DictReader(io.StringIO(text)))
        self.assertEqual("", row["application_link_clickable"])

    def test_csv_labels_linkedin_discovery_without_calling_it_official(self):
        text = jobs_csv([{
            "company": "Example", "title": "Senior AI Architect", "location": "Dubai",
            "url": "https://www.linkedin.com/jobs/view/1", "source_status": "linkedin_discovery",
            "open_status": "linkedin_active", "score": {"total": 70},
        }])
        row = next(csv.DictReader(io.StringIO(text)))
        self.assertEqual("linkedin_discovery", row["source_status"])
        self.assertIn("Open LinkedIn discovery", row["application_link_clickable"])
        self.assertNotIn("official", row["application_link_clickable"].casefold())


if __name__ == "__main__":
    unittest.main()

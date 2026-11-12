import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class GeneratedArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "data" / "jobs.json").read_text(encoding="utf-8"))
        cls.report = json.loads((ROOT / "data" / "refresh-report.json").read_text(encoding="utf-8"))

    def test_live_count_matches_active_non_stale_rows(self):
        live = [job for job in self.data["jobs"] if job["open_status"] in ("verified_open", "linkedin_active") and not job["stale"]]
        self.assertEqual(len(live), self.data["live_job_count"])
        self.assertEqual(len(live), self.report["live_job_count"])
        self.assertEqual(sum(job["source_status"] == "official" for job in live), self.data["official_count"])
        self.assertEqual(sum(job["source_status"] == "linkedin_discovery" for job in live), self.data["linkedin_count"])
        self.assertEqual(self.data["official_count"], self.report["official_count"])
        self.assertEqual(self.data["linkedin_count"], self.report["linkedin_count"])

    def test_generated_roles_obey_location_and_seniority_contract(self):
        for job in self.data["jobs"]:
            with self.subTest(job=job["id"]):
                location = job["location"].casefold()
                title = job["title"].casefold()
                self.assertTrue("dubai" in location or ("remote" in location and "united arab emirates" in location))
                self.assertNotIn("abu dhabi", location)
                self.assertFalse(any(term in title for term in ("staff", "principal")))
                self.assertTrue(job["url"].startswith("https://"))
                self.assertIn(job["source_status"], ("official", "linkedin_discovery", "source_error"))
                self.assertNotIn("_scoring_evidence", job)
                self.assertIn("role_family", job)
                self.assertIn("match_reason", job)

    def test_csv_round_trips_every_generated_role_and_raw_url(self):
        with (ROOT / "data" / "jobs.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(self.data["jobs"]), len(rows))
        self.assertEqual({job["url"] for job in self.data["jobs"]}, {row["raw_application_url"] for row in rows})
        self.assertTrue(all(row["application_link_clickable"].startswith('=HYPERLINK("https://') for row in rows))


if __name__ == "__main__":
    unittest.main()

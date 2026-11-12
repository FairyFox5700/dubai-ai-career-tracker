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

    def test_live_count_matches_verified_non_stale_rows(self):
        live = [job for job in self.data["jobs"] if job["open_status"] == "verified_open" and not job["stale"]]
        self.assertEqual(len(live), self.data["live_job_count"])
        self.assertEqual(len(live), self.report["live_job_count"])

    def test_generated_roles_obey_location_and_seniority_contract(self):
        for job in self.data["jobs"]:
            with self.subTest(job=job["id"]):
                location = job["location"].casefold()
                title = job["title"].casefold()
                self.assertTrue("dubai" in location or ("remote" in location and "united arab emirates" in location))
                self.assertNotIn("abu dhabi", location)
                self.assertFalse(any(term in title for term in ("staff", "principal")))
                self.assertTrue(job["url"].startswith("https://"))

    def test_csv_round_trips_every_generated_role_and_raw_url(self):
        with (ROOT / "data" / "jobs.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(self.data["jobs"]), len(rows))
        self.assertEqual({job["url"] for job in self.data["jobs"]}, {row["raw_application_url"] for row in rows})
        self.assertTrue(all(row["application_link_clickable"].startswith('=HYPERLINK("https://') for row in rows))


if __name__ == "__main__":
    unittest.main()

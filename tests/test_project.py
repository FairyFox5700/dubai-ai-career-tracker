import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class ProjectTests(unittest.TestCase):
    def test_config_encodes_dubai_seniority_and_sources(self):
        config = json.loads((ROOT / "config" / "tracker.json").read_text(encoding="utf-8"))
        self.assertEqual("Dubai", config["location"]["hard_filter"])
        self.assertTrue(config["location"]["allow_uae_remote_if_dubai_supported"])
        self.assertEqual(["senior", "sr.", "snr", "lead", "architect"], config["seniority"]["allowed"])
        self.assertEqual(["staff", "principal"], config["seniority"]["excluded"])
        companies = {source["company"] for source in config["sources"]}
        self.assertTrue({"Databricks", "OpenAI", "Anthropic", "Celonis", "Palantir", "AWS", "Salesforce", "NVIDIA"}.issubset(companies))
        self.assertTrue({"Visa", "Cloudflare", "Elastic", "talabat", "Oracle", "LinkedIn discovery"}.issubset(companies))
        linkedin = next(source for source in config["sources"] if source["kind"] == "linkedin")
        self.assertEqual(6, len(linkedin["queries"]))
        self.assertLessEqual(linkedin["pages"], 3)
        self.assertGreater(linkedin["delay_seconds"], 0)

    def test_site_contains_complete_visible_sponsorship_strategy(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        for phrase in (
            "UAE employment visa workflow", "Target-employer tiers", "Position the CV",
            "Recruiter questions", "Red flags", "Application cadence", "Networking",
            "Offer due diligence", "Visit-visa work", "Candidate-paid visa costs",
        ):
            self.assertIn(phrase, html)
        self.assertIn("u.ae", html)
        self.assertIn("mohre.gov.ae", html)

    def test_site_supports_local_statuses_filters_breakdown_health_and_csv(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")
        for value in ("new", "reviewing", "shortlisted", "applied", "interviewing", "offer", "rejected", "withdrawn", "archived"):
            self.assertIn(value, html)
        for token in ("localStorage", "score.breakdown", "refresh-report.json", "HYPERLINK", "raw_application_url", "download"):
            self.assertIn(token, js)
        self.assertIn('id="source-filter"', html)
        self.assertIn("active roles", html)
        self.assertIn("linkedin_discovery", js)
        self.assertIn("LinkedIn discovery", js)
        self.assertNotIn("Verified Dubai roles", html)

    def test_workflows_use_required_action_majors_and_no_secrets(self):
        combined = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / ".github" / "workflows").glob("*.yml"))
        for action in ("actions/checkout@v7", "actions/setup-python@v7", "actions/configure-pages@v6", "actions/upload-pages-artifact@v5", "actions/deploy-pages@v5"):
            self.assertIn(action, combined)
        self.assertNotRegex(combined, re.compile(r"secrets\.", re.I))
        self.assertIn("cron:", combined)

    def test_scheduled_refresh_deploys_the_generated_data(self):
        workflow = (ROOT / ".github" / "workflows" / "refresh.yml").read_text(encoding="utf-8")
        self.assertIn("pages: write", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("actions/configure-pages@v6", workflow)
        self.assertIn("actions/upload-pages-artifact@v5", workflow)
        self.assertIn("actions/deploy-pages@v5", workflow)
        self.assertLess(workflow.index("python scripts/refresh.py"), workflow.index("actions/upload-pages-artifact@v5"))

    def test_required_repository_files_exist(self):
        for relative in (
            "LICENSE", "README.md", ".nojekyll", "scripts/refresh.py", "data/jobs.json",
            "data/refresh-report.json", "data/jobs.csv", ".github/workflows/ci.yml",
            ".github/workflows/refresh.yml", ".github/workflows/pages.yml",
        ):
            self.assertTrue((ROOT / relative).exists(), relative)


if __name__ == "__main__":
    unittest.main()

import unittest

from career_tracker.scoring import score_job


class ScoringTests(unittest.TestCase):
    def test_score_is_transparent_and_bounded(self):
        job = {
            "title": "Lead AI Forward Deployed Engineer",
            "description_excerpt": "Hands-on architecture and production deployment of agents, RAG, Azure, Python and Kubernetes with enterprise customers.",
            "sponsorship_status": "explicit_sponsorship",
            "posted_at": "2026-11-10",
            "source_status": "official",
        }
        score = score_job(job, now="2026-11-12T12:00:00Z")
        self.assertEqual(score["total"], sum(score["breakdown"].values()))
        self.assertLessEqual(score["total"], 100)
        self.assertEqual(10, score["breakdown"]["sponsorship"])
        self.assertGreaterEqual(score["breakdown"]["profile_skills"], 10)

    def test_explicit_no_sponsorship_is_flagged_and_scores_zero(self):
        score = score_job({"title": "Senior Solutions Architect", "description_excerpt": "Customer architecture", "sponsorship_status": "explicit_no_sponsorship"})
        self.assertEqual(0, score["breakdown"]["sponsorship"])
        self.assertTrue(score["sponsorship_red_flag"])

    def test_unknown_compensation_is_not_invented_or_penalized(self):
        score = score_job({"title": "Senior Solutions Architect", "description_excerpt": "Hands-on customer delivery", "compensation": None})
        self.assertEqual("not_posted", score["compensation_status"])
        self.assertNotIn("compensation", score["breakdown"])


if __name__ == "__main__":
    unittest.main()

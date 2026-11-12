import unittest

from career_tracker.adapters import classify_role


class RelevanceTests(unittest.TestCase):
    def test_forward_deployed_ai_role_uses_full_description_and_emits_reason(self):
        result = classify_role(
            "Senior Forward Deployed AI Engineer",
            "Build RAG and MCP agents, evaluations, and production AI systems with enterprise customers.",
        )
        self.assertTrue(result["eligible"])
        self.assertEqual("forward_deployed_ai", result["role_family"])
        self.assertIn("customer-delivery", result["match_reason"])

    def test_explicit_safe_role_families_are_accepted(self):
        cases = {
            "Senior AI/ML Platform Engineer": "ai_platform_engineering",
            "Lead AI Systems Engineer": "ai_systems_engineering",
            "Senior AI Implementation Engineer": "ai_implementation",
            "Senior Integration Architect - GenAI": "ai_integration_architecture",
            "Lead Professional Services Consultant, AI": "professional_services",
            "Senior Customer Success Architect - AI": "customer_success",
            "Senior Solutions Consultant - Generative AI": "solutions_consulting",
            "Senior Technical Architect – Healthcare": "technical_architecture",
            "Senior Technical Account Manager": "technical_account_management",
            "Enterprise AI Architect": "ai_architecture",
        }
        for title, family in cases.items():
            with self.subTest(title=title):
                result = classify_role(title, "Hands-on customer delivery of AI platforms and cloud solutions.")
                self.assertTrue(result["eligible"])
                self.assertEqual(family, result["role_family"])

    def test_generic_engineering_and_consulting_titles_stay_excluded(self):
        for title in (
            "Senior Software Engineer", "Senior Cloud Engineer", "Senior Data Engineer",
            "Senior ML Engineer", "Senior Consultant", "Senior Enterprise Architect",
        ):
            with self.subTest(title=title):
                self.assertFalse(classify_role(title, "General platform work.")["eligible"])

    def test_people_managers_are_excluded_but_exact_senior_tam_is_allowed(self):
        self.assertFalse(classify_role("Senior Manager, Data Science", "Lead a team of 12 managers and hiring.")["eligible"])
        self.assertFalse(classify_role("Sr Manager Consumer Platforms", "People management and performance reviews.")["eligible"])
        self.assertTrue(classify_role("Senior Technical Account Manager", "Hands-on cloud architecture for customers.")["eligible"])

    def test_arabic_required_in_full_description_is_rejected_but_preferred_is_allowed(self):
        required = classify_role("Senior AI Architect", "Arabic fluency is mandatory for this role.")
        preferred = classify_role("Senior AI Architect", "Arabic is preferred or nice to have.")
        self.assertFalse(required["eligible"])
        self.assertTrue(preferred["eligible"])

    def test_staff_and_principal_are_always_excluded(self):
        self.assertFalse(classify_role("Staff Lead AI Architect", "Agentic AI delivery.")["eligible"])
        self.assertFalse(classify_role("Principal Senior Customer Engineer", "Customer AI delivery.")["eligible"])
        self.assertFalse(classify_role("Solution Architect Graduate - 2027 Start", "Customer architecture.")["eligible"])
        self.assertFalse(classify_role("AI Architect Apprenticeship", "Hands-on AI delivery.")["eligible"])

    def test_explicit_ai_data_scientist_requires_hands_on_production_evidence(self):
        strong = classify_role(
            "Sr. Data Scientist (AI & ML)",
            "Design, build, ship, deploy, evaluate and monitor production generative AI and LLM systems using Python.",
        )
        weak = classify_role("Sr. Data Scientist", "Reporting and business analysis.")
        self.assertTrue(strong["eligible"])
        self.assertEqual("production_ai_data_science", strong["role_family"])
        self.assertFalse(weak["eligible"])


if __name__ == "__main__":
    unittest.main()

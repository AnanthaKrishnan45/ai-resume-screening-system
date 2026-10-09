import unittest
from src.screener import score_resume

class ScreeningTests(unittest.TestCase):
    def test_requires_python_and_ai(self):
        result = score_resume("JavaScript React developer building web interfaces")
        self.assertFalse(result["eligible"])
        self.assertTrue(result["rejection_reasons"])

    def test_python_and_rag_is_eligible(self):
        result = score_resume("Python developer. Projects: Built a RAG pipeline with embeddings and vector search.")
        self.assertTrue(result["eligible"])
        self.assertIsNotNone(result["score_breakdown"])
        self.assertEqual(sum(result["score_breakdown"].values()), result["total_score"])

    def test_missing_github_does_not_affect_eligibility(self):
        result = score_resume("Python implementation of a LangChain agent project.")
        self.assertTrue(result["eligible"])
        self.assertEqual(result["score_breakdown"]["github"], 0)

if __name__ == "__main__":
    unittest.main()

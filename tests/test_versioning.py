import unittest

from syncdocs_mcp.rag.versioning import collection_name, parents_collection_name, sanitize_identifier


class VersioningTests(unittest.TestCase):
    def test_sanitize_identifier(self):
        self.assertEqual(sanitize_identifier("LangChain v0.3"), "langchain_v0_3")

    def test_collection_name(self):
        self.assertEqual(collection_name("LangChain", "0.3"), "langchain_0_3")

    def test_parents_collection_name(self):
        self.assertEqual(parents_collection_name("stripe_latest"), "stripe_latest_parents")


if __name__ == "__main__":
    unittest.main()

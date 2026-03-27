import unittest

from syncdocs_mcp.rag.hybrid import _rrf_merge


class DummyDoc:
    def __init__(self, chunk_id: str, page_content: str):
        self.metadata = {"chunk_id": chunk_id}
        self.page_content = page_content


class HybridTests(unittest.TestCase):
    def test_rrf_merge_deduplicates_and_orders(self):
        docs_a = [DummyDoc("a", "alpha"), DummyDoc("b", "beta")]
        docs_b = [DummyDoc("b", "beta"), DummyDoc("c", "gamma")]
        merged = _rrf_merge(docs_a, docs_b, k=3)
        self.assertEqual([doc.metadata["chunk_id"] for doc in merged], ["b", "a", "c"])


if __name__ == "__main__":
    unittest.main()

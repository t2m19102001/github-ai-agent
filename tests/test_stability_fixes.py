from src.utils.embeddings import text_to_embedding
from src.agents.image_agent import ImageAgent


def test_text_to_embedding_is_deterministic():
    emb1 = text_to_embedding("same-query", 16)
    emb2 = text_to_embedding("same-query", 16)
    assert len(emb1) == 16
    assert emb1 == emb2


def test_text_to_embedding_differs_for_different_text():
    emb1 = text_to_embedding("query-a", 16)
    emb2 = text_to_embedding("query-b", 16)
    assert emb1 != emb2


def test_image_rag_query_embedding_is_deterministic():
    class RecordingStore:
        def __init__(self):
            self.calls = []

        def search(self, embedding, k):
            self.calls.append(list(embedding))
            return []

    store = RecordingStore()
    agent = ImageAgent(rag_store=store)
    agent._search_related_docs("same OCR text")
    agent._search_related_docs("same OCR text")
    assert store.calls[0] == store.calls[1]

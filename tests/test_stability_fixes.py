from src.utils.embeddings import text_to_embedding


def test_text_to_embedding_is_deterministic():
    emb1 = text_to_embedding("same-query", 16)
    emb2 = text_to_embedding("same-query", 16)
    assert len(emb1) == 16
    assert emb1 == emb2


def test_text_to_embedding_differs_for_different_text():
    emb1 = text_to_embedding("query-a", 16)
    emb2 = text_to_embedding("query-b", 16)
    assert emb1 != emb2

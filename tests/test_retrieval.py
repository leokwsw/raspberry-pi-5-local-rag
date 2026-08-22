from app.retrieval import bm25_search, needs_query_rewrite, reciprocal_rank_fusion, tokenize


def test_tokenize_supports_english_and_chinese_bigrams():
    tokens = tokenize("NeRF 體積渲染")

    assert "nerf" in tokens
    assert "體積" in tokens


def test_bm25_prioritizes_exact_terms():
    documents = [
        {"id": "semantic", "text": "A neural representation of a scene."},
        {"id": "exact", "text": "The MLP predicts color and density."},
    ]

    assert bm25_search("MLP density", documents, 2)[0]["id"] == "exact"


def test_rrf_combines_dense_and_lexical_rankings():
    dense = [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}]
    lexical = [{"id": "b", "text": "B"}, {"id": "c", "text": "C"}]

    assert reciprocal_rank_fusion([dense, lexical], 3)[0]["id"] == "b"


def test_only_contextual_followups_need_rewrite():
    assert needs_query_rewrite("What are its benefits?", True)
    assert not needs_query_rewrite("What does the MLP predict?", True)
    assert not needs_query_rewrite("What are its benefits?", False)

from app.graph import KnowledgeGraphStore


def test_entity_keys_are_stable_and_case_insensitive():
    assert KnowledgeGraphStore._entity_key(" Raspberry Pi 5 ") == KnowledgeGraphStore._entity_key("raspberry pi 5")


def test_edge_keys_include_document_identity():
    first = KnowledgeGraphStore._edge_key("doc-1", "Pi", "uses", "ARM64")
    duplicate = KnowledgeGraphStore._edge_key("doc-1", "pi", "USES", "arm64")
    other_document = KnowledgeGraphStore._edge_key("doc-2", "Pi", "uses", "ARM64")

    assert first == duplicate
    assert first != other_document


def test_clean_only_accepts_bounded_strings():
    assert KnowledgeGraphStore._clean(" value ") == "value"
    assert KnowledgeGraphStore._clean(None) == ""
    assert len(KnowledgeGraphStore._clean("x" * 300)) == 200

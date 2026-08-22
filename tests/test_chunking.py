from app.main import split_text


def test_short_paragraphs_are_grouped():
    assert split_text("第一段。\n\n第二段。", 200, 20) == ["第一段。\n\n第二段。"]


def test_long_content_is_split_with_limit():
    chunks = split_text("字" * 500, 200, 20)
    assert len(chunks) == 3
    assert all(len(item) <= 200 for item in chunks)

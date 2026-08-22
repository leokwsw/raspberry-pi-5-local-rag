import pytest
from fastapi import HTTPException

from app.text_files import decode_text


def test_decodes_utf8_plain_text():
    assert decode_text("notes.md", "繁體中文".encode()) == "繁體中文"


def test_rejects_binary_content():
    with pytest.raises(HTTPException) as exc:
        decode_text("bad.txt", b"hello\x00world")
    assert exc.value.status_code == 415


def test_rejects_non_text_extension():
    with pytest.raises(HTTPException) as exc:
        decode_text("manual.pdf", b"plain-looking")
    assert exc.value.status_code == 415

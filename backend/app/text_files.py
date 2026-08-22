import csv
import io
from pathlib import Path

from fastapi import HTTPException
from striprtf.striprtf import rtf_to_text

ALLOWED_EXTENSIONS = {
    ".txt", ".rtf", ".csv", ".tsv", ".log", ".md", ".markdown",
    ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".conf", ".cfg", ".sql", ".sh", ".css", ".html",
    ".xml", ".env",
}


def decode_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, f"不支援的檔案類型：{suffix or '無副檔名'}")
    if b"\x00" in content[:8192]:
        raise HTTPException(415, "偵測到二進位內容，只接受純文字檔案")
    for encoding in ("utf-8-sig", "utf-8", "big5", "gb18030"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise HTTPException(415, "無法辨識文字編碼")
    if suffix == ".rtf":
        text = rtf_to_text(text)
    elif suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        rows = csv.reader(io.StringIO(text), delimiter=delimiter)
        text = "\n".join(" | ".join(cell.strip() for cell in row) for row in rows)
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise HTTPException(422, "檔案沒有可建立索引的文字")
    return text

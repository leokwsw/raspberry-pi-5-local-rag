#!/usr/bin/env python3
import argparse
import mimetypes
from pathlib import Path

import httpx

ALLOWED = {".txt", ".rtf", ".csv", ".tsv", ".log", ".md", ".markdown", ".py", ".js", ".jsx", ".ts", ".tsx", ".json",
           ".yaml", ".yml", ".toml", ".ini", ".conf", ".cfg", ".sql", ".sh", ".css", ".html", ".xml", ".env"}


def main() -> None:
    parser = argparse.ArgumentParser(description="將資料夾內的純文字檔案匯入本機 RAG")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--api", default="http://localhost:8080")
    parser.add_argument("--recursive", action="store_true")
    args = parser.parse_args()
    if not args.folder.is_dir():
        parser.error(f"不是資料夾：{args.folder}")
    paths = args.folder.rglob("*") if args.recursive else args.folder.glob("*")
    files = sorted(path for path in paths if path.is_file() and path.suffix.lower() in ALLOWED)
    with httpx.Client(timeout=600) as client:
        for index, path in enumerate(files, start=1):
            mime = mimetypes.guess_type(path.name)[0] or "text/plain"
            with path.open("rb") as handle:
                response = client.post(f"{args.api.rstrip('/')}/api/documents",
                                       files={"file": (path.name, handle, mime)})
            response.raise_for_status()
            data = response.json()
            print(f"[{index}/{len(files)}] {path.name}: {data['chunk_count']} chunks")


if __name__ == "__main__":
    main()

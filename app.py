import argparse
import textwrap
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DB_PATH = "./chroma_db"
DEFAULT_COLLECTION = "pi_local_rag"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
DEFAULT_GENERATION_MODEL = "llama3.2:3b"


KNOWLEDGE_BASE = [
    {
        "id": "pi5-memory",
        "title": "Raspberry Pi 5 memory",
        "text": "Raspberry Pi 5 有 4GB、8GB 與 16GB RAM 版本。16GB 版本更適合小型本機 AI、RAG、資料庫與多服務同時運行。",
    },
    {
        "id": "pi5-cpu",
        "title": "Raspberry Pi 5 processor",
        "text": "Raspberry Pi 5 使用 Broadcom BCM2712 四核心 Arm Cortex-A76 處理器，時脈 2.4GHz，CPU 效能明顯高於 Raspberry Pi 4。",
    },
    {
        "id": "pi5-cooling",
        "title": "Raspberry Pi 5 cooling",
        "text": "在 Raspberry Pi 5 上長時間執行 LLM 或 embedding 任務時，建議使用主動散熱器，避免過熱造成降頻與回應變慢。",
    },
    {
        "id": "ollama-purpose",
        "title": "Ollama local models",
        "text": "Ollama 可以在本機執行大型語言模型與 embedding 模型，適合邊緣裝置、離線開發與不想把資料送到雲端的 RAG 應用。",
    },
    {
        "id": "chromadb-purpose",
        "title": "ChromaDB vector store",
        "text": "ChromaDB 是輕量向量資料庫，可在本機儲存文件 embedding，並依照語意相似度找回和問題最相關的內容。",
    },
    {
        "id": "rag-flow",
        "title": "RAG workflow",
        "text": "RAG 流程通常包含文件切分、embedding、向量儲存、檢索相關內容、把 context 放進 prompt，最後由 LLM 根據資料回答。",
    },
    {
        "id": "model-choice",
        "title": "Model choice on Raspberry Pi 5",
        "text": "Raspberry Pi 5 16GB 可優先使用 llama3.2:3b 這類較小模型取得較快回應；較大的 7B 或 8B 模型可能可用，但延遲會增加。",
    },
]


@dataclass
class RetrievedSource:
    title: str
    text: str
    distance: float | None


class LocalRAG:
    def __init__(
        self,
        db_path: str,
        collection_name: str,
        embed_model: str,
        generation_model: str,
        top_k: int,
    ) -> None:
        self.db_path = db_path
        self.collection_name = collection_name
        self.embed_model = embed_model
        self.generation_model = generation_model
        self.top_k = max(1, top_k)
        try:
            import chromadb
            import ollama
        except ModuleNotFoundError as exc:
            raise RuntimeError("Missing Python dependency. Run: pip install -r requirements.txt") from exc

        self.ollama = ollama
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def prepare(self, rebuild: bool = False) -> None:
        if rebuild:
            try:
                self.client.delete_collection(name=self.collection_name)
            except Exception:
                pass
            self.collection = self.client.get_or_create_collection(name=self.collection_name)

        if self.collection.count() == 0:
            self.index_documents(KNOWLEDGE_BASE)

    def index_documents(self, documents: list[dict[str, str]]) -> None:
        ids: list[str] = []
        texts: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, str]] = []

        for item in documents:
            text = item["text"]
            ids.append(item["id"])
            texts.append(text)
            embeddings.append(self.embed(text))
            metadatas.append({"title": item["title"]})

        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def embed(self, text: str) -> list[float]:
        response = self.ollama.embeddings(model=self.embed_model, prompt=text)
        return response["embedding"]

    def retrieve(self, question: str) -> list[RetrievedSource]:
        if self.collection.count() == 0:
            raise RuntimeError("ChromaDB collection is empty. Run with --rebuild to recreate the index.")

        query_embedding = self.embed(question)
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(self.top_k, self.collection.count()),
        )

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        sources: list[RetrievedSource] = []
        for index, document in enumerate(documents):
            metadata = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
            distance = distances[index] if index < len(distances) else None
            sources.append(
                RetrievedSource(
                    title=metadata.get("title", "Untitled source"),
                    text=document,
                    distance=distance,
                )
            )
        return sources

    def build_prompt(self, question: str, sources: list[RetrievedSource]) -> str:
        context = "\n\n".join(
            f"[{index}] {source.title}\n{source.text}" for index, source in enumerate(sources, start=1)
        )
        return textwrap.dedent(
            f"""
            你是一個在 Raspberry Pi 5 16GB 本機執行的 RAG AI 助手。
            請只根據下方 context 回答問題；如果 context 不足，請明確說「目前資料不足」。
            回答請使用繁體中文，並保持簡潔。

            context:
            {context}

            question:
            {question}

            answer:
            """
        ).strip()

    def answer(self, question: str) -> tuple[str, list[RetrievedSource]]:
        sources = self.retrieve(question)
        prompt = self.build_prompt(question, sources)
        response = self.ollama.generate(model=self.generation_model, prompt=prompt)
        return response["response"].strip(), sources

    def stream_answer(self, question: str) -> tuple[Iterator[str], list[RetrievedSource]]:
        sources = self.retrieve(question)
        prompt = self.build_prompt(question, sources)
        response_stream = self.ollama.generate(
            model=self.generation_model,
            prompt=prompt,
            stream=True,
        )

        def chunks() -> Iterator[str]:
            for chunk in response_stream:
                text = chunk.get("response", "")
                if text:
                    yield text

        return chunks(), sources


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local Raspberry Pi 5 RAG application using Ollama and ChromaDB."
    )
    parser.add_argument("-q", "--question", help="Ask one question and exit.")
    parser.add_argument("--model", default=DEFAULT_GENERATION_MODEL, help="Ollama generation model.")
    parser.add_argument("--embed-model", default=DEFAULT_EMBED_MODEL, help="Ollama embedding model.")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="ChromaDB persistent storage path.")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, help="ChromaDB collection name.")
    parser.add_argument("--top-k", type=int, default=3, help="Number of retrieved context chunks.")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the ChromaDB collection.")
    parser.add_argument("--show-sources", action="store_true", help="Print retrieved source snippets.")
    parser.add_argument("--stream", action="store_true", help="Stream generated tokens to stdout.")
    return parser


def print_sources(sources: list[RetrievedSource]) -> None:
    print("\nRetrieved sources:")
    for source in sources:
        distance = f", distance={source.distance:.4f}" if source.distance is not None else ""
        print(f"- {source.title}{distance}: {source.text}")


def ask_and_print(rag: LocalRAG, question: str, show_sources: bool, stream: bool) -> None:
    print(f"\nQuestion: {question}")
    if stream:
        answer_stream, sources = rag.stream_answer(question)
        print("\nAnswer:")
        for chunk in answer_stream:
            print(chunk, end="", flush=True)
        print()
    else:
        answer, sources = rag.answer(question)
        print(f"\nAnswer:\n{answer}")
    if show_sources:
        print_sources(sources)


def interactive_loop(rag: LocalRAG, show_sources: bool, stream: bool) -> None:
    print("Local RAG is ready. Type a question, or type 'exit' to quit.")
    while True:
        question = input("\nYou> ").strip()
        if question.lower() in {"exit", "quit", "q"}:
            print("Bye.")
            return
        if not question:
            continue
        ask_and_print(rag, question, show_sources, stream)


def main() -> int:
    args = build_parser().parse_args()
    Path(args.db_path).mkdir(parents=True, exist_ok=True)

    rag = LocalRAG(
        db_path=args.db_path,
        collection_name=args.collection,
        embed_model=args.embed_model,
        generation_model=args.model,
        top_k=args.top_k,
    )

    try:
        rag.prepare(rebuild=args.rebuild)
        if args.question:
            ask_and_print(rag, args.question, args.show_sources, args.stream)
        else:
            interactive_loop(rag, args.show_sources, args.stream)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as exc:
        print(f"\nError: {exc}")
        print("Check that Ollama is running and required models are installed:")
        print(f"  ollama pull {args.embed_model}")
        print(f"  ollama pull {args.model}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

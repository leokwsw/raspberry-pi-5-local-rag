import argparse
from pathlib import Path

from app import (
    DEFAULT_COLLECTION,
    DEFAULT_DB_PATH,
    DEFAULT_EMBED_MODEL,
    DEFAULT_GENERATION_MODEL,
    LocalRAG,
    RetrievedSource,
)


SAMPLE_QUESTIONS = [
    "Raspberry Pi 5 16GB 適合跑本機 RAG 嗎？",
    "在 Raspberry Pi 5 上跑 LLM 需要注意散熱嗎？",
    "Ollama 在這個專案中負責什麼？",
    "ChromaDB 在 RAG 流程中做什麼？",
    "RAG 的基本流程是什麼？",
    "Raspberry Pi 5 上應該先用哪個 LLM 模型？",
]


def format_sources(sources: list[RetrievedSource]) -> str:
    if not sources:
        return "No sources retrieved."

    lines: list[str] = []
    for index, source in enumerate(sources, start=1):
        distance = f" distance={source.distance:.4f}" if source.distance is not None else ""
        lines.append(f"### {index}. {source.title}{distance}\n\n{source.text}")
    return "\n\n".join(lines)


def build_rag(
    db_path: str,
    collection: str,
    embed_model: str,
    generation_model: str,
    top_k: int,
    rebuild: bool,
) -> LocalRAG:
    Path(db_path).mkdir(parents=True, exist_ok=True)
    rag = LocalRAG(
        db_path=db_path,
        collection_name=collection,
        embed_model=embed_model,
        generation_model=generation_model,
        top_k=top_k,
    )
    rag.prepare(rebuild=rebuild)
    return rag


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gradio web GUI for the local Raspberry Pi 5 RAG application."
    )
    parser.add_argument("--host", default="0.0.0.0", help="Gradio server host.")
    parser.add_argument("--port", type=int, default=7860, help="Gradio server port.")
    parser.add_argument("--model", default=DEFAULT_GENERATION_MODEL, help="Ollama generation model.")
    parser.add_argument("--embed-model", default=DEFAULT_EMBED_MODEL, help="Ollama embedding model.")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="ChromaDB persistent storage path.")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, help="ChromaDB collection name.")
    parser.add_argument("--top-k", type=int, default=3, help="Number of retrieved context chunks.")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the ChromaDB collection on startup.")
    parser.add_argument("--share", action="store_true", help="Create a public Gradio share link.")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        import gradio as gr
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing Gradio dependency. Run: pip install -r requirements.txt") from exc

    try:
        rag = build_rag(
            db_path=args.db_path,
            collection=args.collection,
            embed_model=args.embed_model,
            generation_model=args.model,
            top_k=args.top_k,
            rebuild=args.rebuild,
        )
    except Exception as exc:
        print(f"Error while preparing RAG: {exc}")
        print("Check that Ollama is running and required models are installed:")
        print(f"  ollama pull {args.embed_model}")
        print(f"  ollama pull {args.model}")
        return 1

    def ask(question: str, show_sources: bool):
        question = question.strip()
        if not question:
            yield "請先輸入問題。", "", "Waiting for a question."
            return

        yield (
            "AI is thinking...\n\nRetrieving relevant context from ChromaDB and asking the local Ollama model.",
            "",
            "Loading: retrieving context and generating answer...",
        )

        try:
            answer_stream, sources = rag.stream_answer(question)
        except Exception as exc:
            yield (
                f"Error: {exc}\n\n請確認 Ollama 正在執行，且模型已安裝。",
                "",
                "Failed. Check Ollama service and installed models.",
            )
            return

        source_text = format_sources(sources) if show_sources else ""
        partial_answer = ""
        yield "AI is writing the answer...", source_text, "Streaming answer from Ollama..."

        try:
            for chunk in answer_stream:
                partial_answer += chunk
                yield partial_answer, source_text, "Streaming answer from Ollama..."
        except Exception as exc:
            yield (
                f"{partial_answer}\n\nError while streaming: {exc}",
                source_text,
                "Streaming failed. Check Ollama service and model.",
            )
            return

        yield partial_answer.strip(), source_text, "Done."

    def rebuild_index() -> str:
        try:
            rag.prepare(rebuild=True)
        except Exception as exc:
            return f"Rebuild failed: {exc}"
        return "Index rebuilt successfully."

    with gr.Blocks(title="Raspberry Pi 5 Local RAG") as demo:
        gr.Markdown(
            """
            # Raspberry Pi 5 Local RAG

            Local RAG web GUI using Ollama and ChromaDB.
            """
        )

        with gr.Row():
            question = gr.Textbox(
                label="Question",
                placeholder="Ask about Raspberry Pi 5, Ollama, ChromaDB, or the RAG workflow...",
                lines=3,
            )
            with gr.Column(scale=0):
                show_sources = gr.Checkbox(label="Show sources", value=True)
                submit = gr.Button("Ask", variant="primary")
                rebuild = gr.Button("Rebuild Index")

        answer = gr.Markdown(label="Answer")
        sources = gr.Markdown(label="Retrieved Sources")
        status = gr.Textbox(label="Status", interactive=False)

        gr.Examples(
            examples=SAMPLE_QUESTIONS,
            inputs=question,
        )

        submit.click(ask, inputs=[question, show_sources], outputs=[answer, sources, status])
        question.submit(ask, inputs=[question, show_sources], outputs=[answer, sources, status])
        rebuild.click(rebuild_index, outputs=status)

    demo.queue().launch(server_name=args.host, server_port=args.port, share=args.share)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

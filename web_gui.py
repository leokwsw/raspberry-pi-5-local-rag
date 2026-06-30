"""
Enhanced Gradio Web GUI for Raspberry Pi 5 Local RAG.
Features: Dataset management, Chat history, Settings, Feedback RAG.
"""

import argparse
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from enhanced_rag import (
    EnhancedRAG,
    RetrievedSource,
    DEFAULT_DB_PATH,
    DEFAULT_COLLECTION,
    DEFAULT_EMBED_MODEL,
    DEFAULT_GENERATION_MODEL,
    DEFAULT_RERANK_MODEL,
)
from storage import StorageManager, Conversation, Document, Feedback
from media_processor import get_supported_extensions


UPLOAD_DIR = "./uploads"


def ensure_upload_dir():
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


def build_rag(
    db_path: str,
    collection: str,
    embed_model: str,
    generation_model: str,
    rerank_model: str,
    top_k: int,
    storage_path: str,
    rebuild: bool,
    use_feedback: bool = True,
    use_graph: bool = True,
    use_reranking: bool = True,
) -> EnhancedRAG:
    Path(db_path).mkdir(parents=True, exist_ok=True)
    rag = EnhancedRAG(
        db_path=db_path,
        collection_name=collection,
        embed_model=embed_model,
        generation_model=generation_model,
        rerank_model=rerank_model,
        top_k=top_k,
        storage_path=storage_path,
        use_feedback=use_feedback,
        use_graph=use_graph,
        use_reranking=use_reranking,
    )
    rag.prepare(rebuild=rebuild)
    return rag


def format_sources(sources: list[RetrievedSource], show_scores: bool = False) -> str:
    if not sources:
        return "No sources retrieved."

    lines = []
    for i, source in enumerate(sources, start=1):
        header = f"### {i}. {source.title}"
        if show_scores:
            score_info = f" (dist={source.distance:.4f}" if source.distance else " (dist=N/A"
            if source.rerank_score is not None:
                score_info += f", rerank={source.rerank_score:.2f}"
            if source.feedback_score != 0:
                score_info += f", fb={source.feedback_score:+.1f}"
            if source.graph_boost != 0:
                score_info += f", graph={source.graph_boost:+.2f}"
            score_info += f", adj={source.adjusted_score:.4f})"
            header += score_info
        lines.append(f"{header}\n\n{source.text}")
    return "\n\n---\n\n".join(lines)


def format_conversation_list(conversations: list[Conversation]) -> list[tuple[str, str]]:
    result = []
    for conv in conversations:
        updated = conv.updated_at[:16].replace("T", " ") if conv.updated_at else ""
        label = f"{conv.title} ({updated})"
        result.append((label, conv.id))
    return result


def format_documents_table(documents: list[Document]) -> list[list[str]]:
    rows = []
    for doc in documents:
        created = doc.created_at[:16].replace("T", " ") if doc.created_at else ""
        rows.append([
            doc.filename,
            doc.content_type,
            created,
            str(len(doc.chunk_ids)),
            doc.id,
        ])
    return rows


def format_feedback_table(feedbacks: list[Feedback]) -> list[list[str]]:
    rows = []
    for fb in feedbacks:
        created = fb.created_at[:16].replace("T", " ") if fb.created_at else ""
        question_preview = fb.question[:50] + "..." if len(fb.question) > 50 else fb.question
        rows.append([
            question_preview,
            fb.rating,
            fb.comment or "",
            created,
        ])
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enhanced Gradio web GUI for Raspberry Pi 5 local RAG."
    )
    parser.add_argument("--host", default="0.0.0.0", help="Server host.")
    parser.add_argument("--port", type=int, default=7860, help="Server port.")
    parser.add_argument("--model", default=DEFAULT_GENERATION_MODEL, help="Ollama LLM generation model.")
    parser.add_argument("--embed-model", default=DEFAULT_EMBED_MODEL, help="Ollama embedding model.")
    parser.add_argument("--rerank-model", default=DEFAULT_RERANK_MODEL, help="Ollama reranking model.")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="ChromaDB storage path.")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, help="ChromaDB collection name.")
    parser.add_argument("--storage-path", default="./rag_storage", help="Storage path for conversations and metadata.")
    parser.add_argument("--top-k", type=int, default=3, help="Number of retrieved context chunks.")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the ChromaDB collection on startup.")
    parser.add_argument("--share", action="store_true", help="Create a public Gradio share link.")
    parser.add_argument("--no-feedback", action="store_true", help="Disable feedback RAG.")
    parser.add_argument("--no-graph", action="store_true", help="Disable graph DB features.")
    parser.add_argument("--no-reranking", action="store_true", help="Disable reranking.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    ensure_upload_dir()

    try:
        import gradio as gr
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing Gradio. Run: pip install -r requirements.txt") from exc

    try:
        rag = build_rag(
            db_path=args.db_path,
            collection=args.collection,
            embed_model=args.embed_model,
            generation_model=args.model,
            rerank_model=args.rerank_model,
            top_k=args.top_k,
            storage_path=args.storage_path,
            rebuild=args.rebuild,
            use_feedback=not args.no_feedback,
            use_graph=not args.no_graph,
            use_reranking=not args.no_reranking,
        )
    except Exception as exc:
        print(f"Error while preparing RAG: {exc}")
        print("Check that Ollama is running and required models are installed:")
        print(f"  ollama pull {args.embed_model}")
        print(f"  ollama pull {args.model}")
        print(f"  ollama pull {args.rerank_model}  # Optional for reranking")
        return 1

    current_conversation_id: Optional[str] = None
    last_sources: list[RetrievedSource] = []
    last_question: str = ""
    last_answer: str = ""

    # Chat functions
    def new_chat():
        nonlocal current_conversation_id, last_sources, last_question, last_answer
        conv = rag.storage.create_conversation("New Chat")
        current_conversation_id = conv.id
        last_sources = []
        last_question = ""
        last_answer = ""
        return [], get_chat_list(), f"Started new chat: {conv.id[:8]}"

    def load_chat(conv_id: str):
        nonlocal current_conversation_id, last_sources, last_question, last_answer
        if not conv_id:
            return [], f"No conversation selected."

        conv = rag.storage.get_conversation(conv_id)
        if not conv:
            return [], f"Conversation not found."

        current_conversation_id = conv.id
        last_sources = []
        last_question = ""
        last_answer = ""

        history = []
        for msg in conv.messages:
            if msg.role == "user":
                history.append({"role": "user", "content": msg.content})
            else:
                history.append({"role": "assistant", "content": msg.content})

        return history, f"Loaded: {conv.title}"

    def get_chat_list():
        conversations = rag.storage.list_conversations(limit=50)
        return format_conversation_list(conversations)

    def delete_chat(conv_id: str):
        nonlocal current_conversation_id
        if conv_id:
            rag.storage.delete_conversation(conv_id)
            if current_conversation_id == conv_id:
                current_conversation_id = None
        return get_chat_list(), "Chat deleted."

    def chat(message: str, history: list, show_sources: bool, show_scores: bool):
        nonlocal current_conversation_id, last_sources, last_question, last_answer

        if not message.strip():
            yield history, "", "Please enter a message."
            return

        if not current_conversation_id:
            conv = rag.storage.create_conversation(message[:30] + "..." if len(message) > 30 else message)
            current_conversation_id = conv.id

        history = history + [{"role": "user", "content": message}]
        yield history, "", "Retrieving context..."

        rag.storage.add_message(current_conversation_id, "user", message)

        try:
            answer_stream, sources = rag.stream_answer(message)
            last_sources = sources
            last_question = message
        except Exception as exc:
            error_msg = f"Error: {exc}"
            history = history + [{"role": "assistant", "content": error_msg}]
            yield history, "", "Failed. Check Ollama service."
            return

        source_text = format_sources(sources, show_scores) if show_sources else ""
        partial_answer = ""
        history = history + [{"role": "assistant", "content": ""}]

        try:
            for chunk in answer_stream:
                partial_answer += chunk
                history[-1]["content"] = partial_answer
                yield history, source_text, "Generating..."
        except Exception as exc:
            history[-1]["content"] = f"{partial_answer}\n\nError: {exc}"
            yield history, source_text, "Streaming failed."
            return

        last_answer = partial_answer.strip()
        history[-1]["content"] = last_answer

        rag.storage.add_message(
            current_conversation_id,
            "assistant",
            last_answer,
            sources=[{"id": s.id, "title": s.title} for s in sources],
        )

        if len(rag.storage.get_conversation(current_conversation_id).messages) == 2:
            title = message[:30] + "..." if len(message) > 30 else message
            rag.storage.update_conversation_title(current_conversation_id, title)

        yield history, source_text, "Done."

    def submit_feedback(rating: str, comment: str):
        nonlocal last_sources, last_question, last_answer
        if not last_question or not last_answer:
            return "No recent Q&A to rate."
        if rating not in ["positive", "negative"]:
            return "Please select a rating."

        source_ids = [s.id for s in last_sources]
        rag.add_feedback(last_question, last_answer, rating, source_ids, comment or None)
        return f"Feedback submitted: {rating}"

    # Dataset functions
    def upload_file(file):
        if file is None:
            return get_documents_table(), "No file uploaded."

        try:
            dest_path = Path(UPLOAD_DIR) / Path(file.name).name
            shutil.copy(file.name, dest_path)
            doc = rag.add_document(str(dest_path))
            return get_documents_table(), f"Uploaded and indexed: {doc.filename} ({len(doc.chunk_ids)} chunks)"
        except Exception as exc:
            return get_documents_table(), f"Error: {exc}"

    def add_text(text: str, title: str):
        if not text.strip():
            return get_documents_table(), "Please enter some text."

        title = title.strip() or "User Text"
        try:
            doc_id = rag.add_text_content(text, title)
            return get_documents_table(), f"Added text document: {title}"
        except Exception as exc:
            return get_documents_table(), f"Error: {exc}"

    def delete_document(doc_id: str):
        if not doc_id:
            return get_documents_table(), "No document selected."

        if rag.delete_document(doc_id):
            return get_documents_table(), f"Deleted document: {doc_id[:8]}"
        return get_documents_table(), "Document not found."

    def get_documents_table():
        docs = rag.storage.list_documents()
        return format_documents_table(docs)

    # Graph functions
    def get_entities_info():
        entities = rag.storage.list_entities()
        if not entities:
            return "No entities in knowledge graph."

        lines = ["## Entities\n"]
        by_type = {}
        for e in entities:
            by_type.setdefault(e.entity_type, []).append(e)

        for etype, ents in sorted(by_type.items()):
            lines.append(f"### {etype.title()}")
            for e in ents:
                desc = f" - {e.description}" if e.description else ""
                docs = f" ({len(e.document_ids)} docs)" if e.document_ids else ""
                lines.append(f"- **{e.name}**{desc}{docs}")
            lines.append("")

        return "\n".join(lines)

    def get_relationships_info():
        entities = rag.storage.list_entities()
        if not entities:
            return "No relationships in knowledge graph."

        lines = ["## Relationships\n"]
        seen = set()

        for entity in entities:
            rels = rag.storage.get_relationships_for_entity(entity.id)
            for rel in rels:
                if rel.id in seen:
                    continue
                seen.add(rel.id)

                source = rag.storage.get_entity(rel.source_entity_id)
                target = rag.storage.get_entity(rel.target_entity_id)
                if source and target:
                    lines.append(f"- {source.name} **{rel.relationship_type}** {target.name}")

        return "\n".join(lines) if len(lines) > 1 else "No relationships found."

    # Settings functions
    def get_stats():
        stats = rag.get_stats()
        model_status = rag.check_models()
        
        def model_status_icon(available: bool) -> str:
            return "✅" if available else "⚠️"
        
        lines = [
            "## System Statistics\n",
            "### Ollama Models (3 models required)",
            f"- {model_status_icon(model_status.get('llm', False))} LLM: `{stats['models']['llm_model']}`",
            f"- {model_status_icon(model_status.get('embed', False))} Embedding: `{stats['models']['embed_model']}`",
            f"- {model_status_icon(model_status.get('rerank', False))} Reranking: `{stats['models']['rerank_model']}`",
            "",
            "### Vector Database (ChromaDB)",
            f"- Collection: {stats['vector_db']['collection']}",
            f"- Documents: {stats['vector_db']['document_count']}",
            "",
            "### Graph Database (SQLite)",
            f"- Entities: {stats['storage']['entities']}",
            f"- Relationships: {stats['storage']['relationships']}",
            "",
            "### Storage",
            f"- Conversations: {stats['storage']['conversations']}",
            f"- Messages: {stats['storage']['messages']}",
            f"- Documents: {stats['storage']['documents']}",
            f"- Feedback entries: {stats['storage']['feedback']}",
            "",
            "### RAG Settings",
            f"- Top-K: {stats['settings']['top_k']}",
            f"- Reranking: {'Enabled' if stats['settings']['use_reranking'] else 'Disabled'}",
            f"- Feedback RAG: {'Enabled' if stats['settings']['use_feedback'] else 'Disabled'}",
            f"- Graph DB: {'Enabled' if stats['settings']['use_graph'] else 'Disabled'}",
        ]
        return "\n".join(lines)

    def rebuild_index():
        try:
            rag.prepare(rebuild=True)
            return "Index rebuilt successfully."
        except Exception as exc:
            return f"Rebuild failed: {exc}"

    def get_feedback_history():
        feedbacks = rag.storage.list_feedback(limit=50)
        return format_feedback_table(feedbacks)

    # Build Gradio interface
    with gr.Blocks(title="Raspberry Pi 5 Enhanced RAG", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            """
            # 🍓 Raspberry Pi 5 Enhanced RAG

            Local RAG system with Graph DB and Feedback support. Running on Ollama + ChromaDB.
            """
        )

        with gr.Tabs():
            # Chat Tab
            with gr.Tab("💬 Chat"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Conversations")
                        chat_list = gr.Dropdown(
                            label="Select Chat",
                            choices=get_chat_list(),
                            interactive=True,
                        )
                        with gr.Row():
                            new_chat_btn = gr.Button("New Chat", size="sm")
                            load_chat_btn = gr.Button("Load", size="sm")
                            delete_chat_btn = gr.Button("Delete", size="sm", variant="stop")

                        gr.Markdown("### Options")
                        show_sources = gr.Checkbox(label="Show Sources", value=True)
                        show_scores = gr.Checkbox(label="Show Scores", value=False)

                        gr.Markdown("### Feedback")
                        feedback_rating = gr.Radio(
                            ["positive", "negative"],
                            label="Rate Last Answer",
                        )
                        feedback_comment = gr.Textbox(
                            label="Comment (optional)",
                            lines=2,
                        )
                        feedback_btn = gr.Button("Submit Feedback", size="sm")

                    with gr.Column(scale=3):
                        chatbot = gr.Chatbot(
                            label="Chat",
                            height=400,
                            type="messages",
                        )
                        msg_input = gr.Textbox(
                            label="Message",
                            placeholder="Ask a question about your knowledge base...",
                            lines=2,
                        )
                        with gr.Row():
                            send_btn = gr.Button("Send", variant="primary")
                            clear_btn = gr.Button("Clear")

                        sources_output = gr.Markdown(label="Retrieved Sources")
                        chat_status = gr.Textbox(label="Status", interactive=False)

            # Dataset Tab
            with gr.Tab("📁 Dataset"):
                gr.Markdown("### Upload Files")
                gr.Markdown(
                    f"Supported formats: Text ({', '.join(get_supported_extensions()['text'])}), "
                    f"Audio ({', '.join(get_supported_extensions()['audio'])}), "
                    f"Video ({', '.join(get_supported_extensions()['video'])})"
                )

                with gr.Row():
                    file_upload = gr.File(label="Upload File")
                    upload_btn = gr.Button("Upload & Index", variant="primary")

                gr.Markdown("### Add Text Content")
                with gr.Row():
                    text_input = gr.Textbox(
                        label="Text Content",
                        lines=5,
                        placeholder="Paste text content here...",
                    )
                    text_title = gr.Textbox(
                        label="Title",
                        placeholder="Document title",
                    )
                add_text_btn = gr.Button("Add Text")

                gr.Markdown("### Documents")
                documents_table = gr.Dataframe(
                    headers=["Filename", "Type", "Created", "Chunks", "ID"],
                    value=get_documents_table(),
                    interactive=False,
                )
                with gr.Row():
                    doc_id_input = gr.Textbox(label="Document ID to delete")
                    delete_doc_btn = gr.Button("Delete Document", variant="stop")

                dataset_status = gr.Textbox(label="Status", interactive=False)

            # Graph Tab
            with gr.Tab("🔗 Knowledge Graph"):
                gr.Markdown("### Knowledge Graph Visualization")
                gr.Markdown(
                    "The knowledge graph stores entities and relationships extracted from your documents. "
                    "This helps improve retrieval by understanding semantic connections."
                )

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Entities")
                        entities_info = gr.Markdown(get_entities_info())
                    with gr.Column():
                        gr.Markdown("### Relationships")
                        relationships_info = gr.Markdown(get_relationships_info())

                refresh_graph_btn = gr.Button("Refresh Graph View")

            # Feedback Tab
            with gr.Tab("📊 Feedback History"):
                gr.Markdown("### User Feedback")
                gr.Markdown(
                    "Feedback helps improve retrieval quality over time. "
                    "Positive feedback boosts source scores, negative feedback reduces them."
                )

                feedback_table = gr.Dataframe(
                    headers=["Question", "Rating", "Comment", "Date"],
                    value=get_feedback_history(),
                    interactive=False,
                )
                refresh_feedback_btn = gr.Button("Refresh")

            # Settings Tab
            with gr.Tab("⚙️ Settings"):
                gr.Markdown("### System Information")
                stats_output = gr.Markdown(get_stats())

                gr.Markdown("### Actions")
                with gr.Row():
                    rebuild_btn = gr.Button("Rebuild Index", variant="secondary")
                    refresh_stats_btn = gr.Button("Refresh Stats")

                settings_status = gr.Textbox(label="Status", interactive=False)

        # Event handlers - Chat
        new_chat_btn.click(
            new_chat,
            outputs=[chatbot, chat_list, chat_status],
        )

        load_chat_btn.click(
            load_chat,
            inputs=[chat_list],
            outputs=[chatbot, chat_status],
        )

        delete_chat_btn.click(
            delete_chat,
            inputs=[chat_list],
            outputs=[chat_list, chat_status],
        )

        send_btn.click(
            chat,
            inputs=[msg_input, chatbot, show_sources, show_scores],
            outputs=[chatbot, sources_output, chat_status],
        ).then(
            lambda: "",
            outputs=[msg_input],
        ).then(
            get_chat_list,
            outputs=[chat_list],
        )

        msg_input.submit(
            chat,
            inputs=[msg_input, chatbot, show_sources, show_scores],
            outputs=[chatbot, sources_output, chat_status],
        ).then(
            lambda: "",
            outputs=[msg_input],
        ).then(
            get_chat_list,
            outputs=[chat_list],
        )

        clear_btn.click(
            lambda: ([], "", "Cleared."),
            outputs=[chatbot, sources_output, chat_status],
        )

        feedback_btn.click(
            submit_feedback,
            inputs=[feedback_rating, feedback_comment],
            outputs=[chat_status],
        ).then(
            lambda: (None, ""),
            outputs=[feedback_rating, feedback_comment],
        )

        # Event handlers - Dataset
        upload_btn.click(
            upload_file,
            inputs=[file_upload],
            outputs=[documents_table, dataset_status],
        )

        add_text_btn.click(
            add_text,
            inputs=[text_input, text_title],
            outputs=[documents_table, dataset_status],
        ).then(
            lambda: ("", ""),
            outputs=[text_input, text_title],
        )

        delete_doc_btn.click(
            delete_document,
            inputs=[doc_id_input],
            outputs=[documents_table, dataset_status],
        ).then(
            lambda: "",
            outputs=[doc_id_input],
        )

        # Event handlers - Graph
        refresh_graph_btn.click(
            lambda: (get_entities_info(), get_relationships_info()),
            outputs=[entities_info, relationships_info],
        )

        # Event handlers - Feedback
        refresh_feedback_btn.click(
            get_feedback_history,
            outputs=[feedback_table],
        )

        # Event handlers - Settings
        rebuild_btn.click(
            rebuild_index,
            outputs=[settings_status],
        ).then(
            get_stats,
            outputs=[stats_output],
        )

        refresh_stats_btn.click(
            get_stats,
            outputs=[stats_output],
        )

    demo.queue().launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

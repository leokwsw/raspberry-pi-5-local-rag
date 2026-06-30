# raspberry-pi-5-local-rag

Small local RAG AI application for Raspberry Pi 5 16GB using Ollama and ChromaDB.

This project provides multiple entry points:

- **CLI**: `app.py` - Simple command-line interface
- **Basic Web GUI**: `app_gradio.py` - Basic Gradio web interface
- **Enhanced Web GUI**: `web_gui.py` - Full-featured web interface with dataset management, chat history, feedback RAG, and knowledge graph

All versions share the same RAG pipeline, ChromaDB storage, and Ollama models.

## Features

### Core RAG Features
- Local embedding and LLM generation with Ollama
- Vector storage with ChromaDB
- Streaming answer generation
- Retrieval-Augmented Generation workflow

### Enhanced Features (web_gui.py)
- **Dataset Management**: Upload and index text, audio, and video files
- **Chat History**: Save and load conversation sessions
- **Feedback RAG**: Rate answers to improve retrieval quality over time
- **Knowledge Graph**: Entity and relationship extraction for better context understanding
- **Multi-modal Support**: Process text files, audio transcription, video transcription

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Web GUI (Gradio)                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │  Chat   │ │ Dataset │ │  Graph  │ │Settings │           │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           │
└───────┼───────────┼───────────┼───────────┼─────────────────┘
        │           │           │           │
┌───────┴───────────┴───────────┴───────────┴─────────────────┐
│                    Enhanced RAG Engine                       │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐               │
│  │  Retrieval │ │  Feedback  │ │   Graph    │               │
│  │  + Ranking │ │  Scoring   │ │   Boost    │               │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘               │
└────────┼──────────────┼──────────────┼──────────────────────┘
         │              │              │
┌────────┴──────────────┴──────────────┴──────────────────────┐
│                      Storage Layer                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ ChromaDB │ │ SQLite   │ │ Graph DB │ │ Feedback │        │
│  │ (Vector) │ │ (Meta)   │ │ (Entity) │ │ (Rating) │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
└─────────────────────────────────────────────────────────────┘
         │
┌────────┴────────────────────────────────────────────────────┐
│                     Ollama (Local LLM)                       │
│  ┌────────────────┐ ┌────────────────┐                      │
│  │ nomic-embed    │ │ llama3.2:3b    │                      │
│  │ (Embedding)    │ │ (Generation)   │                      │
│  └────────────────┘ └────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

- Raspberry Pi 5 16GB or another local machine
- Python 3.10+
- Ollama installed and running
- Enough disk space for the selected Ollama models

### Python Dependencies

Core dependencies in `requirements.txt`:

```txt
chromadb
ollama
gradio
```

Optional for audio/video processing:

```txt
openai-whisper  # or faster-whisper for better performance
ffmpeg          # system package for video processing
```

## Setup

### 1. Create Virtual Environment

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Install Ollama

Install Ollama from [ollama.com](https://ollama.com), then pull the default models:

```sh
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

Make sure Ollama is running:

```sh
ollama serve
```

### 3. Optional: Audio/Video Support

For audio and video transcription, install Whisper:

```sh
pip install openai-whisper
```

For video processing, install FFmpeg:

```sh
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

## Usage

### CLI (app.py)

Start interactive chat mode:

```sh
python3 app.py
```

Ask a single question:

```sh
python3 app.py --question "Raspberry Pi 5 的處理器是什麼？"
```

Stream the answer:

```sh
python3 app.py --question "RAG 的基本流程是什麼？" --stream
```

Show retrieved sources:

```sh
python3 app.py --question "本機 RAG 需要注意什麼？" --show-sources
```

Rebuild the index:

```sh
python3 app.py --rebuild
```

### Basic Web GUI (app_gradio.py)

Start the basic Gradio interface:

```sh
python3 app_gradio.py
```

Options:

```sh
python3 app_gradio.py --host 0.0.0.0 --port 7860
python3 app_gradio.py --rebuild
python3 app_gradio.py --model llama3.2:3b --top-k 3
```

### Enhanced Web GUI (web_gui.py)

Start the full-featured web interface:

```sh
python3 web_gui.py
```

Options:

```sh
# Basic options
python3 web_gui.py --host 0.0.0.0 --port 7860

# Model options
python3 web_gui.py --model llama3.2:3b --embed-model nomic-embed-text

# Storage options
python3 web_gui.py --db-path ./chroma_db --storage-path ./rag_storage

# Feature toggles
python3 web_gui.py --no-feedback  # Disable feedback RAG
python3 web_gui.py --no-graph     # Disable knowledge graph

# Rebuild index on startup
python3 web_gui.py --rebuild

# Create public share link
python3 web_gui.py --share
```

Access the interface at `http://<raspberry-pi-ip>:7860`

## Enhanced Features

### Dataset Management

The enhanced GUI allows you to:

1. **Upload Files**: Drag and drop text, audio, or video files
2. **Add Text**: Paste text content directly
3. **View Documents**: See all indexed documents with metadata
4. **Delete Documents**: Remove documents from the index

Supported file types:
- Text: `.txt`, `.md`, `.rst`, `.csv`, `.json`, `.xml`, `.html`
- Audio: `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`, `.webm`
- Video: `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`

### Chat History

- **New Chat**: Start a fresh conversation
- **Load Chat**: Resume previous conversations
- **Delete Chat**: Remove old conversations
- Conversations are automatically saved with timestamps

### Feedback RAG

Improve retrieval quality by rating answers:

1. After receiving an answer, click "positive" or "negative"
2. Optionally add a comment explaining your rating
3. Click "Submit Feedback"

The system uses feedback to adjust retrieval scores:
- Positive feedback boosts the score of used sources
- Negative feedback reduces the score of used sources

### Knowledge Graph

The system automatically extracts entities and relationships:

- **Entities**: Concepts, hardware, software mentioned in documents
- **Relationships**: How entities are connected (e.g., "runs", "uses", "provides")

Graph information is used to:
- Boost retrieval of related documents
- Provide additional context in the prompt

## Data Storage

```
./chroma_db/      # ChromaDB vector database
./rag_storage/    # SQLite database for metadata
  └── rag_data.db # Conversations, feedback, entities, relationships
./uploads/        # Uploaded files (for web_gui.py)
```

Delete these folders or run with `--rebuild` to recreate the index.

## Configuration

### CLI Options (app.py)

| Option | Default | Description |
|--------|---------|-------------|
| `-q, --question` | - | Ask one question and exit |
| `--model` | llama3.2:3b | Ollama generation model |
| `--embed-model` | nomic-embed-text | Ollama embedding model |
| `--db-path` | ./chroma_db | ChromaDB storage path |
| `--collection` | pi_local_rag | ChromaDB collection name |
| `--top-k` | 3 | Number of retrieved chunks |
| `--rebuild` | false | Recreate the index |
| `--show-sources` | false | Print retrieved sources |
| `--stream` | false | Stream generated tokens |

### Enhanced GUI Options (web_gui.py)

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | 0.0.0.0 | Server host |
| `--port` | 7860 | Server port |
| `--model` | llama3.2:3b | Ollama generation model |
| `--embed-model` | nomic-embed-text | Ollama embedding model |
| `--db-path` | ./chroma_db | ChromaDB storage path |
| `--storage-path` | ./rag_storage | Metadata storage path |
| `--collection` | pi_local_rag | ChromaDB collection name |
| `--top-k` | 3 | Number of retrieved chunks |
| `--rebuild` | false | Recreate the index on startup |
| `--share` | false | Create public Gradio link |
| `--no-feedback` | false | Disable feedback RAG |
| `--no-graph` | false | Disable knowledge graph |

## Troubleshooting

### Ollama Connection Error

Check that Ollama is running:

```sh
ollama list
```

If a model is missing:

```sh
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

### Audio/Video Processing Errors

Make sure Whisper and FFmpeg are installed:

```sh
pip install openai-whisper
sudo apt install ffmpeg
```

### Slow Performance

On Raspberry Pi 5 16GB:
- Use `llama3.2:3b` (default) instead of larger models
- Keep `top_k` low (3-5)
- Use active cooling to prevent thermal throttling

### Stale Index

Rebuild the index:

```sh
python3 app.py --rebuild
# or
python3 web_gui.py --rebuild
```

## Project Files

| File | Description |
|------|-------------|
| `app.py` | CLI RAG application |
| `app_gradio.py` | Basic Gradio web GUI |
| `web_gui.py` | Enhanced Gradio web GUI |
| `enhanced_rag.py` | Enhanced RAG engine with feedback and graph |
| `storage.py` | SQLite storage for conversations, feedback, graph |
| `media_processor.py` | Text/audio/video processing |
| `requirements.txt` | Python dependencies |
| `AGENTS.md` | Development guidelines |

## License

MIT License

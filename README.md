# SyncDocs RAG 🚀

![SyncDocs RAG Hero](https://raw.githubusercontent.com/prasanna00019/SyncDocs-RAG/main/logo.png)

**SyncDocs RAG** is a "just-in-time" Retrieval-Augmented Generation (RAG) system designed to solve one of the biggest bottlenecks in AI development: **outdated knowledge.**

## 🧠 The Problem: The "Knowledge Cutoff"

Standard LLMs (like GPT-4 or local models) suffer from a **knowledge cutoff.** If a software library was updated last week, the LLM won't know about the new API changes or deprecated methods. Relying on outdated data leads to:

- **Hallucinations**: The AI suggests non-existent parameters or methods.
- **Wasted Time**: Developers spend hours debugging code that the "AI thought was right."
- **Stale Context**: Static documentation datasets are obsolete almost as soon as they are compiled.

## ⚡ The Solution: SyncDocs RAG

SyncDocs RAG eliminates the cutoff by bridging the gap between your LLM and the live web. It uses **Firecrawl** to "Sync" the latest documentation directly into the AI's reasoning loop.

- **Eliminate Halucinations**: Answers are grounded in the *exact* documentation you point it at.
- **Just-In-Time Intelligence**: If the docs update, your AI updates. Instantly.
- **Precision Retrieval**: Uses semantic Markdown splitting to ensure the AI understands the *structure* of the documentation, not just the words.

---

## ✨ Key Features

- **Just-In-Time Ingestion**: Scrape any documentation site in real-time using **Firecrawl**.
- **Full-Stack UI**: Modern React + Tailwind frontend with real-time pipeline status and terminal-style logs.
- **Semantic Link Filtering**: Embeds the query and available URLs to mathematically select the most relevant pages, eliminating LLM hallucination and saving context space.
- **Advanced RAG (HyDE & Cross-Encoder)**: Generates hypothetical answers to massively improve retrieval accuracy, followed by `sentence-transformers` Cross-Encoder re-ranking to surface the definitive top chunks.
- **Enterprise Security**: Built-in input sanitization, heuristic blacklist checking, and system prompt XML delimiters to prevent jailbreaks and prompt injections.
- **High-Performance Non-Blocking Backend**: True concurrent async API execution paired with **MD5 Content Hashing** to instantly skip re-scraping and embedding unchanged documentation pages.
- **Local-First AI**: Optimized for local execution with **Ollama** (supports cloud fallback for chat).

## 🏗️ Architecture

- **Backend**: FastAPI server with strictly unblocked asynchronous pipeline execution and SSE logging.
- **Frontend**: Vite + React 19 + Tailwind CSS v3 with a sleek dark theme.
- **Vector DB**: ChromaDB for local embedding storage.
- **AI Stack**: LangChain Core/Community/Ollama for orchestration and HuggingFace for fast local embeddings.
- **Re-Ranking**: `sentence-transformers` (Cross-Encoder) for state-of-the-art chunk scoring.

## 🚀 Getting Started

### 1. Prerequisites

- [Ollama](https://ollama.com/) installed and running.
- [Firecrawl API Key](https://firecrawl.dev/).
- Python 3.10+ and Node.js.

### 2. Environment Setup

Create a `.env` file in the `backend/` directory:

```env
FIRECRAWL_API_KEY="fc-..."
OPENAI_API_KEY="sk-..."  # Optional, defaults to Ollama
```

### 3. Run the Backend

```bash
cd backend
uv venv
# Activate venv then:
uv pip install -r requirements.txt
python server.py
```

### 4. Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

## 🛠️ Configuration

**SyncDocs RAG** automatically selects the best available models from your local Ollama:

- **Chat**: Prefers `minimax-m2.5:cloud` or `gemma3:4b`.
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (CPU-optimized, blazing fast local embeddings).

## 📄 License

MIT

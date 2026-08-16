# Repo-Aware Coding Assistant

A self-hosted, AST-aware code intelligence service for Python repositories. It indexes functions, classes, methods, call relationships, file/line locations, and docstrings so questions are answered with grounded repository references instead of arbitrary text chunks.

## What works

- Python AST chunking at function, async-function, method, and class boundaries
- Forward call graph plus reverse caller graph
- Repository-aware lexical retrieval with symbol/path boosts
- Grounded file, line, and symbol references
- CLI for indexing and asking questions
- FastAPI endpoints for indexing and querying
- Helpful errors for missing indexes and invalid paths
- Docker-compatible service
- Automated unit and API integration tests
- GitHub Actions CI on pushes and pull requests

The assistant intentionally does **not** invent code patches. It first identifies the code that matters and its caller/callee relationships. A patch should only be created after a concrete requested behavior change is known.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m code_assistant.cli index .
python -m code_assistant.cli ask "where is retrieve used?"
```

Run the tests:

```bash
pytest -q
```

## API

Start the service:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs` for the interactive Swagger UI.

Create an index:

```bash
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{"repo_path":".","index_path":".code-index.json"}'
```

Ask a repository question:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"where is retrieve used?","index_path":".code-index.json"}'
```

## Docker

```bash
docker compose up --build
```

Then visit `http://localhost:8000/docs`.

## How it works

1. `index_repo` scans Python files while excluding common generated and virtual-environment directories.
2. `chunk_file` uses Python's AST to extract semantic chunks and calls.
3. The index records symbols, outgoing call edges, and reverse caller edges.
4. `retrieve` ranks repository chunks using lexical relevance plus exact symbol/path boosts.
5. `answer` returns relevant locations and caller/callee context with precise repository references.

## Current scope

Parsing is Python-only and symbol resolution is intentionally lightweight. Calls with the same short symbol name in multiple scopes can produce multiple graph candidates. This is a deterministic, local-first retrieval layer rather than an LLM patch generator.

Good next extensions are Tree-sitter language support, qualified-name resolution, git-diff awareness, local embeddings/reranking, and an optional local model synthesis layer.

## License

MIT licensed. Repository code is processed locally by default and is not sent to a paid external model.

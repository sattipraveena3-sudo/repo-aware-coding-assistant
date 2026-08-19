# Repo-Aware Coding Assistant

A complete, local-first coding assistant that understands **repository structure instead of arbitrary text chunks**. It indexes Python functions/classes with the AST, builds caller/callee relationships, retrieves grounded code context, and can optionally send only retrieved context to a self-hosted Ollama model for natural-language synthesis.

## Included

- **Repository ingestion** — index local folders or clone Git repositories available to the runtime.
- **AST-aware indexing** — functions, async functions, classes, methods, qualified names, docstrings, source ranges, and call relationships.
- **Graph-aware retrieval** — lexical relevance plus linked callers/callees.
- **Grounded answers** — deterministic offline mode always works; Ollama mode adds natural-language synthesis and automatically falls back if unavailable.
- **Web application** — responsive UI for adding repositories, refreshing indexes, asking questions, and viewing references.
- **FastAPI backend** — health, repository management, refresh, and ask endpoints with generated OpenAPI docs.
- **CLI** — index, clone, list, refresh, and ask commands.
- **Persistent workspace** — repository metadata and indexes survive restarts.
- **Docker + Compose** — application and Ollama services with persistent volumes.
- **Automated tests + GitHub Actions CI** — core, workspace, and end-to-end API coverage.

## Architecture

```text
Browser UI
   │
   ▼
FastAPI API ─────────────── CLI
   │                        │
   └──────── Workspace ─────┘
              │
      ┌───────┴────────┐
      ▼                ▼
 Repository files   JSON indexes
      │
      ▼
 Python AST indexer
      │
      ├─ symbol chunks
      ├─ source ranges
      ├─ call graph
      └─ reverse caller graph
              │
              ▼
      graph-aware retriever
              │
       ┌──────┴──────┐
       ▼             ▼
 deterministic     Ollama
 grounded answer   synthesis
```

## Fastest local start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
pytest -q
uvicorn code_assistant.api:app --reload
```

Open `http://localhost:8000`. API docs are at `http://localhost:8000/docs`.

Index this project from the UI using the project directory, or via CLI:

```bash
python -m code_assistant.cli index .
python -m code_assistant.cli list
```

The `index` command returns a repository id. Use it to ask:

```bash
python -m code_assistant.cli ask <repo-id> "Where is repository refresh implemented and what does it call?"
```

## Optional local LLM with Ollama

The assistant works without any model. For richer synthesis:

```bash
ollama pull qwen2.5-coder:3b
export OLLAMA_MODEL=qwen2.5-coder:3b
uvicorn code_assistant.api:app --reload
```

Only retrieved repository context is sent to Ollama. If Ollama cannot be reached, the app falls back to deterministic graph-aware retrieval automatically.

## Docker Compose

```bash
docker compose up --build -d
docker compose exec ollama ollama pull qwen2.5-coder:3b
```

Then open `http://localhost:8000`. The compose stack mounts this repository read-only at `/workspace/example`, so you can index `/workspace/example` immediately from the UI.

## API examples

```bash
curl -X POST http://localhost:8000/api/repositories/local \
  -H 'Content-Type: application/json' \
  -d '{"path":"/workspace/example"}'

curl -X POST http://localhost:8000/api/repositories/<repo-id>/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Where is indexing implemented?"}'
```

Clone a remote repository:

```bash
curl -X POST http://localhost:8000/api/repositories/clone \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://github.com/OWNER/REPO.git"}'
```

## Production notes

This project is intended to be self-hosted. For internet-facing deployment, place it behind authentication and a reverse proxy because indexing local paths and cloning repositories are privileged operations by design. Keep the workspace on a persistent volume. For private Git repositories, configure Git credentials/SSH in the runtime rather than embedding credentials in URLs.

## Current scope

The semantic parser is intentionally Python-first. The architecture isolates indexing and retrieval so tree-sitter parsers or language-specific indexers can be added later without replacing the API, UI, workspace, or synthesis layers.

## Quality checks

```bash
ruff check app.py code_assistant tests
ruff format --check app.py code_assistant tests
pytest -q
python -m code_assistant.cli --workspace .tmp-assistant index tests/fixture
python -m pip wheel --no-deps --wheel-dir dist .
```

GitHub Actions runs these checks on Python 3.11 and 3.12, builds an installable wheel,
and verifies the production Docker image on every pull request and push to `main`.

## License

MIT.

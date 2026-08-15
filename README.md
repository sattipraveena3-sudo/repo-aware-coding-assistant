# Repo-Aware Coding Assistant

I built this self-hosted code-intelligence tool to retrieve program structure rather than arbitrary text windows. Python's AST defines function, method, and class chunks; a call graph links callees; lexical retrieval and graph expansion return grounded file and line references. The CLI is primary, with a small FastAPI wrapper.

```bash
pip install -r requirements.txt
python -m code_assistant.cli index .
python -m code_assistant.cli ask "where is retrieve used?"
pytest
```

Example self-indexing output includes `code_assistant/core.py` symbols such as `index_repo`, `retrieve`, and their call-linked dependencies. Suggested changes are emitted in unified-diff form. The deterministic answer layer works offline; Docker Compose includes Ollama so a local `qwen2.5-coder` synthesis layer can be connected without changing retrieval.

This differs from naive RAG by respecting AST boundaries, recording symbol calls, and expanding retrieved nodes through code dependencies. Current limitations are Python-only parsing, simple name resolution, lexical rather than learned embeddings, and no automatic patch application. Next steps are tree-sitter languages, local dense embeddings, repository-aware reranking, Ollama synthesis, git-aware diffs, and sandboxed tests.

Suggested commits: `set up CLI`, `add AST chunker`, `build call graph`, `add hybrid retriever`, `add grounded references`, `format diff suggestions`, `add FastAPI wrapper`, `add self-indexing demo`, `add tests`, `add Ollama Compose`, `write README`.

```bash
git init -b main
git add code_assistant && git commit -m "add AST-aware indexing and retrieval"
git add app.py tests && git commit -m "add API and retrieval tests"
git add Dockerfile docker-compose.yml && git commit -m "add self-hosted runtime"
git add README.md && git commit -m "document self-indexing workflow"
gh repo create repo-aware-coding-assistant --public --source=. --remote=origin
git push -u origin main
```

MIT licensed. The tool never sends repository code to a paid service by default.

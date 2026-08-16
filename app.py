from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from code_assistant.core import answer, index_repo, load_index, save_index

app = FastAPI(
    title="Repo-Aware Coding Assistant",
    version="1.0.0",
    description="AST-aware repository indexing and grounded code retrieval for Python projects.",
)


class IndexRequest(BaseModel):
    repo_path: str = Field(default=".", description="Local repository path visible to the service")
    index_path: str = Field(default=".code-index.json", description="Where to persist the generated index")


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    index_path: str = ".code-index.json"
    top_k: int = Field(default=6, ge=1, le=20)


@app.get("/")
def root():
    return {
        "name": "Repo-Aware Coding Assistant",
        "docs": "/docs",
        "health": "/health",
        "index": "POST /index",
        "ask": "POST /ask",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/index")
def build_index(request: IndexRequest):
    try:
        index = index_repo(Path(request.repo_path))
        save_index(index, request.index_path)
        return {
            "status": "indexed",
            "index_path": request.index_path,
            "files_indexed": index["files_indexed"],
            "symbols_indexed": len(index["chunks"]),
            "files_skipped": index["files_skipped"],
        }
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/ask")
def ask(request: AskRequest):
    try:
        return answer(load_index(request.index_path), request.question, k=request.top_k)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

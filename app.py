from __future__ import annotations

import os
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from code_assistant.llm import answer_with_optional_ollama
from code_assistant.workspace import Workspace

WORKSPACE_DIR = os.getenv('REPO_ASSISTANT_WORKSPACE', '.repo_assistant')
workspace = Workspace(WORKSPACE_DIR)
app = FastAPI(title='Repo-Aware Coding Assistant', version='1.0.0', description='Self-hosted repository intelligence with AST retrieval and optional Ollama synthesis.')


class IndexLocalRequest(BaseModel):
    path: str
    name: str | None = None


class CloneRequest(BaseModel):
    url: str
    name: str | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    model: str | None = None


@app.get('/api/health')
def health():
    return {'status': 'ok', 'version': app.version, 'workspace': str(workspace.root)}


@app.get('/api/repositories')
def repositories():
    return {'repositories': workspace.list()}


@app.post('/api/repositories/local')
def index_local(body: IndexLocalRequest):
    try:
        return workspace.index_local(body.path, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/api/repositories/clone')
def clone_repository(body: CloneRequest):
    try:
        return workspace.clone_and_index(body.url, body.name)
    except (ValueError, subprocess.SubprocessError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/api/repositories/{repo_id}/refresh')
def refresh(repo_id: str):
    try:
        return workspace.refresh(repo_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except subprocess.SubprocessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/api/repositories/{repo_id}/ask')
def ask(repo_id: str, body: AskRequest):
    try:
        index = workspace.load_repo_index(repo_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return answer_with_optional_ollama(index, body.question, model=body.model)


STATIC_DIR = Path(__file__).parent / 'static'
app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')


@app.get('/', include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / 'index.html')

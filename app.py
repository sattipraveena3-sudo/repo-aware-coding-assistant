from fastapi import FastAPI
from pydantic import BaseModel
from code_assistant.core import answer,load_index
app=FastAPI(title="Repo-Aware Coding Assistant")
class Ask(BaseModel): question:str; index_path:str=".code-index.json"
@app.get("/health")
def health(): return {"status":"ok"}
@app.post("/ask")
def ask(q:Ask): return answer(load_index(q.index_path),q.question)

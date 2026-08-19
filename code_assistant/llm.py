from __future__ import annotations

import json
import os
from urllib import error, request

from .core import build_context, deterministic_answer, references, retrieve


def answer_with_optional_ollama(
    index: dict, question: str, model: str | None = None, base_url: str | None = None
) -> dict:
    model = model or os.getenv("OLLAMA_MODEL", "")
    base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
    hits = retrieve(index, question)
    if not model or not hits:
        return deterministic_answer(index, question)
    prompt = (
        "You are a repository-aware coding assistant. Answer only from the supplied repository "
        "context. Be specific about files, symbols, behavior, risks, and concrete next steps. "
        "If evidence is insufficient, say so.\n\n"
        f"QUESTION:\n{question}\n\nREPOSITORY CONTEXT:\n{build_context(hits)}"
    )
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = request.Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = (data.get("response") or "").strip()
        if not text:
            return deterministic_answer(index, question)
        return {
            "answer": text,
            "references": references(hits),
            "context": hits,
            "mode": f"ollama:{model}",
        }
    except (error.URLError, TimeoutError, json.JSONDecodeError):
        result = deterministic_answer(index, question)
        result["warning"] = (
            "Ollama was unavailable, so the assistant fell back to deterministic repository "
            "retrieval."
        )
        return result

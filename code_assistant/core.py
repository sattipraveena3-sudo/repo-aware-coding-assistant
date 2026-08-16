import ast
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

IGNORED_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}


@dataclass
class Chunk:
    id: str
    path: str
    symbol: str
    kind: str
    start: int
    end: int
    code: str
    calls: list[str]
    docstring: str = ""


def _is_ignored(path: Path) -> bool:
    return any(part in IGNORED_DIRS or part.startswith(".") for part in path.parts)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def chunk_file(path: Path, root: Path) -> list[Chunk]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    lines = text.splitlines()
    result: list[Chunk] = []
    rel = str(path.relative_to(root))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            end = getattr(node, "end_lineno", node.lineno)
            calls = sorted(
                {
                    name
                    for call in ast.walk(node)
                    if isinstance(call, ast.Call)
                    for name in [_call_name(call)]
                    if name
                }
            )
            result.append(
                Chunk(
                    id=f"{rel}:{node.lineno}:{node.name}",
                    path=rel,
                    symbol=node.name,
                    kind=type(node).__name__,
                    start=node.lineno,
                    end=end,
                    code="\n".join(lines[node.lineno - 1 : end]),
                    calls=calls,
                    docstring=ast.get_docstring(node) or "",
                )
            )
    return result


def _python_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        rel = path.relative_to(root)
        if not _is_ignored(rel):
            yield path


def index_repo(root: Path) -> dict:
    root = root.expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Repository path does not exist or is not a directory: {root}")

    chunks: list[Chunk] = []
    skipped: list[str] = []
    files = list(_python_files(root))
    for path in files:
        try:
            chunks.extend(chunk_file(path, root))
        except (SyntaxError, UnicodeDecodeError, OSError):
            skipped.append(str(path.relative_to(root)))

    symbols: dict[str, list[str]] = defaultdict(list)
    by_id = {c.id: c for c in chunks}
    for chunk in chunks:
        symbols[chunk.symbol].append(chunk.id)

    edges: dict[str, list[str]] = {}
    reverse_edges: dict[str, list[str]] = defaultdict(list)
    for chunk in chunks:
        targets = sorted({target for call in chunk.calls for target in symbols.get(call, [])})
        edges[chunk.id] = targets
        for target in targets:
            reverse_edges[target].append(chunk.id)

    return {
        "version": 2,
        "root": str(root),
        "files_indexed": len(files) - len(skipped),
        "files_skipped": skipped,
        "chunks": [asdict(c) for c in chunks],
        "edges": edges,
        "reverse_edges": {k: sorted(v) for k, v in reverse_edges.items()},
        "symbols": {k: sorted(v) for k, v in symbols.items()},
    }


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z_][a-zA-Z0-9_]+", text.lower())


def retrieve(index: dict, question: str, k: int = 6) -> list[dict]:
    docs = index.get("chunks", [])
    if not docs:
        return []

    query = Counter(tokens(question))
    df = Counter(t for d in docs for t in set(tokens(f'{d["symbol"]} {d.get("docstring", "")} {d["code"]}')))
    scores: list[tuple[float, dict]] = []
    q_lower = question.lower()

    for doc in docs:
        haystack = f'{doc["symbol"]} {doc.get("docstring", "")} {doc["code"]}'
        tf = Counter(tokens(haystack))
        score = sum(
            query[t] * tf[t] * math.log((len(docs) + 1) / (df[t] + 1) + 1)
            for t in query
        )
        if doc["symbol"].lower() in q_lower:
            score += 6
        if doc["path"].lower() in q_lower:
            score += 3
        scores.append((score, doc))

    ranked = [doc for score, doc in sorted(scores, key=lambda item: item[0], reverse=True) if score > 0][:k]
    ids = {doc["id"] for doc in ranked}
    related = {
        related_id
        for chunk_id in list(ids)
        for related_id in index.get("edges", {}).get(chunk_id, []) + index.get("reverse_edges", {}).get(chunk_id, [])
    }
    return ranked + [doc for doc in docs if doc["id"] in related and doc["id"] not in ids][:3]


def _reference(hit: dict) -> str:
    return f'{hit["path"]}:{hit["start"]}-{hit["end"]} ({hit["symbol"]})'


def _relationship_summary(index: dict, hit: dict) -> list[str]:
    by_id = {c["id"]: c for c in index.get("chunks", [])}
    outgoing = [by_id[x]["symbol"] for x in index.get("edges", {}).get(hit["id"], []) if x in by_id]
    incoming = [by_id[x]["symbol"] for x in index.get("reverse_edges", {}).get(hit["id"], []) if x in by_id]
    details: list[str] = []
    if outgoing:
        details.append(f"calls {', '.join(outgoing[:5])}")
    if incoming:
        details.append(f"called by {', '.join(incoming[:5])}")
    return details


def answer(index: dict, question: str, k: int = 6) -> dict:
    question = question.strip()
    if not question:
        raise ValueError("Question cannot be empty")

    hits = retrieve(index, question, k=k)
    if not hits:
        return {
            "answer": "I could not find a matching Python symbol in the current repository index.",
            "references": [],
            "context": [],
            "suggested_diff": None,
        }

    lines = [f"I found {len(hits)} relevant code locations for: {question}"]
    for hit in hits[:5]:
        relationship = _relationship_summary(index, hit)
        suffix = f" — {'; '.join(relationship)}" if relationship else ""
        lines.append(f"- {_reference(hit)}{suffix}")

    primary = hits[0]
    symbol = primary["symbol"]
    suggestion = (
        f"Start with `{symbol}` in `{primary['path']}` and inspect the linked callers/callees before editing. "
        "The index can identify the relevant code, but it intentionally does not fabricate a patch without a concrete requested change."
    )
    lines.append(suggestion)

    return {
        "answer": "\n".join(lines),
        "references": [_reference(hit) for hit in hits],
        "context": hits,
        "suggested_diff": None,
    }


def save_index(index: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(index, indent=2), encoding="utf-8")


def load_index(path: str | Path) -> dict:
    index_path = Path(path)
    if not index_path.exists():
        raise FileNotFoundError(f"Index file not found: {index_path}. Run the index command first.")
    return json.loads(index_path.read_text(encoding="utf-8"))

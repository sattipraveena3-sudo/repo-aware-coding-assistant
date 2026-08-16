from __future__ import annotations

import ast
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

IGNORED_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'node_modules', 'dist', 'build', '.mypy_cache', '.pytest_cache'}


@dataclass
class Chunk:
    id: str
    path: str
    symbol: str
    qualified_name: str
    kind: str
    start: int
    end: int
    code: str
    calls: list[str]
    docstring: str = ''


def _is_ignored(path: Path) -> bool:
    return any(part in IGNORED_DIRS or part.startswith('.') for part in path.parts)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _walk_definitions(tree: ast.AST):
    def visit(node: ast.AST, parents: list[str]):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qn = '.'.join([*parents, child.name]) if parents else child.name
                yield child, qn
                yield from visit(child, [*parents, child.name])
            else:
                yield from visit(child, parents)
    yield from visit(tree, [])


def chunk_file(path: Path, root: Path) -> list[Chunk]:
    text = path.read_text(encoding='utf-8')
    tree = ast.parse(text)
    lines = text.splitlines()
    rel = path.relative_to(root).as_posix()
    chunks: list[Chunk] = []
    for node, qualified_name in _walk_definitions(tree):
        end = getattr(node, 'end_lineno', node.lineno)
        calls = sorted({name for call in ast.walk(node) if isinstance(call, ast.Call) for name in [_call_name(call)] if name})
        chunks.append(Chunk(id=f'{rel}:{node.lineno}:{qualified_name}', path=rel, symbol=node.name, qualified_name=qualified_name, kind=type(node).__name__, start=node.lineno, end=end, code='\n'.join(lines[node.lineno - 1:end]), calls=calls, docstring=ast.get_docstring(node) or ''))
    return chunks


def _python_files(root: Path) -> Iterable[Path]:
    for path in root.rglob('*.py'):
        if not _is_ignored(path.relative_to(root)):
            yield path


def index_repo(root: Path) -> dict:
    root = root.expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f'Repository path does not exist or is not a directory: {root}')
    chunks: list[Chunk] = []
    skipped: list[str] = []
    files = list(_python_files(root))
    for path in files:
        try:
            chunks.extend(chunk_file(path, root))
        except (SyntaxError, UnicodeDecodeError, OSError):
            skipped.append(path.relative_to(root).as_posix())
    symbols: dict[str, list[str]] = defaultdict(list)
    for chunk in chunks:
        symbols[chunk.symbol].append(chunk.id)
        symbols[chunk.qualified_name].append(chunk.id)
    edges: dict[str, list[str]] = {}
    reverse_edges: dict[str, list[str]] = defaultdict(list)
    for chunk in chunks:
        targets = sorted({target for call in chunk.calls for target in symbols.get(call, [])})
        edges[chunk.id] = targets
        for target in targets:
            reverse_edges[target].append(chunk.id)
    return {'version': 3, 'root': str(root), 'files_indexed': len(files) - len(skipped), 'files_skipped': skipped, 'chunks': [asdict(c) for c in chunks], 'edges': edges, 'reverse_edges': {k: sorted(v) for k, v in reverse_edges.items()}, 'symbols': {k: sorted(set(v)) for k, v in symbols.items()}}


def tokens(text: str) -> list[str]:
    return re.findall(r'[a-zA-Z_][a-zA-Z0-9_]+', text.lower())


def retrieve(index: dict, question: str, k: int = 8) -> list[dict]:
    docs = index.get('chunks', [])
    if not docs:
        return []
    query = Counter(tokens(question))
    df = Counter(t for d in docs for t in set(tokens(f"{d['qualified_name']} {d.get('docstring', '')} {d['code']}")))
    q_lower = question.lower()
    scored: list[tuple[float, dict]] = []
    for doc in docs:
        haystack = f"{doc['qualified_name']} {doc.get('docstring', '')} {doc['code']}"
        tf = Counter(tokens(haystack))
        score = sum(query[t] * tf[t] * math.log((len(docs) + 1) / (df[t] + 1) + 1) for t in query)
        if doc['symbol'].lower() in q_lower or doc['qualified_name'].lower() in q_lower:
            score += 8
        if doc['path'].lower() in q_lower:
            score += 4
        scored.append((score, doc))
    ranked = [d for s, d in sorted(scored, key=lambda x: x[0], reverse=True) if s > 0][:k]
    ids = {d['id'] for d in ranked}
    related = {rid for cid in list(ids) for rid in index.get('edges', {}).get(cid, []) + index.get('reverse_edges', {}).get(cid, [])}
    return ranked + [d for d in docs if d['id'] in related and d['id'] not in ids][:4]


def references(hits: list[dict]) -> list[str]:
    return [f"{h['path']}:{h['start']}-{h['end']} ({h['qualified_name']})" for h in hits]


def build_context(hits: list[dict], max_chars: int = 14000) -> str:
    blocks: list[str] = []
    used = 0
    for hit in hits:
        block = f"FILE: {hit['path']}\nSYMBOL: {hit['qualified_name']}\nLINES: {hit['start']}-{hit['end']}\n```python\n{hit['code']}\n```"
        if used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block)
    return '\n\n'.join(blocks)


def deterministic_answer(index: dict, question: str, k: int = 8) -> dict:
    hits = retrieve(index, question, k=k)
    if not hits:
        return {'answer': 'No matching Python symbols were found in this repository index.', 'references': [], 'context': [], 'mode': 'retrieval'}
    by_id = {c['id']: c for c in index.get('chunks', [])}
    lines = [f'Found {len(hits)} relevant code locations for: {question}']
    for hit in hits[:6]:
        outgoing = [by_id[x]['qualified_name'] for x in index.get('edges', {}).get(hit['id'], []) if x in by_id][:4]
        incoming = [by_id[x]['qualified_name'] for x in index.get('reverse_edges', {}).get(hit['id'], []) if x in by_id][:4]
        relation = []
        if outgoing:
            relation.append('calls ' + ', '.join(outgoing))
        if incoming:
            relation.append('called by ' + ', '.join(incoming))
        suffix = f" — {'; '.join(relation)}" if relation else ''
        lines.append(f"- {hit['path']}:{hit['start']}-{hit['end']} ({hit['qualified_name']}){suffix}")
    return {'answer': '\n'.join(lines), 'references': references(hits), 'context': hits, 'mode': 'retrieval'}


def save_index(index: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2), encoding='utf-8')


def load_index(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'Index file not found: {path}')
    return json.loads(path.read_text(encoding='utf-8'))

import ast, json, math, re
from collections import Counter,defaultdict
from dataclasses import asdict,dataclass
from pathlib import Path

@dataclass
class Chunk:
    id:str; path:str; symbol:str; kind:str; start:int; end:int; code:str; calls:list[str]

def chunk_file(path:Path,root:Path)->list[Chunk]:
    text=path.read_text(encoding="utf-8"); tree=ast.parse(text); lines=text.splitlines(); result=[]
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            calls=sorted({n.func.id if isinstance(n.func,ast.Name) else n.func.attr for n in ast.walk(node) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))})
            rel=str(path.relative_to(root)); result.append(Chunk(f"{rel}:{node.lineno}:{node.name}",rel,node.name,type(node).__name__,node.lineno,node.end_lineno,"\n".join(lines[node.lineno-1:node.end_lineno]),calls))
    return result

def index_repo(root:Path)->dict:
    chunks=[]
    for path in root.rglob("*.py"):
        if not any(part.startswith(".") or part in {"venv","__pycache__"} for part in path.parts):
            try: chunks.extend(chunk_file(path,root))
            except (SyntaxError,UnicodeDecodeError): pass
    symbols=defaultdict(list)
    for c in chunks: symbols[c.symbol].append(c.id)
    edges={c.id:sorted({target for call in c.calls for target in symbols.get(call,[])}) for c in chunks}
    return {"root":str(root.resolve()),"chunks":[asdict(c) for c in chunks],"edges":edges}

def tokens(text): return re.findall(r"[a-zA-Z_][a-zA-Z0-9_]+",text.lower())
def retrieve(index:dict,question:str,k=6)->list[dict]:
    docs=index["chunks"]; query=Counter(tokens(question)); df=Counter(t for d in docs for t in set(tokens(d["symbol"]+" "+d["code"])))
    scores=[]
    for d in docs:
        tf=Counter(tokens(d["symbol"]+" "+d["code"])); score=sum(query[t]*tf[t]*math.log((len(docs)+1)/(df[t]+1)+1) for t in query)
        if d["symbol"].lower() in question.lower(): score+=5
        scores.append((score,d))
    ranked=[d for s,d in sorted(scores,key=lambda x:x[0],reverse=True) if s>0][:k]; ids={d["id"] for d in ranked}
    related={x for i in list(ids) for x in index["edges"].get(i,[])}
    return ranked+[d for d in docs if d["id"] in related and d["id"] not in ids][:2]

def answer(index,question):
    hits=retrieve(index,question); refs=[f'{h["path"]}:{h["start"]}-{h["end"]} ({h["symbol"]})' for h in hits]
    return {"answer":"Relevant symbols are listed below. Inspect their dependency-linked implementations before changing behavior.","references":refs,"context":hits,"suggested_diff":"--- a/path.py\n+++ b/path.py\n@@\n-# existing behavior\n+# proposed change after reviewing retrieved context"}

def save_index(index,path): Path(path).write_text(json.dumps(index),encoding="utf-8")
def load_index(path): return json.loads(Path(path).read_text(encoding="utf-8"))

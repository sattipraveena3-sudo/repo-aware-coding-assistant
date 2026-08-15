from pathlib import Path
from code_assistant.core import chunk_file,index_repo,retrieve
ROOT=Path(__file__).parent/'fixture'
def test_ast_chunking():
    chunks=chunk_file(ROOT/'sample.py',ROOT); assert {c.symbol for c in chunks} >= {'load_value','normalize','Service','run'}
def test_dependency_graph():
    idx=index_repo(ROOT); load=next(c for c in idx['chunks'] if c['symbol']=='load_value'); assert any('normalize' in x for x in idx['edges'][load['id']])
def test_retrieval(): assert retrieve(index_repo(ROOT),'where is normalize used?')[0]['symbol']=='normalize'

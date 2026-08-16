from pathlib import Path
from code_assistant.core import chunk_file, index_repo, retrieve, deterministic_answer

ROOT = Path(__file__).parent / 'fixture'


def test_chunking_and_qualified_names():
    chunks = chunk_file(ROOT / 'sample.py', ROOT)
    names = {c.qualified_name for c in chunks}
    assert {'normalize', 'load_value', 'Service', 'Service.run'} <= names


def test_dependency_graph_and_reverse_edges():
    idx = index_repo(ROOT)
    load = next(c for c in idx['chunks'] if c['qualified_name'] == 'load_value')
    normalize = next(c for c in idx['chunks'] if c['qualified_name'] == 'normalize')
    assert normalize['id'] in idx['edges'][load['id']]
    assert load['id'] in idx['reverse_edges'][normalize['id']]


def test_retrieval_prefers_named_symbol():
    assert retrieve(index_repo(ROOT), 'where is normalize used?')[0]['symbol'] == 'normalize'


def test_deterministic_answer_is_grounded():
    result = deterministic_answer(index_repo(ROOT), 'where is normalize used?')
    assert result['references']
    assert 'sample.py' in result['answer']

from pathlib import Path
from code_assistant.workspace import Workspace

FIXTURE = Path(__file__).parent / 'fixture'


def test_workspace_index_list_refresh_and_load(tmp_path):
    ws = Workspace(tmp_path / 'ws')
    record = ws.index_local(FIXTURE)
    assert record['symbols'] >= 4
    assert ws.list()[0]['id'] == record['id']
    assert ws.load_repo_index(record['id'])['chunks']
    refreshed = ws.refresh(record['id'])
    assert refreshed['id'] == record['id']

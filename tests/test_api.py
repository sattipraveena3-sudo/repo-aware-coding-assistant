from pathlib import Path

from fastapi.testclient import TestClient

from code_assistant import api as api_app
from code_assistant.workspace import Workspace

FIXTURE = Path(__file__).parent / "fixture"


def test_end_to_end_api(tmp_path, monkeypatch):
    monkeypatch.setattr(api_app, "workspace", Workspace(tmp_path / "ws"))
    client = TestClient(api_app.app)
    assert client.get("/api/health").status_code == 200
    created = client.post("/api/repositories/local", json={"path": str(FIXTURE)}).json()
    repo_id = created["id"]
    answer = client.post(
        f"/api/repositories/{repo_id}/ask", json={"question": "where is normalize used?"}
    ).json()
    assert answer["references"]
    assert answer["mode"] == "retrieval"
    assert client.get("/").status_code == 200

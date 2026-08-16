from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_and_ask(tmp_path):
    index_path = tmp_path / "index.json"
    response = client.post(
        "/index",
        json={"repo_path": "tests/fixture", "index_path": str(index_path)},
    )
    assert response.status_code == 200
    assert response.json()["symbols_indexed"] > 0

    response = client.post(
        "/ask",
        json={"question": "where is normalize used?", "index_path": str(index_path)},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["references"]
    assert "normalize" in body["answer"]


def test_missing_index_returns_404(tmp_path):
    response = client.post(
        "/ask",
        json={"question": "where is normalize?", "index_path": str(tmp_path / "missing.json")},
    )
    assert response.status_code == 404

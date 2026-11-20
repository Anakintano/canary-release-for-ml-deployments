"""Unit tests. Run with: docker build --target test .   (or python -m pytest -q tests from the repo root)"""
import os

import pytest
from fastapi.testclient import TestClient

from ml import train
from ml.data import make_tickets
from scripts.canary_check import judge

BILLING = "I was charged twice for my Pro plan, please refund the payment"


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    out = tmp_path_factory.mktemp("model")
    train.main(["--n", "800", "--out", str(out)])
    os.environ["MODEL_DIR"] = str(out)
    from app import main  # imported here so it loads the model trained above
    return TestClient(main.app)


def test_data_is_deterministic():
    assert make_tickets(50, seed=3) == make_tickets(50, seed=3)
    assert set(make_tickets(200, seed=3)[1]) == {"billing", "technical", "account", "shipping"}


def test_predict(client):
    r = client.post("/predict", json={"text": BILLING})
    assert r.status_code == 200
    body = r.json()
    assert body["category"] == "billing"
    assert 0 < body["confidence"] <= 1
    assert body["version"] == open("VERSION").read().strip()


def test_empty_ticket_is_rejected(client):
    assert client.post("/predict", json={"text": ""}).status_code == 422


def test_page_health_and_metrics(client):
    assert 'id="ticket"' in client.get("/").text
    assert client.get("/healthz").json()["status"] == "ok"
    client.post("/predict", json={"text": BILLING})
    assert "tickets_requests_total{version=" in client.get("/metrics").text


def test_fast_tokenizer_breaks_serving(client, monkeypatch):
    # Demo 2 only works if the bad-release switch really hurts live traffic.
    good = client.post("/predict", json={"text": BILLING}).json()["confidence"]
    monkeypatch.setenv("TOKENIZER", "fast")
    bad = client.post("/predict", json={"text": BILLING}).json()["confidence"]
    assert bad < good
    assert client.post("/predict", json={"text": "Charged ?499 twice ??"}).status_code == 500


def test_canary_judge():
    stable = {"requests": 900, "error_rate": 0.0, "p95": 0.02, "confidence": 0.8}
    assert judge(stable, dict(stable, requests=100)) == []
    failed = judge(stable, {"requests": 100, "error_rate": 0.2, "p95": 0.02, "confidence": 0.3})
    assert len(failed) == 2 and "error rate" in failed[0] and "confidence" in failed[1]
    assert judge(stable, {"requests": 100, "error_rate": None, "p95": 0.5, "confidence": 0.8})[0].startswith("p95")

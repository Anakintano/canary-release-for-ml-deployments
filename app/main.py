"""Ticket classifier API: POST /predict, GET /metrics (Prometheus), GET /healthz, demo page at /."""
import os
import time
from pathlib import Path

import joblib
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

from ml.train import clean

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "VERSION").read_text().strip()
MODEL = joblib.load(Path(os.getenv("MODEL_DIR", ROOT / "model")) / "model.joblib")

REQUESTS = Counter("tickets_requests", "Prediction requests", ["version"])
ERRORS = Counter("tickets_errors", "Prediction requests that failed with HTTP 500", ["version"])
LATENCY = Histogram("tickets_request_latency_seconds", "Prediction latency", ["version"])
CONFIDENCE = Histogram(
    "tickets_prediction_confidence", "Probability of the predicted category", ["version", "category"],
    buckets=[i / 10 for i in range(1, 11)],
)
# Export zeros at startup so error-rate queries work before the first error happens.
REQUESTS.labels(VERSION)
ERRORS.labels(VERSION)

app = FastAPI(title="Ticket classifier")


class Ticket(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


def preprocess(text):
    if os.getenv("TOKENIZER") == "fast":
        # Failure demo 2, a deliberate training/serving skew: this "fast" tokenizer upper-cases and
        # assumes ASCII, but the model was trained on clean() output. Most words miss the vocabulary,
        # so confidence collapses, and non-ASCII tickets raise UnicodeEncodeError (HTTP 500).
        return " ".join(text.encode("ascii").decode().upper().split())
    return clean(text)


@app.get("/")
def page():
    return FileResponse(ROOT / "app" / "index.html")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "version": VERSION}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict")
def predict(ticket: Ticket):
    REQUESTS.labels(VERSION).inc()
    start = time.perf_counter()
    try:
        probs = MODEL.predict_proba([preprocess(ticket.text)])[0]
    except Exception:
        ERRORS.labels(VERSION).inc()
        raise HTTPException(500, f"prediction failed in model {VERSION}")
    finally:
        LATENCY.labels(VERSION).observe(time.perf_counter() - start)
    best = int(probs.argmax())
    category, confidence = str(MODEL.classes_[best]), float(probs[best])
    CONFIDENCE.labels(VERSION, category).observe(confidence)
    return {
        "category": category,
        "confidence": round(confidence, 4),
        "version": VERSION,
        "scores": {str(c): round(float(p), 4) for c, p in zip(MODEL.classes_, probs)},
    }

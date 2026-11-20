"""Train the ticket classifier and write <out>/model.joblib and <out>/metrics.json.

Usage: python -m ml.train [--degrade] [--n 4000] [--out model]
"""
import argparse
import json
import random
import re
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from ml.data import make_tickets

HOLDOUT_SEED = 999  # fixed held-out set, so accuracy is comparable across releases


def clean(text):
    """Preprocessing the model is trained on: lower-case, keep only a-z / 0-9 words."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=4000, help="training rows")
    p.add_argument("--out", default="model")
    p.add_argument("--degrade", action="store_true", help="failure demo 1: 40 rows with shuffled labels")
    args = p.parse_args(argv)

    texts, labels = make_tickets(args.n, seed=1)
    if args.degrade:
        texts, labels = texts[:40], random.Random(0).sample(labels[:40], 40)

    model = make_pipeline(
        # Input is already clean()ed, so the vectorizer does not lower-case again.
        # This also means serving must use clean() too (see demo 2 in app/main.py).
        TfidfVectorizer(lowercase=False, ngram_range=(1, 2), min_df=2, sublinear_tf=True),
        LogisticRegression(max_iter=1000),
    )
    model.fit([clean(t) for t in texts], labels)

    test_texts, test_labels = make_tickets(1000, seed=HOLDOUT_SEED)
    accuracy = round(model.score([clean(t) for t in test_texts], test_labels), 4)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out / "model.joblib")
    metrics = {"accuracy": accuracy, "train_rows": len(texts), "test_rows": len(test_texts)}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(metrics)
    return metrics


if __name__ == "__main__":
    main()

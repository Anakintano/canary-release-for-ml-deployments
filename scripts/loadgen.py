"""Send realistic ticket traffic to the ingress so Prometheus has something to measure.

Usage: python -m scripts.loadgen BASE_URL [REQUESTS_PER_SECOND]
Runs in the cluster as the `loadgen` Deployment (k8s/loadgen.yaml). Stdlib only.
"""
import json
import random
import sys
import time
import urllib.request

from ml.data import make_tickets

url = sys.argv[1].rstrip("/") + "/predict"
rps = float(sys.argv[2]) if len(sys.argv) > 2 else 8
texts, _ = make_tickets(2000, seed=7)
sent = failed = 0
print(f"sending ~{rps} req/s to {url}", flush=True)
while True:
    body = json.dumps({"text": random.choice(texts)}).encode()
    request = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(request, timeout=5).read()
    except Exception:  # errors are what the canary check measures; keep sending
        failed += 1
    sent += 1
    if sent % 500 == 0:
        print(f"sent={sent} failed={failed}", flush=True)
    time.sleep(1 / rps)

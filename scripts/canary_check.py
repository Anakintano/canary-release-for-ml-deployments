"""Canary analysis: compare canary to stable using live Prometheus metrics.

Usage: python scripts/canary_check.py PROMETHEUS_URL
Exit 0 = promote, exit 1 = roll back. Jenkins acts on the exit code.
"""
import json
import sys
import time
import urllib.parse
import urllib.request

# --- thresholds: the only knobs of the canary analysis ---
WATCH_SECONDS = 300            # watch this long before promoting
STEP_SECONDS = 20              # check this often
MIN_CANARY_REQUESTS = 50       # do not judge on fewer canary requests than this
MAX_ERROR_RATE_INCREASE = 0.02 # canary error rate may be at most 2 points above stable
MAX_P95_INCREASE_S = 0.10      # canary p95 latency may be at most 100 ms above stable
MIN_CONFIDENCE_RATIO = 0.85    # canary mean confidence must be at least 85% of stable's


def query(prom, promql):
    url = f"{prom}/api/v1/query?" + urllib.parse.urlencode({"query": promql})
    with urllib.request.urlopen(url, timeout=10) as resp:
        result = json.load(resp)["data"]["result"]
    if not result:
        return None
    value = float(result[0]["value"][1])
    return None if value != value else value  # NaN (0/0) -> None


def snapshot(prom, track, window):
    s, w = f'track="{track}"', f"{window}s"
    return {
        "requests": query(prom, f"sum(increase(tickets_requests_total{{{s}}}[{w}]))"),
        "error_rate": query(prom, f"sum(rate(tickets_errors_total{{{s}}}[{w}])) / sum(rate(tickets_requests_total{{{s}}}[{w}]))"),
        "p95": query(prom, f"histogram_quantile(0.95, sum by (le) (rate(tickets_request_latency_seconds_bucket{{{s}}}[{w}])))"),
        "confidence": query(prom, f"sum(rate(tickets_prediction_confidence_sum{{{s}}}[{w}])) / sum(rate(tickets_prediction_confidence_count{{{s}}}[{w}]))"),
    }


def judge(stable, canary):
    """Return the list of failed checks; empty means the canary looks healthy. Missing values count as 0."""
    st = {k: v or 0 for k, v in stable.items()}
    ca = {k: v or 0 for k, v in canary.items()}
    failed = []
    if ca["error_rate"] > st["error_rate"] + MAX_ERROR_RATE_INCREASE:
        failed.append(f"error rate {ca['error_rate']:.1%} vs stable {st['error_rate']:.1%}")
    if ca["p95"] > st["p95"] + MAX_P95_INCREASE_S:
        failed.append(f"p95 latency {ca['p95'] * 1000:.0f} ms vs stable {st['p95'] * 1000:.0f} ms")
    if ca["confidence"] < st["confidence"] * MIN_CONFIDENCE_RATIO:
        failed.append(f"mean confidence {ca['confidence']:.2f} vs stable {st['confidence']:.2f}")
    return failed


def main(prom):
    start = time.time()
    while True:
        time.sleep(STEP_SECONDS)
        elapsed = int(time.time() - start)
        window = max(30, elapsed)
        stable, canary = snapshot(prom, "stable", window), snapshot(prom, "canary", window)
        print(f"[{elapsed:>3}s] stable={json.dumps(stable)} canary={json.dumps(canary)}", flush=True)
        enough = (canary["requests"] or 0) >= MIN_CANARY_REQUESTS
        failed = judge(stable, canary) if enough else []
        if failed:
            print(f"ROLLBACK after {elapsed}s: " + "; ".join(failed))
            return 1
        if elapsed >= WATCH_SECONDS:
            if not enough:
                print(f"ROLLBACK: only {canary['requests']} canary requests in {elapsed}s, not enough to judge")
                return 1
            print(f"PROMOTE: canary healthy for {elapsed}s")
            return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1].rstrip("/")))

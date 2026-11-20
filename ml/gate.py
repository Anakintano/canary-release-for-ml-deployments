"""Accuracy gate: exit 1 if the new model is less accurate than the one in the running stable image.

Usage: python ml/gate.py NEW_METRICS.json STABLE_METRICS.json
"""
import json
import sys

new, stable = (json.load(open(path))["accuracy"] for path in sys.argv[1:3])
passed = new >= stable
print(f"accuracy gate: new={new:.4f} stable={stable:.4f} -> {'PASS' if passed else 'FAIL'}")
sys.exit(0 if passed else 1)

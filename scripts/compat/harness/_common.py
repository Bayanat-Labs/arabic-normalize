# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Shared JSONL loop for oracle harnesses. Reads {"id", "text", "pipeline"} lines on stdin and writes
{"id", "pipeline", "output", "error"} lines on stdout. Each harness runs in its own venv as a subprocess."""
import json
import sys


def run(pipelines):
    for line in sys.stdin:
        rec = json.loads(line)
        out = {"id": rec["id"], "pipeline": rec["pipeline"], "output": None, "error": None}
        try:
            out["output"] = pipelines[rec["pipeline"]](rec["text"])
        except Exception as exc:  # recorded, never fatal
            out["error"] = "%s: %s" % (type(exc).__name__, exc)
        sys.stdout.write(json.dumps(out, ensure_ascii=True) + "\n")
    sys.stdout.flush()

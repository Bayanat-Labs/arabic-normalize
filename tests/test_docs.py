# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Generated documentation (policy cards, README sections, CLAIMS.md) matches the released files."""
import os
import subprocess
import sys

from conftest import ROOT


def test_generated_docs_up_to_date():
    pytest_dir = os.path.dirname(os.path.abspath(__file__))
    env = dict(os.environ)
    env["PYTHONPATH"] = pytest_dir + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "make_docs.py"), "--check"],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stdout + r.stderr

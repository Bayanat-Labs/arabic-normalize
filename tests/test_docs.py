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


def test_fixture_readme_counts_match_the_fixture_files():
    """tests/fixtures/README.md states record and family counts; they must match the files."""
    import re
    from conftest import FIXTURES, fixtures
    with open(os.path.join(FIXTURES, "README.md"), encoding="utf-8") as f:
        text = f.read()
    for split in ("dev", "acceptance", "rejected"):
        m = re.search(r"^\| %s \| [^|]+ \| (\d+) \|([^|]*)\|" % split, text, re.M)
        assert m, split
        recs = fixtures(split)
        assert int(m.group(1)) == len(recs), split
        fam = re.search(r"across (\d+) families", m.group(2))
        if fam:
            assert int(fam.group(1)) == len({r["family"] for r in recs}), split

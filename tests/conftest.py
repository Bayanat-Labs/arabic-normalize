# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
import json
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIXTURES = os.path.join(HERE, "fixtures")
UCD_DIR = os.path.join(ROOT, "ucd", "18.0.0")


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def fixtures(split):
    name = {"dev": "dev/dev.jsonl", "acceptance": "acceptance/acceptance.jsonl", "rejected": "rejected/rejected.jsonl"}[split]
    return load_jsonl(os.path.join(FIXTURES, name))


@pytest.fixture(scope="session")
def jsonschema_mod():
    return pytest.importorskip("jsonschema")

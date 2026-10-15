#!/usr/bin/env python3
# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Run other Arabic normalisers (oracles) on the 80 pilot fixtures and write agreement tables to docs/compat/.

Each oracle runs in its own virtual environment, as a subprocess, through a small harness that exchanges JSON lines
on stdin and stdout. Nothing from an oracle is imported by this script or by the arabic-normalize package.

Harnesses: scripts/compat/harness/{camel,tnkeeh,whisper}_harness.py (the tools are MIT-licensed). No PyArabic
harness is included, because PyArabic is GPL: to run it, write one on the model of the others and pass it with
--harness pyarabic=PATH (it needs _common.py from scripts/compat/harness/ next to it). An oracle whose venv or
harness is missing is skipped.

Set up the venvs (versions as recorded in docs/compat/agreement.json), for example:
    uv venv compat/oracles/camel/.venv && VIRTUAL_ENV=compat/oracles/camel/.venv uv pip install --no-deps \
        camel-tools==1.6.0 emoji==2.16.0 six==1.17.0
Then:
    python -I scripts/compat/compare.py [--oracles-dir compat/oracles] [--harness pyarabic=/path/pyarabic_harness.py]
"""
import argparse
import collections
import datetime
import difflib
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HARNESS_DIR = os.path.join(REPO, "scripts", "compat", "harness")
OUT_DOCS = os.path.join(REPO, "docs", "compat")
ORA = os.path.join(REPO, "compat", "oracles")  # set by --oracles-dir; venvs are not committed
RUNS = os.path.join(REPO, "compat", "runs")  # set by --runs-dir; raw oracle outputs, not committed
HARNESS = {}  # oracle name -> harness path, filled in main()
sys.path.insert(0, os.path.join(REPO, "src"))

from arabic_normalize import normalize, __version__  # noqa: E402
from arabic_normalize import _ucd as U  # noqa: E402
from arabic_normalize import engine as E  # noqa: E402

POLICIES = ["bayanat-norm-v1", "asr-eval-v1", "raw-safe-v1"]

# Single-feature probe strings (authored here) run through every pipeline: a behaviour fingerprint.
PROBES = [
    ("alef maqsura", "ى"), ("alef variants", "أإآٱ"), ("taa marbuta", "ة"),
    ("hamza carriers", "ؤئ"), ("fatha on a letter", "كَت"),
    ("superscript alef", "هٰذا"), ("tatweel", "بـب"),
    ("Arabic-Indic digits", "١٢"), ("lam-alef ligature", "ﻻ"), ("U+FDFA", "ﷺ"),
    ("ZWNJ between joiners", "ب‌ب"), ("Arabic comma", "ب، ب"),
    ("Latin capital", "AB"),
]

ORACLES = {
    "camel": {"label": "CAMeL Tools 1.6.0", "licence": "MIT", "pipelines": ["camel-nfc", "camel-norm", "camel-asr"],
              "analogue": {"raw-safe-v1": "camel-nfc", "bayanat-norm-v1": "camel-norm", "asr-eval-v1": "camel-asr"}},
    "tnkeeh": {"label": "tnkeeh 0.0.9", "licence": "MIT", "pipelines": ["tnkeeh-default", "tnkeeh-norm", "tnkeeh-asr"],
               "analogue": {"raw-safe-v1": "tnkeeh-default", "bayanat-norm-v1": "tnkeeh-norm",
                            "asr-eval-v1": "tnkeeh-asr"}},
    "whisper": {"label": "Whisper BasicTextNormalizer (whisper-normalizer 0.1.15)", "licence": "MIT",
                "pipelines": ["whisper-basic", "whisper-basic-rd"], "analogue": {"asr-eval-v1": "whisper-basic"}},
    "pyarabic": {"label": "PyArabic 0.6.15 (subprocess only)", "licence": "GPL", "pipelines":
                 ["pyarabic-hamza", "pyarabic-norm", "pyarabic-asr"],
                 "analogue": {"bayanat-norm-v1": "pyarabic-norm", "asr-eval-v1": "pyarabic-asr"}},
}

PIPELINE_DOC = {
    "camel-nfc": "`normalize_unicode(s, compatibility=False)` (NFC)",
    "camel-norm": "`normalize_unicode(s)` (NFKC plus two ligature fixes) → `dediac_ar` → `normalize_alef_ar` → "
                  "`normalize_alef_maksura_ar`",
    "camel-asr": "camel-norm → `normalize_teh_marbuta_ar`",
    "tnkeeh-default": "`Tnkeeh().clean_raw_text(s)` with every option off (the tool still pads non-letters with "
                      "spaces and squeezes runs of spaces)",
    "tnkeeh-norm": "`Tnkeeh(normalize=True, remove_diacritics=True, remove_tatweel=True).clean_raw_text(s)`",
    "tnkeeh-asr": "tnkeeh-norm options plus `remove_special_chars=True`",
    "whisper-basic": "`BasicTextNormalizer()(s)` (the default Whisper basic normaliser)",
    "whisper-basic-rd": "`BasicTextNormalizer(remove_diacritics=True)(s)`",
    "pyarabic-hamza": "`strip_tashkeel` → `strip_tatweel` → `normalize_hamza` (default method) → `normalize_ligature` "
                      "(the composition planned for compat-pyarabic-v1)",
    "pyarabic-norm": "`normalize_ligature` → `strip_diacritics` → `strip_tatweel` → `normalize_alef`",
    "pyarabic-asr": "pyarabic-norm → `normalize_teh`",
}

# ---------------------------------------------------------------- divergence classes (pinned UCD 18.0.0)
CLASS_ORDER = ["whitespace", "punctuation", "harakat", "superscript_alef", "quranic_marks", "tatweel", "alef",
               "hamza", "alef_maqsura_yeh", "taa_marbuta_heh", "digits", "presentation_forms", "honorific",
               "invisible_controls", "rejected_code_points", "latin", "symbols", "other_marks", "other_arabic",
               "other"]
INVISIBLE = frozenset(E.BIDI | {E.ZWSP, E.ZWNJ, E.ZWJ, E.BOM} | E.FORMAT_CONTROLS)


def char_class(ch):
    cp = ord(ch)
    gc = U.general_category(cp)
    if cp in U.WHITE_SPACE:
        return "whitespace"
    if E.REJECT_RE.match(ch):
        return "rejected_code_points"
    if cp in INVISIBLE:
        return "invisible_controls"
    if cp in E.HARAKAT:
        return "harakat"
    if cp == 0x0670:
        return "superscript_alef"
    if cp in E.QURANIC:
        return "quranic_marks"
    if cp == 0x0640:
        return "tatweel"
    if cp in (0x0622, 0x0623, 0x0625, 0x0671, 0x0627):
        return "alef"
    if cp in (0x0621, 0x0624, 0x0626, 0x0654, 0x0655):
        return "hamza"
    if cp in (0x0649, 0x064A):
        return "alef_maqsura_yeh"
    if cp in (0x0629, 0x0647):
        return "taa_marbuta_heh"
    if cp in E.HONORIFIC:
        return "honorific"
    if cp in E.PF:
        return "presentation_forms"
    if gc == "Nd":
        return "digits"
    if gc.startswith("P"):
        return "punctuation"
    if gc.startswith("S"):
        return "symbols"
    if cp in U.SCRIPT_LATIN:
        return "latin"
    if gc.startswith("M"):
        return "other_marks"
    if cp in U.SCRIPT_ARABIC:
        return "other_arabic"
    return "other"


def divergence(ours, theirs):
    sm = difflib.SequenceMatcher(None, ours, theirs, autojunk=False)
    classes = set()
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        for ch in ours[i1:i2] + theirs[j1:j2]:
            classes.add(char_class(ch))
    return [c for c in CLASS_ORDER if c in classes]


def squeeze_ws(s):
    return " ".join(s.split())


def squeeze_ws_punct(s):
    return squeeze_ws("".join(" " if U.general_category(ord(c)).startswith("P") else c for c in s))


def esc(s):
    return "".join(c if 0x20 < ord(c) < 0x7F and c not in "|\\`" else "\\u%04x" % ord(c) if ord(c) < 0x10000
                   else "\\U%08x" % ord(c) for c in s)


# ---------------------------------------------------------------- run
def load_fixtures():
    rows = []
    for split in ("dev", "acceptance"):
        with open(os.path.join(REPO, "tests", "fixtures", split, split + ".jsonl"), encoding="utf-8") as f:
            rows += [json.loads(line) for line in f if line.strip()]
    return rows


def run_oracle(name, fixtures):
    spec = ORACLES[name]
    py = os.path.join(ORA, name, ".venv", "bin", "python")
    harness = HARNESS[name]
    items = [(fx["fixture_id"], fx["input"]) for fx in fixtures] + [("probe-%02d" % i, t)
                                                                     for i, (_, t) in enumerate(PROBES)]
    lines = [json.dumps({"id": i, "text": t, "pipeline": p}, ensure_ascii=True)
             for i, t in items for p in spec["pipelines"]]
    proc = subprocess.run([py, "-I", "-W", "ignore", harness], input="\n".join(lines) + "\n", capture_output=True,
                          text=True, cwd=RUNS, timeout=600, env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"})
    if proc.returncode != 0:
        raise SystemExit("%s harness failed: %s" % (name, proc.stderr[-2000:]))
    out = {}
    for line in proc.stdout.splitlines():
        r = json.loads(line)
        out[(r["id"], r["pipeline"])] = r
    with open(os.path.join(RUNS, name + "_fixtures.jsonl"), "w", encoding="utf-8") as f:
        for k in sorted(out):
            f.write(json.dumps(out[k], ensure_ascii=True) + "\n")
    return out


def oracle_versions():
    info = {}
    for name in ORACLES:
        py = os.path.join(ORA, name, ".venv", "bin", "python")
        v = subprocess.run([py, "-I", "-c", "import sys,unicodedata;print(sys.version.split()[0], "
                            "unicodedata.unidata_version)"], capture_output=True, text=True, cwd=RUNS).stdout.split()
        frz = subprocess.run(["uv", "pip", "freeze"], capture_output=True, text=True, cwd=RUNS,
                             env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                                  "VIRTUAL_ENV": os.path.join(ORA, name, ".venv")}).stdout.split()
        info[name] = {"python": v[0], "unicodedata": v[1], "freeze": frz}
    return info


def main():
    global ORA, RUNS
    ap = argparse.ArgumentParser()
    ap.add_argument("--oracles-dir", default=ORA, help="directory holding <oracle>/.venv for each oracle")
    ap.add_argument("--runs-dir", default=RUNS, help="where raw oracle outputs are written")
    ap.add_argument("--harness", action="append", default=[], metavar="NAME=PATH",
                    help="harness for an oracle not shipped here (pyarabic)")
    a = ap.parse_args()
    ORA, RUNS = os.path.abspath(a.oracles_dir), os.path.abspath(a.runs_dir)
    for name in ORACLES:
        HARNESS[name] = os.path.join(HARNESS_DIR, name + "_harness.py")
    for item in a.harness:
        name, _, path = item.partition("=")
        HARNESS[name] = os.path.abspath(path)
    for name in list(ORACLES):
        if not (os.path.exists(HARNESS[name]) and os.path.exists(os.path.join(ORA, name, ".venv", "bin", "python"))):
            print("skipping %s: harness or venv not found" % name, file=sys.stderr)
            del ORACLES[name]
    os.makedirs(OUT_DOCS, exist_ok=True)
    os.makedirs(RUNS, exist_ok=True)
    fixtures = load_fixtures()
    assert len(fixtures) == 80
    ours = {(fx["fixture_id"], p): normalize(fx["input"], p) for fx in fixtures for p in POLICIES}
    for fx in fixtures:  # sanity: the engine passes every fixture
        assert ours[(fx["fixture_id"], fx["policy_id"])] == fx["expected_output"], fx["fixture_id"]
    results = {name: run_oracle(name, fixtures) for name in ORACLES}
    versions = oracle_versions()

    errors = {name: sum(1 for r in res.values() if r["error"]) for name, res in results.items()}

    # Per-fixture agreement against each oracle's designated analogue of the fixture's own policy.
    per_fixture = []
    summary = collections.OrderedDict()
    div_counter = {name: collections.Counter() for name in ORACLES}
    for fx in fixtures:
        fid, pol = fx["fixture_id"], fx["policy_id"]
        row = {"fixture_id": fid, "split": fx["split"], "family": fx["family"], "policy_id": pol,
               "input_escaped": fx["input_escaped"], "ours": esc(fx["expected_output"]), "oracles": {}}
        for name, spec in ORACLES.items():
            pipe = spec["analogue"].get(pol)
            if pipe is None:
                row["oracles"][name] = {"pipeline": None}
                continue
            r = results[name][(fid, pipe)]
            theirs = r["output"]
            cell = {"pipeline": pipe, "error": r["error"]}
            if theirs is None:
                cell.update({"exact": False, "ws": False, "ws_punct": False, "classes": ["error"]})
            else:
                exact = theirs == fx["expected_output"]
                cell.update({"exact": exact, "ws": squeeze_ws(theirs) == squeeze_ws(fx["expected_output"]),
                             "ws_punct": squeeze_ws_punct(theirs) == squeeze_ws_punct(fx["expected_output"]),
                             "classes": [] if exact else divergence(fx["expected_output"], theirs),
                             "output_escaped": esc(theirs)})
            for c in cell["classes"]:
                div_counter[name][c] += 1
            row["oracles"][name] = cell
            s = summary.setdefault((name, pol), {"n": 0, "exact": 0, "ws": 0, "ws_punct": 0})
            s["n"] += 1
            s["exact"] += cell["exact"]
            s["ws"] += cell["ws"]
            s["ws_punct"] += cell["ws_punct"]
        per_fixture.append(row)

    # Full matrix: every oracle pipeline against every policy, all 80 inputs.
    matrix = collections.OrderedDict()
    for name, spec in ORACLES.items():
        for pipe in spec["pipelines"]:
            for pol in POLICIES:
                m = {"exact": 0, "ws": 0, "ws_punct": 0}
                for fx in fixtures:
                    theirs = results[name][(fx["fixture_id"], pipe)]["output"]
                    o = ours[(fx["fixture_id"], pol)]
                    if theirs is None:
                        continue
                    m["exact"] += theirs == o
                    m["ws"] += squeeze_ws(theirs) == squeeze_ws(o)
                    m["ws_punct"] += squeeze_ws_punct(theirs) == squeeze_ws_punct(o)
                matrix[(pipe, pol)] = m

    # Behaviour probes computed from the same runs (no number is typed in).
    has_harakat = [fx for fx in fixtures if any(ord(c) in E.HARAKAT for c in fx["input"])]
    wb_split = sum(1 for fx in has_harakat
                   if len(results["whisper"][(fx["fixture_id"], "whisper-basic")]["output"].split())
                   > len(normalize(fx["input"], "asr-eval-v1").split()))
    honor = [fx for fx in fixtures if any(ord(c) in (0xFDFA, 0xFDF2) for c in fx["input"])]
    camel_honor_expanded = sum(1 for fx in honor
                               if len(results["camel"][(fx["fixture_id"], "camel-norm")]["output"])
                               > len(fx["input"]))
    probes = {
        "fixtures_with_harakat": len(has_harakat),
        "whisper_basic_more_tokens_than_asr_eval_on_harakat_fixtures": wb_split,
        "fixtures_with_U+FDFA_or_U+FDF2": len(honor),
        "camel_norm_expanded_honorific_ligature": camel_honor_expanded,
    }

    today = datetime.date.today().isoformat()
    data = {"generated": today, "arabic_normalize_version": __version__, "unicode_version": U.UNICODE_VERSION,
            "oracles": {n: {"label": s["label"], "licence": s["licence"], "pipelines": s["pipelines"],
                            "analogue": s["analogue"], "env": versions[n], "harness_errors": errors[n]}
                        for n, s in ORACLES.items()},
            "pipelines": PIPELINE_DOC,
            "summary": [{"oracle": k[0], "policy_id": k[1], **v} for k, v in summary.items()],
            "matrix": [{"pipeline": k[0], "policy_id": k[1], "n": 80, **v} for k, v in matrix.items()],
            "divergence_classes": {n: dict(c.most_common()) for n, c in div_counter.items()},
            "probes": probes, "fixtures": per_fixture,
            "probe_strings": [{"probe": label, "input_escaped": esc(t),
                               "ours": {p: esc(normalize(t, p)) for p in POLICIES},
                               "oracles": {pipe: (esc(results[n][("probe-%02d" % i, pipe)]["output"])
                                                  if results[n][("probe-%02d" % i, pipe)]["output"] is not None
                                                  else "error")
                                           for n, sp in ORACLES.items() for pipe in sp["pipelines"]}}
                              for i, (label, t) in enumerate(PROBES)]}
    with open(os.path.join(OUT_DOCS, "agreement.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")
    write_markdown(data)
    print(json.dumps({"summary": data["summary"], "probes": probes, "errors": errors}, indent=1))


def write_markdown(d):
    L = []
    w = L.append
    w("# Agreement with other Arabic normalisers on the pilot fixtures")
    w("")
    w("Generated %s from the 80 pilot fixtures (64 dev, 16 acceptance) and arabic-normalize %s (UCD %s) by "
      "`scripts/compat/compare.py`. The CAMeL Tools, tnkeeh and Whisper harnesses are in `scripts/compat/harness/`; "
      "no PyArabic harness is included, so that no file here imports a GPL module: one is passed to the driver "
      "with `--harness pyarabic=PATH`. Every number below is computed by the driver; the "
      "machine-readable result is [agreement.json](agreement.json) and the per-fixture table is "
      "[fixtures.md](fixtures.md)." % (d["generated"], d["arabic_normalize_version"], d["unicode_version"]))
    w("")
    w("This is a pilot comparison on synthetic fixtures, not the compatibility target planned for compat policies (paragraph-level "
      "exact match on 10,000 stress paragraphs for each future `compat-*` policy). The pilot ships no compat "
      "policy; these tables show how far each tool's closest pipeline is from the three pilot policies, and "
      "where, so that compat policies can be designed later.")
    w("")
    w("## How the oracles were run")
    w("")
    w("- Each tool is installed in its own virtual environment outside this repository and is called as a "
      "subprocess that exchanges JSON lines. No oracle code is imported by, copied into or shipped with "
      "arabic-normalize. PyArabic is GPL and is used only this way.")
    w("- Only each tool's public functions are called, in the compositions below. Nothing is re-implemented.")
    w("- The tools use the Unicode data of their interpreter; arabic-normalize uses its pinned UCD %s tables."
      % d["unicode_version"])
    w("")
    w("| Oracle | Licence | Python | Interpreter Unicode | Installed packages |")
    w("|---|---|---|---|---|")
    for n, o in d["oracles"].items():
        w("| %s | %s | %s | %s | %s |" % (o["label"], o["licence"], o["env"]["python"], o["env"]["unicodedata"],
                                         ", ".join(o["env"]["freeze"])))
    w("")
    w("Installation notes: camel-tools was installed without its declared dependencies (torch, transformers, "
      "kenlm and others are not needed by `camel_tools.utils`); only `emoji` and `six`, which the utility modules "
      "import, were added. tnkeeh imports `farasa.segmenter` at load time but uses it only for segmentation, "
      "which is not used here, so farasapy (which downloads a Java archive on first use) is not installed and an "
      "inert module stands in for it.")
    w("")
    w("### Pipelines")
    w("")
    w("| Pipeline | Calls | Compared with |")
    w("|---|---|---|")
    for n, o in d["oracles"].items():
        inv = {}
        for pol, p in o["analogue"].items():
            inv.setdefault(p, []).append(pol)
        for p in o["pipelines"]:
            w("| `%s` | %s | %s |" % (p, d["pipelines"][p], ", ".join("`%s`" % x for x in inv.get(p, [])) or
                                    "matrix only"))
    w("")
    w("Whisper has no counterpart of `bayanat-norm-v1` or `raw-safe-v1`, and PyArabic none of `raw-safe-v1`; "
      "those cells are n/a in the per-fixture table.")
    w("")
    w("## Agreement with the closest pipeline, per fixture policy")
    w("")
    w("Exact: identical output. Spacing: identical after squeezing whitespace runs and trimming both outputs. "
      "Spacing+punct.: identical after also turning every punctuation character into a space on both sides.")
    w("")
    w("| Oracle | Policy | Fixtures | Exact | Spacing | Spacing+punct. |")
    w("|---|---|---|---|---|---|")
    for s in d["summary"]:
        w("| %s | `%s` | %d | %d | %d | %d |" % (d["oracles"][s["oracle"]]["label"], s["policy_id"], s["n"],
                                                 s["exact"], s["ws"], s["ws_punct"]))
    w("")
    w("## Matrix: every pipeline against every pilot policy (all 80 inputs, exact match)")
    w("")
    w("| Pipeline | bayanat-norm-v1 | asr-eval-v1 | raw-safe-v1 |")
    w("|---|---|---|---|")
    by = collections.OrderedDict()
    for m in d["matrix"]:
        by.setdefault(m["pipeline"], {})[m["policy_id"]] = m
    for p, row in by.items():
        w("| `%s` | %s | %s | %s |" % (p, *["%d (%d / %d)" % (row[x]["exact"], row[x]["ws"], row[x]["ws_punct"])
                                           for x in POLICIES]))
    w("")
    w("Cells: exact matches out of 80, then (spacing / spacing+punct.) matches.")
    w("")
    w("## Where they diverge")
    w("")
    w("Character classes involved in the differing segments, counted over the fixtures compared with each "
      "oracle's closest pipeline (one fixture can count in several classes).")
    w("")
    w("| Oracle | Classes (fixtures) |")
    w("|---|---|")
    for n, c in d["divergence_classes"].items():
        w("| %s | %s |" % (d["oracles"][n]["label"], ", ".join("%s (%d)" % kv for kv in c.items()) or "none"))
    w("")
    p = d["probes"]
    w("Behaviour checks computed from the same runs:")
    w("")
    w("- Whisper basic normaliser: on %d of the %d fixtures that contain harakat, its output has more "
      "space-separated tokens than `asr-eval-v1`, because it replaces every combining mark with a space and so "
      "splits vocalised words." % (p["whisper_basic_more_tokens_than_asr_eval_on_harakat_fixtures"],
                                   p["fixtures_with_harakat"]))
    w("- CAMeL Tools `normalize_unicode` (NFKC): on %d of the %d fixtures with U+FDFA or U+FDF2, the honorific "
      "ligature was expanded into words; `bayanat-norm-v1` keeps it and flags it (docs/DECISIONS.md, section 1)."
      % (p["camel_norm_expanded_honorific_ligature"], p["fixtures_with_U+FDFA_or_U+FDF2"]))
    w("")
    w("### Behaviour fingerprint")
    w("")
    w("Short probe strings, each isolating one feature, run through every pipeline. Inputs and outputs are "
      "shown as escapes, with a space written as `\\u0020`; (empty) means the output is empty.")
    w("")
    pipes = [pp for o in d["oracles"].values() for pp in o["pipelines"]]
    w("| Probe | Input | " + " | ".join("`%s`" % x for x in POLICIES + pipes) + " |")
    w("|---" * (2 + len(POLICIES) + len(pipes)) + "|")
    for pr in d["probe_strings"]:
        cells = [pr["ours"][x] for x in POLICIES] + [pr["oracles"][x] for x in pipes]
        w("| %s | %s | %s |" % (pr["probe"], pr["input_escaped"],
                                " | ".join(c.replace(" ", "\\u0020") or "(empty)" for c in cells)))
    w("")
    w("## What this means for compat policies")
    w("")
    w("None of the four tools is a drop-in match for a pilot policy, which is expected: the pilot policies keep "
      "punctuation and spacing (bayanat-norm-v1), remove invisible controls and invalid code points, and pin "
      "Unicode data. The `compat-camel-v1`, `compat-whisper-basic-v1` and `compat-pyarabic-v1` policies planned "
      "for v1.0 must be designed from these divergence classes and then verified on the stress corpus. Lucene "
      "was not run in this pass (no Java harness yet).")
    w("")
    with open(os.path.join(OUT_DOCS, "README.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))

    # Per-fixture table.
    T = ["# Per-fixture agreement with other normalisers", "",
         "Generated %s by `scripts/compat/compare.py` (see [README.md](README.md)). Each cell compares the oracle's closest pipeline for the "
         "fixture's policy (see [README.md](README.md)) with the fixture's expected output, which arabic-normalize "
         "reproduces. `=` exact match; `≈ws` equal after squeezing spaces; `≈p` equal after also dropping "
         "punctuation; `≠` different, followed by the character classes that differ. n/a: the tool has no "
         "counterpart of that policy. Oracle outputs, as escapes, are in [agreement.json](agreement.json)."
         % d["generated"], "",
         "| Fixture | Family | Policy | CAMeL Tools | tnkeeh | Whisper basic | PyArabic |",
         "|---|---|---|---|---|---|---|"]
    for r in d["fixtures"]:
        cells = []
        for n in ORACLES:
            c = r["oracles"][n]
            if c["pipeline"] is None:
                cells.append("n/a")
            elif c["exact"]:
                cells.append("=")
            elif c["ws"]:
                cells.append("≈ws")
            elif c["ws_punct"]:
                cells.append("≈p")
            else:
                cells.append("≠ " + ", ".join(c["classes"]))
        T.append("| %s | %s | `%s` | %s |" % (r["fixture_id"], r["family"], r["policy_id"], " | ".join(cells)))
    T.append("")
    with open(os.path.join(OUT_DOCS, "fixtures.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(T))


if __name__ == "__main__":
    main()

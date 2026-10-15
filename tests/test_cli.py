# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""The arnorm command line: normalize (text, JSONL, CSV, detailed, resume), diff, explain, policy, version."""
import csv
import hashlib
import io
import json
import os
import subprocess
import sys


from arabic_normalize import load_policy, normalize
from arabic_normalize.cli import main

WORKED = "إِلَى المَدْرَسَةِ ١٢"


def run_cli(args, stdin=b""):
    import arabic_normalize
    env = dict(os.environ)
    # Run the same package the test process imported (the source tree or an installed wheel).
    pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(arabic_normalize.__file__)))
    env["PYTHONPATH"] = pkg_parent + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([sys.executable, "-m", "arabic_normalize"] + args, input=stdin, capture_output=True, env=env)
    return r.returncode, r.stdout.decode("utf-8"), r.stderr.decode("utf-8")


def test_normalize_stdin_text():
    code, out, err = run_cli(["normalize"], (WORKED + "\n" + "على\n").encode("utf-8"))
    assert code == 0, err
    assert out == "الي المدرسة 12\nعلي\n"


def test_normalize_file_policy_and_out(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("مدرسة، جميلة!\n", encoding="utf-8")
    out = tmp_path / "out.txt"
    assert main(["normalize", "-p", "asr-eval-v1", str(src), "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == "مدرسه جميله\n"


def test_normalize_jsonl_and_detailed(tmp_path):
    src = tmp_path / "in.jsonl"
    src.write_text(json.dumps({"id": 1, "text": WORKED}, ensure_ascii=False) + "\n", encoding="utf-8")
    out = tmp_path / "out.jsonl"
    assert main(["normalize", "--jsonl", str(src), "--out", str(out)]) == 0
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rec["id"] == 1 and rec["text"] == WORKED
    assert rec["text_norm"] == normalize(WORKED)
    assert rec["policy_hash"] == load_policy("bayanat-norm-v1").policy_hash
    assert main(["normalize", "--jsonl", "--detailed", str(src), "--out", str(out)]) == 0
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rec["lossy_flags"] == ["alef_maqsura.to_yeh", "alef_variants.map"]
    assert rec["flags"] == ["taa_marbuta.flag"]
    assert len(rec["offset_map"]) == len(rec["text_norm"])
    assert rec["text_diac"] == WORKED  # raw-safe-v1 output: the input has harakat and nothing to clean


def test_output_schema(tmp_path, jsonschema_mod):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "schemas", "output.schema.json"), encoding="utf-8") as f:
        schema = json.load(f)
    src = tmp_path / "in.txt"
    src.write_text(WORKED + "\n‏ﻻ\u0007\n\n", encoding="utf-8")
    code, out, err = run_cli(["normalize", "--detailed", str(src)])
    assert code == 0, err
    rows = [json.loads(x) for x in out.splitlines()]
    assert len(rows) == 3
    for r in rows:
        jsonschema_mod.validate(r, schema)


def test_normalize_csv(tmp_path):
    src = tmp_path / "in.csv"
    src.write_text('id,text\n1,"مرحبا، عالم"\n2,١٢٣\n',
                   encoding="utf-8")
    code, out, err = run_cli(["normalize", "--csv", "-p", "asr-eval-v1", "--detailed", str(src)])
    assert code == 0, err
    rows = list(csv.DictReader(io.StringIO(out)))
    assert [r["text_norm"] for r in rows] == ["مرحبا عالم", "123"]
    assert rows[0]["policy_id"] == "asr-eval-v1"


def test_csv_export_identifies_policy_library_and_unicode(tmp_path):
    """Every export carries policy_id, policy_hash, lib_version and unicode_version (quality gate)."""
    from arabic_normalize import UNICODE_VERSION, __version__, load_policy
    src = tmp_path / "in.csv"
    src.write_text('id,text\n1,"إِلَى المَدْرَسَةِ"\n', encoding="utf-8")
    for extra in ([], ["--detailed"]):
        code, out, err = run_cli(["normalize", "--csv"] + extra + [str(src)])
        assert code == 0, err
        rows = list(csv.DictReader(io.StringIO(out)))
        assert len(rows) == 1
        r = rows[0]
        assert r["policy_id"] == "bayanat-norm-v1"
        assert r["policy_hash"] == load_policy("bayanat-norm-v1").policy_hash
        assert r["lib_version"] == __version__
        assert r["unicode_version"] == UNICODE_VERSION


def test_invalid_utf8_and_on_error(tmp_path):
    src = tmp_path / "bad.txt"
    src.write_bytes("نص\n".encode("utf-8") + b"\xff\xfe\n" + "على\n".encode("utf-8"))
    code, out, err = run_cli(["normalize", str(src)])
    assert code == 2 and "invalid_utf8" in err
    code, out, err = run_cli(["normalize", "--on-error", "record", str(src)])
    assert code == 0 and out == "نص\n\nعلي\n"
    code, out, err = run_cli(["normalize", "--on-error", "skip", str(src)])
    assert code == 0 and out == "نص\nعلي\n" and "1 record(s) rejected" in err


def test_jsonl_rejections(tmp_path):
    src = tmp_path / "in.jsonl"
    src.write_text('{"text": "نص"}\n{"body": 1}\n{"text": 3}\n{"text": "x"\n', encoding="utf-8")
    code, out, err = run_cli(["normalize", "--jsonl", "--on-error", "record", str(src)])
    assert code == 0, err
    reasons = [json.loads(x).get("error", {}).get("reason") for x in out.splitlines()]
    assert reasons == [None, "missing_text_field", "text_not_string", "invalid_json"]


def test_strict(tmp_path):
    code, out, err = run_cli(["normalize", "--strict"], "نص\u0007\n".encode("utf-8"))
    assert code == 2 and "control" in err
    code, out, err = run_cli(["normalize"], "نص\u0007\n".encode("utf-8"))
    assert code == 0 and out == "نص\n"


def test_resume_gives_the_same_output(tmp_path):
    lines = ["سطر رقم %d على ما يرام" % i
             for i in range(2600)]
    src = tmp_path / "in.txt"
    src.write_text("\n".join(lines) + "\n", encoding="utf-8")
    full = tmp_path / "full.txt"
    assert main(["normalize", str(src), "--out", str(full)]) == 0
    part = tmp_path / "part.txt"
    # Simulate an interrupted run: the first 1,000 records written and checkpointed.
    raw = src.read_bytes()
    offset = sum(len(x) for x in raw.splitlines(keepends=True)[:1000])
    part.write_text("".join(normalize(x) + "\n" for x in lines[:1000]), encoding="utf-8")
    with open(str(part) + ".checkpoint", "w", encoding="utf-8") as f:
        json.dump({"input": os.path.abspath(str(src)), "byte_offset": offset, "records": 1000,
                   "policy_hash": load_policy("bayanat-norm-v1").policy_hash, "mode": "text", "complete": False}, f)
    assert main(["normalize", str(src), "--out", str(part), "--resume"]) == 0
    assert hashlib.sha256(part.read_bytes()).hexdigest() == hashlib.sha256(full.read_bytes()).hexdigest()
    with open(str(part) + ".checkpoint", encoding="utf-8") as f:
        assert json.load(f)["complete"] is True


def test_diff_explain_policy_version(capsys):
    assert main(["diff", WORKED]) == 0
    out = capsys.readouterr().out
    assert "alef_variants.map" in out and "(lossy)" in out
    assert main(["diff", "--a", "bayanat-norm-v1", "--b", "asr-eval-v1", "--json", WORKED]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["rules_only_b"] == ["taa_marbuta.to_heh"]
    assert d["regions"] and d["regions"][0]["a"].endswith("ة")
    assert main(["explain", "--json", "ﻷ"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["rows"][0]["codepoint"] == "U+FEF7" and d["rows"][0]["output"] == "لا"
    assert main(["explain", "هٰذا"]) == 0
    assert "SUPERSCRIPT ALEF" in capsys.readouterr().out
    assert main(["policy", "list"]) == 0
    assert "bayanat-norm-v1" in capsys.readouterr().out
    assert main(["policy", "export", "bayanat-norm-v1", "--canonical"]) == 0
    canon = capsys.readouterr().out.strip()
    assert hashlib.sha256(canon.encode("utf-8")).hexdigest() == load_policy("bayanat-norm-v1").policy_hash
    assert main(["policy", "export", "raw-safe-v1"]) == 0
    assert json.loads(capsys.readouterr().out)["policy_id"] == "raw-safe-v1"
    assert main(["policy", "hash", "asr-eval-v1"]) == 0
    assert capsys.readouterr().out.strip() == load_policy("asr-eval-v1").policy_hash
    assert main(["version"]) == 0
    assert "Unicode 18.0.0" in capsys.readouterr().out


def test_unknown_policy_exit_code():
    code, out, err = run_cli(["normalize", "-p", "bayanat-norm-v9"], b"x\n")
    assert code == 2 and "unknown_policy" in err

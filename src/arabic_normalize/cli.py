# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""arnorm: command-line interface for arabic-normalize by Bayanat Labs.

  arnorm normalize [--policy ID|FILE] [--jsonl|--csv] [--field text] [--detailed] [FILE ...]
  arnorm diff --a POLICY --b POLICY [TEXT | --file FILE]
  arnorm explain TEXT [--policy ID]
  arnorm policy list | show ID | export ID [--canonical] | hash ID_OR_FILE
  arnorm version

Input is UTF-8 (strict). Files are streamed record by record; '-' or no file means stdin.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys

from . import engine
from ._ucd import UNICODE_VERSION
from ._version import __version__
from .errors import ArabicNormalizeError, InputRejected
from .policy import list_policies, load_policy

CHECKPOINT_EVERY = 1000


def _out_stream(path, append=False):
    if path in (None, "-"):
        return io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n", line_buffering=False), False
    return open(path, "a" if append else "w", encoding="utf-8", newline="\n"), True


def _inputs(files):
    return files if files else ["-"]


def _open_bin(path):
    if path == "-":
        return sys.stdin.buffer, False
    return open(path, "rb"), True


class _Checkpoint(object):
    def __init__(self, out_path, policy, mode):
        self.path = out_path + ".checkpoint" if out_path and out_path != "-" else None
        self.policy_hash = policy.policy_hash
        self.mode = mode

    def load(self, inp):
        if not self.path or not os.path.exists(self.path):
            return None
        with open(self.path, encoding="utf-8") as f:
            cp = json.load(f)
        if cp.get("input") != os.path.abspath(inp) or cp.get("policy_hash") != self.policy_hash or cp.get("mode") != self.mode:
            raise SystemExit("arnorm: checkpoint %s does not match this input, policy or mode; remove it or drop --resume"
                             % self.path)
        return cp

    def save(self, inp, offset, records, complete=False):
        if not self.path:
            return
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"input": os.path.abspath(inp), "byte_offset": offset, "records": records,
                       "policy_hash": self.policy_hash, "mode": self.mode, "complete": complete}, f)
        os.replace(tmp, self.path)


def _record_fields(res, detailed, text_raw=None):
    d = {"text_norm": res.text_norm} if not detailed else res.to_dict(text_raw=text_raw)
    if not detailed:
        d.update({"policy_id": res.policy_id, "policy_hash": res.policy_hash,
                  "lib_version": res.lib_version, "unicode_version": res.unicode_version})
    return d


def _handle_error(args, where, err, out, counters):
    counters["rejected"] += 1
    if args.on_error == "fail":
        sys.stderr.write("arnorm: %s: rejected (%s)\n" % (where, err))
        raise SystemExit(2)
    if args.on_error == "record":
        if args.mode == "text":
            out.write("\n")  # keep line alignment with the input
        elif args.mode == "jsonl":
            out.write(json.dumps({"error": {"reason": err.reason, "detail": err.detail, "where": where}},
                                 ensure_ascii=False) + "\n")


def cmd_normalize(args):
    policy = load_policy(args.policy)
    mode = "jsonl" if args.jsonl else ("csv" if args.csv else "text")
    args.mode = mode
    files = _inputs(args.files)
    if args.resume and (mode == "csv" or len(files) != 1 or files[0] == "-" or not args.out):
        raise SystemExit("arnorm: --resume needs one input file, --out, and text or --jsonl mode")
    ckpt = _Checkpoint(args.out, policy, mode)
    start = None
    if args.resume:
        start = ckpt.load(files[0])
        if start and start.get("complete"):
            sys.stderr.write("arnorm: checkpoint says this input is already complete\n")
            return 0
    out, close = _out_stream(args.out, append=bool(start))
    counters = {"records": 0, "rejected": 0}
    try:
        for path in files:
            if mode == "csv":
                _normalize_csv(args, policy, path, out, counters)
            else:
                _normalize_lines(args, policy, path, out, counters, mode, ckpt, start)
    finally:
        out.flush()
        if close:
            out.close()
        else:
            out.detach()
    if counters["rejected"]:
        sys.stderr.write("arnorm: %d record(s) rejected (--on-error %s)\n" % (counters["rejected"], args.on_error))
    return 0


def _normalize_lines(args, policy, path, out, counters, mode, ckpt, start):
    fh, close = _open_bin(path)
    try:
        offset = 0
        lineno = 0
        if start:
            fh.seek(start["byte_offset"])
            offset = start["byte_offset"]
            lineno = start["records"]
        for raw in fh:
            offset += len(raw)
            lineno += 1
            body = raw[:-1] if raw.endswith(b"\n") else raw
            where = "%s:%d" % (path, lineno)
            try:
                if mode == "text":
                    text = engine.decode_utf8(body)
                    if args.detailed:
                        res = engine.normalize_detailed(text, policy, strict=args.strict)
                        rec = {"line": lineno}
                        rec.update(res.to_dict(text_raw=text))
                        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    else:
                        out.write(engine.normalize(text, policy, strict=args.strict) + "\n")
                else:
                    if not body.strip():
                        continue
                    line = engine.decode_utf8(body)
                    rec, text = engine.parse_record(line, args.field)
                    if args.detailed:
                        res = engine.normalize_detailed(text, policy, strict=args.strict)
                        rec[args.out_field] = res.text_norm
                        d = res.to_dict()
                        d.pop("text_norm")
                        rec.update(d)
                    else:
                        rec[args.out_field] = engine.normalize(text, policy, strict=args.strict)
                        rec.update({"policy_id": policy.policy_id, "policy_hash": policy.policy_hash,
                                    "lib_version": __version__, "unicode_version": UNICODE_VERSION})
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                counters["records"] += 1
            except ArabicNormalizeError as e:
                _handle_error(args, where, e, out, counters)
            if args.out and lineno % CHECKPOINT_EVERY == 0:
                out.flush()
                ckpt.save(path, offset, lineno)
        if args.out and args.out != "-" and len(_inputs(args.files)) == 1:
            out.flush()
            ckpt.save(path, offset, lineno, complete=True)
    finally:
        if close:
            fh.close()


def _normalize_csv(args, policy, path, out, counters):
    fh, close = _open_bin(path)
    try:
        text_stream = io.TextIOWrapper(fh, encoding="utf-8", errors="strict", newline="")
        reader = csv.DictReader(text_stream)
        if reader.fieldnames is None or args.field not in reader.fieldnames:
            raise SystemExit("arnorm: %s: CSV has no column %r" % (path, args.field))
        extra = [args.out_field, "policy_id", "policy_hash", "lib_version", "unicode_version"]
        if args.detailed:
            extra += ["lossy_flags", "flags", "diacritization_ratio", "n_changes", "rejected"]
        names = list(reader.fieldnames) + [c for c in extra if c not in reader.fieldnames]
        writer = csv.DictWriter(out, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        row_no = 1
        while True:
            try:
                row = next(reader)
            except StopIteration:
                break
            except UnicodeDecodeError as e:
                _handle_error(args, "%s: row %d" % (path, row_no + 1), InputRejected("invalid_utf8", str(e)), out, counters)
                break
            row_no += 1
            try:
                text = row.get(args.field)
                if not isinstance(text, str):
                    raise InputRejected("missing_text_field", "row has no value for %r" % args.field)
                if args.detailed:
                    res = engine.normalize_detailed(text, policy, strict=args.strict)
                    row.update({args.out_field: res.text_norm, "lossy_flags": ";".join(res.lossy_flags),
                                "flags": ";".join(res.flags), "diacritization_ratio": "%.6f" % res.diacritization_ratio,
                                "n_changes": len(res.changes), "rejected": len(res.rejected_spans)})
                else:
                    row[args.out_field] = engine.normalize(text, policy, strict=args.strict)
                row.update({"policy_id": policy.policy_id, "policy_hash": policy.policy_hash,
                            "lib_version": __version__, "unicode_version": UNICODE_VERSION})
                writer.writerow(row)
                counters["records"] += 1
            except ArabicNormalizeError as e:
                _handle_error(args, "%s: row %d" % (path, row_no), e, out, counters)
        text_stream.detach()
    finally:
        if close:
            fh.close()


def _read_text_arg(args):
    if getattr(args, "file", None):
        with open(args.file, "rb") as f:
            return engine.decode_utf8(f.read())
    if args.text is None or args.text == "-":
        return engine.decode_utf8(sys.stdin.buffer.read())
    return args.text


def _show(s):
    """Make invisible and combining characters visible in terminal output."""
    out = []
    for ch in s:
        cp = ord(ch)
        cat = engine.U.general_category(cp)
        if cat in ("Cc", "Cf", "Zl", "Zp", "Cs", "Cn", "Co") or (cat.startswith("Z") and ch != " "):
            out.append("<U+%04X>" % cp)
        else:
            out.append(ch)
    return "".join(out)


def cmd_diff(args):
    text = _read_text_arg(args)
    if args.b is None:
        res = engine.normalize_detailed(text, args.a)
        if args.json:
            print(json.dumps({"policy_id": res.policy_id, "policy_hash": res.policy_hash, "before": text,
                              "after": res.text_norm, "changes": [c._asdict() for c in res.changes],
                              "lossy_flags": list(res.lossy_flags), "flags": list(res.flags)}, ensure_ascii=False, indent=1))
            return 0
        print("policy  %s  sha256 %s" % (res.policy_id, res.policy_hash))
        print("before  %s" % _show(text))
        print("after   %s" % _show(res.text_norm))
        for c in res.changes:
            print("  [%d:%d] %-28s %s -> %s%s" % (c.src_start, c.src_end, c.rule_id, _show(c.before) or "''",
                                                 _show(c.after) or "''", "  (lossy)" if c.lossy else ""))
        if res.flags:
            print("flags   %s" % ", ".join(res.flags))
        return 0
    d = engine.diff_policies(text, args.a, args.b)
    if args.json:
        print(json.dumps(d, ensure_ascii=False, indent=1))
        return 0
    print("A  %-22s %s" % (d["policy_a"], _show(d["text_a"])))
    print("B  %-22s %s" % (d["policy_b"], _show(d["text_b"])))
    print("identical: %s" % ("yes" if d["identical"] else "no"))
    if d["rules_only_a"]:
        print("rules only in A: %s" % ", ".join(d["rules_only_a"]))
    if d["rules_only_b"]:
        print("rules only in B: %s" % ", ".join(d["rules_only_b"]))
    for r in d["regions"]:
        print("  [%d:%d] %s   A: %s   B: %s" % (r["src_start"], r["src_end"], _show(r["source"]),
                                               _show(r["a"]) or "''", _show(r["b"]) or "''"))
    return 0


def cmd_explain(args):
    text = _read_text_arg(args)
    d = engine.explain(text, args.policy)
    if args.json:
        print(json.dumps(d, ensure_ascii=False, indent=1))
        return 0
    print("policy %s  sha256 %s" % (d["policy_id"], d["policy_hash"]))
    print("output %s" % _show(d["text_norm"]))
    print("%-5s %-9s %-6s %-3s %-4s %-2s %-40s %s" % ("idx", "code", "char", "gc", "ccc", "jt", "name", "rules -> output"))
    for r in d["rows"]:
        ch = _show(r["char"])
        if r["general_category"] in ("Mn", "Me"):
            ch = "◌" + r["char"]
        print("%-5d %-9s %-6s %-3s %-4d %-2s %-40s %s -> %s" % (
            r["index"], r["codepoint"], ch, r["general_category"], r["ccc"], r["joining_type"], r["name"][:40],
            ",".join(r["rules"]) or "-", _show(r["output"]) or "''"))
    if d["lossy_flags"]:
        print("lossy: %s" % ", ".join(d["lossy_flags"]))
    if d["flags"]:
        print("flags: %s" % ", ".join(d["flags"]))
    return 0


def cmd_policy(args):
    if args.action == "list":
        for pid in list_policies():
            p = load_policy(pid)
            print("%-18s %s  %s" % (pid, p.policy_hash, p.data.get("meta", {}).get("title_en", "")))
        return 0
    if not args.name:
        raise SystemExit("arnorm policy %s: give a policy id or file" % args.action)
    p = load_policy(args.name)
    if args.action == "hash":
        print(p.policy_hash)
    elif args.action == "export":
        text = p.canonical() if args.canonical else p.to_json()
        if args.out:
            with open(args.out, "w", encoding="utf-8", newline="\n") as f:
                f.write(text + "\n")
            sys.stderr.write("wrote %s (sha256 %s)\n" % (args.out, p.policy_hash))
        else:
            print(text)
    elif args.action == "show":
        meta = p.data.get("meta", {})
        print("%s  (%s)" % (p.policy_id, meta.get("title_en", "")))
        if meta.get("title_ar"):
            print(meta["title_ar"])
        print("sha256          %s" % p.policy_hash)
        print("unicode_form    %s   unicode_version %s   idempotent %s" % (p.unicode_form, p.data["unicode_version"],
                                                                          str(p.idempotent).lower()))
        from .policy import STAGE_ORDER
        for k in STAGE_ORDER:
            print("  %-22s %s" % (k, p.stages[k]))
    return 0


def cmd_version(args):
    print("arabic-normalize %s (Bayanat Labs), Unicode %s, spec arabic-normalize-spec-1" % (__version__, UNICODE_VERSION))
    for pid in list_policies():
        print("  %-18s %s" % (pid, load_policy(pid).policy_hash))
    return 0


def build_parser():
    ap = argparse.ArgumentParser(prog="arnorm", description="Arabic text normalisation with named, versioned policies "
                                 "(arabic-normalize by Bayanat Labs).")
    ap.add_argument("--version", action="version", version="arabic-normalize %s (Unicode %s)" % (__version__, UNICODE_VERSION))
    sub = ap.add_subparsers(dest="command")

    n = sub.add_parser("normalize", aliases=["normalise"], help="normalise text, JSONL or CSV (streams files)")
    n.add_argument("files", nargs="*", help="input files ('-' or none for stdin)")
    n.add_argument("--policy", "-p", default=engine.DEFAULT_POLICY, help="built-in policy id or policy JSON file")
    g = n.add_mutually_exclusive_group()
    g.add_argument("--jsonl", action="store_true", help="input is JSONL; normalise one field per record")
    g.add_argument("--csv", action="store_true", help="input is CSV with a header; normalise one column")
    n.add_argument("--field", default="text", help="field or column to normalise (default: text)")
    n.add_argument("--out-field", default="text_norm", help="output field or column (default: text_norm)")
    n.add_argument("--detailed", action="store_true", help="add offset map, change log, flags and statistics")
    n.add_argument("--strict", action="store_true", help="reject records with invalid code points instead of dropping them")
    n.add_argument("--on-error", choices=["fail", "skip", "record"], default="fail",
                   help="what to do with a rejected record (default: fail with exit code 2)")
    n.add_argument("--out", "-o", help="output file (default: stdout)")
    n.add_argument("--resume", action="store_true", help="resume from OUT.checkpoint (one text or JSONL file)")
    n.set_defaults(func=cmd_normalize)

    d = sub.add_parser("diff", help="show what a policy changes, or compare two policies")
    d.add_argument("text", nargs="?", help="text to compare ('-' or none: stdin)")
    d.add_argument("--file", help="read the text from a file")
    d.add_argument("--a", "--policy", dest="a", default=engine.DEFAULT_POLICY, help="policy A (or the single policy)")
    d.add_argument("--b", default=None, help="policy B (omit to show before/after for policy A)")
    d.add_argument("--json", action="store_true")
    d.set_defaults(func=cmd_diff)

    e = sub.add_parser("explain", help="list every code point with its properties and the rules applied")
    e.add_argument("text", nargs="?", help="text to explain ('-' or none: stdin)")
    e.add_argument("--file", help="read the text from a file")
    e.add_argument("--policy", "-p", default=engine.DEFAULT_POLICY)
    e.add_argument("--json", action="store_true")
    e.set_defaults(func=cmd_explain)

    p = sub.add_parser("policy", help="list, show, export or hash policies")
    p.add_argument("action", choices=["list", "show", "export", "hash"])
    p.add_argument("name", nargs="?", help="policy id or policy JSON file")
    p.add_argument("--canonical", action="store_true", help="export the canonical JSON that the hash covers")
    p.add_argument("--out", "-o")
    p.set_defaults(func=cmd_policy)

    v = sub.add_parser("version", help="library, Unicode and policy hash versions")
    v.set_defaults(func=cmd_version)
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 1
    try:
        return args.func(args)
    except ArabicNormalizeError as e:
        sys.stderr.write("arnorm: rejected (%s)\n" % e)
        return 2
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())

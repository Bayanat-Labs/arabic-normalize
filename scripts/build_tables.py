#!/usr/bin/env python3
# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Generate src/arabic_normalize/tables/ucd_tables.json from the pinned Unicode Character Database.

Inputs: ucd/<version>/*.txt.gz (verbatim copies of https://www.unicode.org/Public/<version>/ucd/ files,
gzipped with mtime=0; SHA-256 of the uncompressed files in ucd/<version>/SHA256SUMS).
The output is deterministic and is derived data under the Unicode License V3 (see NOTICE-unicode.txt).

Run: python scripts/build_tables.py [--check]
"""
import argparse
import gzip
import hashlib
import json
import os
import sys

VERSION = "18.0.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UCD = os.path.join(ROOT, "ucd", VERSION)
OUT = os.path.join(ROOT, "src", "arabic_normalize", "tables", "ucd_tables.json")

# Names are stored only for these ranges (used by `arnorm explain`; never by normalisation).
NAME_RANGES = [(0x0000, 0x024F), (0x0300, 0x036F), (0x0600, 0x06FF), (0x0750, 0x077F), (0x0870, 0x08FF),
               (0x2000, 0x206F), (0x2070, 0x209F), (0xFB50, 0xFDFF), (0xFE00, 0xFE0F), (0xFE70, 0xFEFF),
               (0xFFF0, 0xFFFF), (0x10EC0, 0x10EFF), (0x1EE00, 0x1EEFF), (0x1F3FB, 0x1F3FF)]


def read(name):
    path = os.path.join(UCD, name + ".gz")
    data = gzip.decompress(open(path, "rb").read())
    return data, data.decode("utf-8")


def check_sums():
    sums = {}
    for line in open(os.path.join(UCD, "SHA256SUMS"), encoding="utf-8"):
        sha, name = line.split()
        sums[name] = sha
    got = {}
    for name, sha in sums.items():
        data, _ = read(name)
        h = hashlib.sha256(data).hexdigest()
        if h != sha:
            raise SystemExit("SHA-256 mismatch for %s" % name)
        got[name] = h
    return got


def parse_cp_field(field):
    field = field.strip()
    if ".." in field:
        a, b = field.split("..")
        return int(a, 16), int(b, 16)
    c = int(field, 16)
    return c, c


def data_lines(text):
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            yield [p.strip() for p in line.split(";")]


def to_ranges(cps):
    cps = sorted(set(cps))
    out = []
    for c in cps:
        if out and out[-1][1] == c - 1:
            out[-1][1] = c
        else:
            out.append([c, c])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if the committed table differs from a fresh build")
    a = ap.parse_args()
    sums = check_sums()

    _, ud = read("UnicodeData.txt")
    gc = {}
    ccc = {}
    decomp = {}
    lower = {}
    names = {}
    pending_first = None
    for line in ud.splitlines():
        f = line.split(";")
        cp = int(f[0], 16)
        name, cat = f[1], f[2]
        if name.endswith(", First>"):
            pending_first = (cp, cat)
            continue
        if name.endswith(", Last>"):
            start, cat0 = pending_first
            for c in range(start, cp + 1):
                gc[c] = cat0
            pending_first = None
            continue
        gc[cp] = cat
        if int(f[3]):
            ccc[cp] = int(f[3])
        if f[5]:
            parts = f[5].split()
            compat = parts[0].startswith("<")
            if compat:
                parts = parts[1:]
            decomp[cp] = (compat, [int(p, 16) for p in parts])
        if f[13]:
            lower[cp] = int(f[13], 16)
        if any(lo <= cp <= hi for lo, hi in NAME_RANGES):
            names[cp] = name if not name.startswith("<") else (f[10] or name)

    # Full decompositions.
    def full(cp, compat_ok, memo):
        if cp in memo:
            return memo[cp]
        d = decomp.get(cp)
        if d is None or (d[0] and not compat_ok):
            res = [cp]
        else:
            res = []
            for x in d[1]:
                res.extend(full(x, compat_ok, memo))
        memo[cp] = res
        return res

    m1, m2 = {}, {}
    nfd = {}
    nfkd = {}
    for cp in sorted(decomp):
        a1 = full(cp, False, m1)
        if a1 != [cp]:
            nfd[cp] = a1
        a2 = full(cp, True, m2)
        if a2 != [cp]:
            nfkd[cp] = a2

    _, dnp = read("DerivedNormalizationProps.txt")
    props = {}
    for parts in data_lines(dnp):
        lo, hi = parse_cp_field(parts[0])
        key = parts[1] if len(parts) == 2 else parts[1] + "=" + parts[2]
        props.setdefault(key, []).extend(range(lo, hi + 1))
    fce = set(props["Full_Composition_Exclusion"])
    compose = []
    for cp in sorted(decomp):
        compat, parts = decomp[cp]
        if not compat and len(parts) == 2 and cp not in fce:
            compose.append([parts[0], parts[1], cp])

    _, pl = read("PropList.txt")
    plist = {}
    for parts in data_lines(pl):
        lo, hi = parse_cp_field(parts[0])
        plist.setdefault(parts[1], []).extend(range(lo, hi + 1))

    _, sc = read("Scripts.txt")
    scripts = {}
    for parts in data_lines(sc):
        lo, hi = parse_cp_field(parts[0])
        if parts[1] in ("Arabic", "Latin"):
            scripts.setdefault(parts[1], []).extend(range(lo, hi + 1))

    _, ash = read("ArabicShaping.txt")
    jt = {}
    for parts in data_lines(ash):
        lo, hi = parse_cp_field(parts[0])
        for c in range(lo, hi + 1):
            jt[c] = parts[2]
    # Derived rule (ArabicShaping.txt header): unlisted Mn, Me, Cf are T; everything else unlisted is U.
    for c, cat in gc.items():
        if c not in jt and cat in ("Mn", "Me", "Cf"):
            jt[c] = "T"

    _, ed = read("emoji-data.txt")
    emoji = {}
    for parts in data_lines(ed):
        lo, hi = parse_cp_field(parts[0])
        if parts[1] in ("Extended_Pictographic", "Emoji_Modifier"):
            emoji.setdefault(parts[1], []).extend(range(lo, hi + 1))

    gc_ranges = []
    for c in sorted(gc):
        cat = gc[c]
        if gc_ranges and gc_ranges[-1][2] == cat and gc_ranges[-1][1] == c - 1:
            gc_ranges[-1][1] = c
        else:
            gc_ranges.append([c, c, cat])

    latin = set(scripts["Latin"])
    arabic = set(scripts["Arabic"])
    table = {
        "unicode_version": VERSION,
        "source": "https://www.unicode.org/Public/%s/ucd/" % VERSION,
        "source_sha256": sums,
        "license": "Unicode-3.0 (derived from the Unicode Character Database; see NOTICE-unicode.txt)",
        "gc_ranges": gc_ranges,
        "ccc": [[c, ccc[c]] for c in sorted(ccc)],
        "nfd": [[c] + nfd[c] for c in sorted(nfd)],
        "nfkd": [[c] + nfkd[c] for c in sorted(nfkd)],
        "compat_decomposable": sorted(c for c, (compat, _) in decomp.items() if compat),
        "compose": compose,
        "nfc_qc_no": to_ranges(props.get("NFC_QC=N", [])),
        "nfc_qc_maybe": to_ranges(props.get("NFC_QC=M", [])),
        "nfkc_qc_no": to_ranges(props.get("NFKC_QC=N", [])),
        "nfkc_qc_maybe": to_ranges(props.get("NFKC_QC=M", [])),
        "white_space": to_ranges(plist["White_Space"]),
        "noncharacter": to_ranges(plist["Noncharacter_Code_Point"]),
        "bidi_control": to_ranges(plist["Bidi_Control"]),
        "script_arabic": to_ranges(arabic),
        "script_latin": to_ranges(latin),
        "joining_type": {t: to_ranges([c for c, v in jt.items() if v == t]) for t in sorted(set(jt.values()))},
        "extended_pictographic": to_ranges(emoji["Extended_Pictographic"]),
        "emoji_modifier": to_ranges(emoji["Emoji_Modifier"]),
        "latin_lower": [[c, lower[c]] for c in sorted(lower) if c in latin and gc.get(c) in ("Lu", "Lt")],
        "names": [[c, names[c]] for c in sorted(names)],
    }
    blob = json.dumps(table, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    if a.check:
        cur = open(OUT, encoding="utf-8").read()
        if cur != blob:
            raise SystemExit("ucd_tables.json is out of date; run scripts/build_tables.py")
        print("ucd_tables.json is up to date")
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(blob)
    print("wrote %s (%d bytes); sha256 %s" % (os.path.relpath(OUT, ROOT), len(blob.encode()),
                                               hashlib.sha256(blob.encode()).hexdigest()))
    print("compose pairs %d, nfd %d, nfkd %d, ccc %d" % (len(compose), len(nfd), len(nfkd), len(ccc)), file=sys.stderr)


if __name__ == "__main__":
    main()

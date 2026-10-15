#!/usr/bin/env python3
# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Generate every computed part of the documentation from the released files.

Writes docs/policies/<id>.md and <id>.ar.md (policy cards), CLAIMS.md, and the marked sections of README.md
and CHANGELOG.md (worked example, policy table, fixture counts, policy hashes). Every number comes from the
engine run on the fixture files or from the policy files. `--check` fails if any output is stale.

Run: python scripts/make_docs.py [--check]
"""
import argparse
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import arabic_normalize as an  # noqa: E402
from arabic_normalize.errors import ArabicNormalizeError  # noqa: E402
from arabic_normalize.policy import STAGE_ORDER  # noqa: E402

DOC_DATE = "2026-10-15"  # date the counts and census refer to; change it when the docs are regenerated for a release
CENSUS = os.path.join(ROOT, "evidence", "census_2026-10-15.json")
JS_COUNTS = os.path.join(ROOT, "js", "conformance.json")  # written by js/scripts/conformance_counts.mjs
WORKED = "إِلَى المَدْرَسَةِ " \
         "الجَدِيدَةِ ١٢٣"

STAGE_AR = {
    "reject_invalid": "رفض المحارف غير الصالحة", "strip_controls": "محارف التنسيق غير المرئية",
    "presentation_forms": "أشكال العرض", "ligatures_honorific": "الرموز المركبة التعظيمية",
    "bidi_zw": "محارف الاتجاه والمحارف الصفرية العرض", "canonical_order": "الترتيب القانوني",
    "tatweel": "التطويل", "diacritics": "الحركات", "quranic_marks": "العلامات القرآنية",
    "superscript_alef": "الألف الخنجرية", "alef_variants": "صور الألف", "alef_maqsura": "الألف المقصورة",
    "taa_marbuta": "التاء المربوطة", "hamza_carriers": "الهمزة على الواو والياء",
    "persian_urdu_letters": "الحروف الفارسية والأردية", "digits": "الأرقام", "punctuation": "علامات الترقيم",
    "whitespace": "المسافات", "latin_case": "حالة الحروف اللاتينية",
}

EFFECT = {  # (stage, mode) -> (English, Arabic)
    ("reject_invalid", "drop"): ("Remove lone surrogates, control characters other than whitespace, and noncharacters; report them in rejected_spans.",
                                 "حذف البدائل المنفردة ومحارف التحكم غير الفراغية والمحارف غير الصالحة، مع تسجيلها في قائمة المقاطع المرفوضة."),
    ("reject_invalid", "error"): ("Reject the whole input if it contains any of them.", "رفض النص كاملًا إذا احتوى على أي منها."),
    ("strip_controls", "strip"): ("Remove invisible format characters: soft hyphen, word joiner, BOM and similar.",
                                  "حذف محارف التنسيق غير المرئية، مثل الواصلة المرنة ومحرف الربط وعلامة ترتيب البايتات."),
    ("strip_controls", "keep"): ("Keep them.", "إبقاؤها."),
    ("presentation_forms", "map"): ("Map Arabic presentation forms (U+FB50 to U+FDFF, U+FE70 to U+FEFF) to their NFKC letters, for example ﻻ to لا.",
                                    "تحويل أشكال العرض العربية إلى حروفها وفق NFKC، مثل ﻻ إلى لا."),
    ("presentation_forms", "keep"): ("Keep presentation forms.", "إبقاء أشكال العرض كما هي."),
    ("presentation_forms", "flag"): ("Keep presentation forms and raise presentation_forms.flag.", "إبقاء أشكال العرض مع رفع علامة تنبيه."),
    ("ligatures_honorific", "flag"): ("Keep honorific word ligatures such as ﷺ and ﷲ as one character and raise ligatures_honorific.flag.",
                                      "إبقاء الرموز المركبة التعظيمية، مثل ﷺ ولفظ الجلالة ﷲ، محرفًا واحدًا مع رفع علامة تنبيه."),
    ("ligatures_honorific", "keep"): ("Keep them, without a flag.", "إبقاؤها دون علامة تنبيه."),
    ("ligatures_honorific", "expand"): ("Expand them to words (NFKC).", "فكّها إلى كلمات وفق NFKC."),
    ("bidi_zw", "strip-except-meaningful"): ("Remove bidi controls and zero-width characters, except a ZWNJ that prevents a join and a ZWJ inside an emoji sequence.",
                                             "حذف محارف التحكم الاتجاهي والمحارف الصفرية العرض، باستثناء الفاصل غير الواصل الذي يمنع اتصال حرفين، والواصل الصفري داخل تسلسل الرموز التعبيرية."),
    ("bidi_zw", "keep"): ("Keep them.", "إبقاؤها."),
    ("bidi_zw", "strip"): ("Remove all of them.", "حذفها كلها."),
    ("canonical_order", "NFC"): ("Apply NFC (canonical composition and mark order) from the pinned UCD 18.0.0 tables; a final NFC pass runs at the end.",
                                 "تطبيق صيغة التطبيع NFC (التركيب القانوني وترتيب العلامات) من جداول يونيكود 18.0.0 المثبّتة، مع مرور أخير في النهاية."),
    ("canonical_order", "NFKC"): ("Apply NFKC to all text (lossy for non-Arabic compatibility characters).",
                                  "تطبيق صيغة التطبيع NFKC على النص كله (تغيير فاقد للمعلومات في المحارف التوافقية غير العربية)."),
    ("canonical_order", "none"): ("No Unicode normalisation.", "دون تطبيع يونيكود."),
    ("tatweel", "strip"): ("Remove tatweel (ـ).", "حذف التطويل (ـ)."),
    ("tatweel", "keep"): ("Keep tatweel.", "إبقاء التطويل."),
    ("diacritics", "strip"): ("Remove harakat U+064B to U+0652 (tanween, fatha, damma, kasra, shadda, sukun).",
                              "حذف الحركات من U+064B إلى U+0652 (التنوين والفتحة والضمة والكسرة والشدة والسكون)."),
    ("diacritics", "strip-except-shadda"): ("Remove harakat except shadda.", "حذف الحركات ما عدا الشدة."),
    ("diacritics", "keep"): ("Keep harakat.", "إبقاء الحركات."),
    ("quranic_marks", "strip"): ("Remove Quranic annotation marks (explicit list in SPEC.md 4.9).",
                                 "حذف علامات الضبط القرآنية (القائمة الكاملة في المواصفة، القسم 4.9)."),
    ("quranic_marks", "keep"): ("Keep Quranic marks.", "إبقاء العلامات القرآنية."),
    ("superscript_alef", "strip"): ("Remove the superscript (dagger) alef.", "حذف الألف الخنجرية."),
    ("superscript_alef", "to-alef"): ("Replace the superscript alef with a full alef.", "استبدال ألف كاملة بالألف الخنجرية."),
    ("superscript_alef", "keep"): ("Keep the superscript alef.", "إبقاء الألف الخنجرية."),
    ("alef_variants", "map"): ("Map أ إ آ ٱ to ا (lossy).", "تحويل الألف المهموزة (أ، إ) والممدودة (آ) وهمزة الوصل (ٱ) إلى ا (تغيير فاقد للمعلومات)."),
    ("alef_variants", "keep"): ("Keep alef variants.", "إبقاء صور الألف."),
    ("alef_maqsura", "to-yeh"): ("Map ى to ي (lossy).", "تحويل ى إلى ي (تغيير فاقد للمعلومات)."),
    ("alef_maqsura", "flag"): ("Keep ى and raise alef_maqsura.flag.", "إبقاء ى مع رفع علامة تنبيه."),
    ("alef_maqsura", "keep"): ("Keep alef maqsura.", "إبقاء الألف المقصورة."),
    ("taa_marbuta", "flag"): ("Keep ة and raise taa_marbuta.flag.", "إبقاء التاء المربوطة ة مع رفع علامة تنبيه."),
    ("taa_marbuta", "to-heh"): ("Map ة to ه (lossy).", "تحويل ة إلى ه (تغيير فاقد للمعلومات)."),
    ("taa_marbuta", "keep"): ("Keep taa marbuta, without a flag.", "إبقاء التاء المربوطة دون علامة تنبيه."),
    ("hamza_carriers", "keep"): ("Keep ؤ and ئ.", "إبقاء الهمزة على الواو (ؤ) وعلى الياء (ئ)."),
    ("hamza_carriers", "fold"): ("Map ؤ to و and ئ to ي (lossy).", "تحويل الواو المهموزة (ؤ) إلى و، والياء المهموزة (ئ) إلى ي (تغيير فاقد للمعلومات)."),
    ("persian_urdu_letters", "keep"): ("Keep Persian and Urdu letters (ی ک ہ ھ).",
                                       "إبقاء الحروف الفارسية والأردية (ی ک ہ ھ)."),
    ("persian_urdu_letters", "map"): ("Map Persian and Urdu letters to their Arabic counterparts (lossy).",
                                      "تحويل الحروف الفارسية والأردية إلى نظائرها العربية (تغيير فاقد للمعلومات)."),
    ("digits", "ascii"): ("Map Arabic-Indic and Extended Arabic-Indic digits to 0 to 9.",
                          "تحويل الأرقام العربية المشرقية والفارسية إلى الأرقام من 0 إلى 9."),
    ("digits", "keep"): ("Keep digits as written.", "إبقاء الأرقام كما كُتبت."),
    ("digits", "arabic-indic"): ("Map digits to Arabic-Indic digits.", "تحويل الأرقام إلى الأرقام العربية المشرقية."),
    ("punctuation", "keep"): ("Keep punctuation.", "إبقاء علامات الترقيم."),
    ("punctuation", "strip"): ("Replace every punctuation mark with a space.", "وضع مسافة مكان كل علامة ترقيم."),
    ("punctuation", "ascii"): ("Map Arabic punctuation to ASCII punctuation.", "تحويل علامات الترقيم العربية إلى نظائرها اللاتينية."),
    ("whitespace", "keep"): ("Keep whitespace as written.", "إبقاء المسافات كما كُتبت."),
    ("whitespace", "collapse"): ("Collapse whitespace runs to one space and trim both ends.",
                                 "دمج الفراغات المتتالية في مسافة واحدة وحذف الفراغ في البداية والنهاية."),
    ("latin_case", "keep"): ("Keep Latin letter case.", "إبقاء حالة الحروف اللاتينية."),
    ("latin_case", "lower"): ("Lower-case Latin letters (lossy).", "تحويل الحروف اللاتينية إلى حروف صغيرة (تغيير فاقد للمعلومات)."),
}

LOSSY_BY_MODE = {
    ("alef_variants", "map"): "alef_variants.map", ("alef_maqsura", "to-yeh"): "alef_maqsura.to_yeh",
    ("taa_marbuta", "to-heh"): "taa_marbuta.to_heh", ("hamza_carriers", "fold"): "hamza_carriers.fold",
    ("persian_urdu_letters", "map"): "persian_urdu_letters.map", ("latin_case", "lower"): "latin_case.lower",
}

USE = {
    "bayanat-norm-v1": (
        "Default for text_norm columns in Bayanat Labs datasets, deduplication and statistics.",
        "The RULES.md section 5.1 recipe. Store `text_raw` (and `text_diac`, the raw-safe-v1 output) next to it.",
        "السياسة الافتراضية لحقل النص الموحد text_norm في مجموعات بيانات بيانات لابز، ولإزالة التكرار والإحصاءات.",
        "تطبّق وصفة القسم 5.1 من قواعد البرنامج. يُحفظ النص الخام text_raw والنص المشكول text_diac (ناتج raw-safe-v1) إلى جانبه."),
    "asr-eval-v1": (
        "Scoring only: WER and CER for Arabic speech recognition.",
        "Apply the same policy to the reference and the hypothesis and report the policy id and hash with every score (TL-001 ArabicWER).",
        "للتقييم فقط: حساب معدل خطأ الكلمات ومعدل خطأ الحروف في التعرّف الآلي على الكلام العربي.",
        "تُطبَّق السياسة نفسها على النص المرجعي وعلى ناتج النظام، ويُذكر معرّف السياسة وبصمتها مع كل نتيجة."),
    "raw-safe-v1": (
        "Cleaning without changing any letter, mark, digit or punctuation.",
        "The recipe for text_diac columns, for display and for legal text.",
        "تنظيف لا يغيّر أي حرف أو علامة أو رقم أو علامة ترقيم.",
        "وصفة حقل النص المشكول text_diac، وللعرض، وللنصوص القانونية."),
}

# Added after the lossy-rule review (docs/LOSSY_REVIEW.md, findings L-2 and L-3).
UTHMANI_EN = ("Uthmani (Quranic) spelling is not converted to modern spelling: removing the superscript alef leaves the "
              "consonantal skeleton (ٱلْكِتَٰبُ becomes الكتب, not الكتاب), which can coincide with another word. "
              "This is not flagged as lossy, because the superscript alef is counted as a vowel mark in diacritization_ratio.")
UTHMANI_AR = ("لا يُحوَّل الرسم العثماني إلى الرسم الإملائي الحديث: حذف الألف الخنجرية يُبقي الهيكل الحرفي "
              "(ٱلْكِتَٰبُ تصبح الكتب لا الكتاب)، وقد يطابق ذلك كلمة أخرى. ولا يُسجَّل هذا تغييرًا فاقدًا للمعلومات، "
              "لأن الألف الخنجرية تُحسب علامةَ تشكيل في نسبة التشكيل diacritization_ratio.")
MAQSURA_EN = ("The ى to ي rule is meant for Arabic-language text. In some other languages written in Arabic script "
              "(for example Uyghur) ى and ي are different letters; the change is still flagged as lossy.")
MAQSURA_AR = ("قاعدة تحويل ى إلى ي مخصصة للنص العربي. ففي بعض اللغات الأخرى المكتوبة بالحرف العربي (مثل الأويغورية) "
              "تكون ى وي حرفين مختلفين، ويبقى التغيير مسجَّلًا على أنه فاقد للمعلومات.")

LIMITS = {
    "bayanat-norm-v1": (
        ["Words that differ only in the hamza of an alef or in final ى/ي become identical (for example إن/أن, على/علي); some names change spelling.",
         "Not for vocalisation, OCR or phonology tasks: use text_raw or raw-safe-v1.",
         "Persian and Urdu letters are kept, so mixed Arabic and Persian text is not unified.",
         "Arabic presentation forms follow NFKC exactly, so an isolated harakat form such as U+FE70 leaves a space behind.",
         UTHMANI_EN, MAQSURA_EN],
        ["تصبح الكلمات التي لا تختلف إلا في همزة الألف أو في الياء والألف المقصورة في آخرها متطابقة (مثل إن وأن، وعلى وعلي)، وتتغير كتابة بعض الأسماء.",
         "لا تُستخدم في مهام التشكيل أو التعرف الضوئي على الحروف أو الصوتيات؛ استخدم النص الخام أو سياسة raw-safe-v1.",
         "تبقى الحروف الفارسية والأردية كما هي، فلا يُوحَّد النص المختلط بين العربية والفارسية.",
         "تتبع أشكال العرض العربية NFKC بدقة، ولذلك يترك الشكل المنفصل لعلامات التشكيل مثل U+FE70 مسافة بعد تحويله.",
         UTHMANI_AR, MAQSURA_AR]),
    "asr-eval-v1": (
        ["Lossy by design (ة to ه, ى to ي, alef variants): never store its output as a text field.",
         "Arabic decimal and thousands separators are punctuation, so a number such as ١٬٢٥٠ becomes several tokens.",
         "Latin letter case is kept.", UTHMANI_EN, MAQSURA_EN],
        ["يفقد بعض المعلومات عمدًا (تحويل التاء المربوطة إلى هاء، والألف المقصورة إلى ياء، وتوحيد صور الألف)، فلا يُخزَّن ناتجه حقلًا نصيًا.",
         "الفاصلتان العشرية والألفية العربيتان علامتا ترقيم، فيتحول عدد مثل ١٬٢٥٠ إلى أكثر من كلمة.",
         "تبقى حالة الحروف اللاتينية كما هي.", UTHMANI_AR, MAQSURA_AR]),
    "raw-safe-v1": (
        ["Removes bidi controls, which can change how mixed right-to-left and left-to-right text is displayed: keep text_raw when exact display matters.",
         "Keeps presentation forms, tatweel, harakat and every letter."],
        ["يحذف محارف التحكم الاتجاهي، وقد يغيّر ذلك طريقة عرض النص المختلط بين الاتجاهين؛ احتفظ بالنص الخام إذا كان العرض الدقيق مهمًا.",
         "يُبقي أشكال العرض والتطويل والحركات وجميع الحروف."]),
}


def load_jsonl(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def fixture_results():
    dev = load_jsonl("tests/fixtures/dev/dev.jsonl")
    acc = load_jsonl("tests/fixtures/acceptance/acceptance.jsonl")
    rej = load_jsonl("tests/fixtures/rejected/rejected.jsonl")
    res = []
    for fx in dev + acc:
        r = an.normalize_detailed(fx["input"], fx["policy_id"])
        ok = (r.text_norm == fx["expected_output"] and list(r.rules) == fx["expected_rules"]
              and list(r.lossy_flags) == fx["expected_lossy_flags"] and list(r.flags) == fx["expected_flags"]
              and [dict(x) for x in r.rejected_spans] == fx["expected_rejected_spans"]
              and (fx["expected_offset_map"] is None or [list(x) for x in r.offset_map] == fx["expected_offset_map"]))
        res.append((fx, r, ok))
    rej_ok = 0
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    from test_rejected import _run  # the same harness as the test suite
    for fx in rej:
        try:
            _run(fx)
        except ArabicNormalizeError as e:
            rej_ok += e.reason == fx["expected_reason"]
    return dev, acc, rej, res, rej_ok


def esc(s):
    return "".join("<U+%04X>" % ord(c) if an.engine.U.general_category(ord(c)) in ("Cc", "Cf", "Cs", "Cn") else c for c in s)


def policy_lossy(p):
    out = [LOSSY_BY_MODE[(k, v)] for k, v in p.stages.items() if (k, v) in LOSSY_BY_MODE]
    if p.unicode_form == "NFKC":
        out.append("canonical_order.nfkc")
    return sorted(out)


def stage_rows(p):
    rows = []
    for k in STAGE_ORDER[:5]:
        rows.append((k, p.stages[k]))
    rows.append(("canonical_order", p.unicode_form))
    for k in STAGE_ORDER[5:]:
        rows.append((k, p.stages[k]))
    return rows


def card(pid, res, lang):
    p = an.load_policy(pid)
    meta = p.data.get("meta", {})
    examples = [(fx, r) for fx, r, ok in res if fx["policy_id"] == pid and ok and fx["input"] != r.text_norm][:6]
    lossy = policy_lossy(p)
    u = USE[pid]
    if lang == "en":
        L = ["# %s" % pid, "", "**%s**" % meta.get("title_en", ""), "",
             "| Field | Value |", "|---|---|",
             "| Policy id | `%s` |" % pid, "| SHA-256 | `%s` |" % p.policy_hash,
             "| Spec | %s |" % p.data["spec"], "| Unicode | %s, form %s |" % (p.data["unicode_version"], p.unicode_form),
             "| Idempotent | %s (tested) |" % ("yes" if p.idempotent else "no"),
             "| Status | %s, arabic-normalize %s |" % (meta.get("status", ""), an.__version__),
             "| Licence | %s (policy file), Bayanat Labs |" % meta.get("license", ""), "",
             "## Use", "", u[0] + " " + u[1], "",
             "## Stages (in order)", "", "| # | Stage | Mode | Effect |", "|---|---|---|---|"]
        for i, (k, v) in enumerate(stage_rows(p), 1):
            L.append("| %d | %s | %s | %s |" % (i, k, v, EFFECT[(k, v)][0]))
        L += ["", "## Lossy rules", ""]
        L += ["- `%s`" % x for x in lossy] or ["None: no letter is changed."]
        L += ["", "Every lossy change is logged with `lossy: true` and listed in `lossy_flags`.", "",
              "## Examples (from the conformance fixtures, computed)", "", "| Fixture | Input | Output | Rules |", "|---|---|---|---|"]
        for fx, r in examples:
            L.append("| %s | %s | %s | %s |" % (fx["fixture_id"], esc(fx["input"]), esc(r.text_norm) or "(empty)", ", ".join(r.rules)))
        L += ["", "## Limitations", ""] + ["- " + x for x in LIMITS[pid][0]]
        L += ["", "## Cite", "", "Normalised with `%s` (sha256 `%s`), arabic-normalize %s, Bayanat Labs." % (pid, p.policy_hash, an.__version__),
              "", "Arabic version: [%s.ar.md](%s.ar.md). Stage definitions: [SPEC.md](../SPEC.md). Generated by `scripts/make_docs.py`." % (pid, pid), ""]
        return "\n".join(L)
    L = ["---", "lang: ar", "dir: rtl", "native_review: pending (independent AI Arabic review, then a human native review, recommended)", "---", "",
         '<div dir="rtl" lang="ar">', "", "# %s" % pid, "", "**%s**" % meta.get("title_ar", ""), "",
         "| الحقل | القيمة |", "|---|---|",
         "| معرّف السياسة | `%s` |" % pid, "| بصمة SHA-256 | `%s` |" % p.policy_hash,
         "| المواصفة | %s |" % p.data["spec"], "| يونيكود | %s، صيغة %s |" % (p.data["unicode_version"], p.unicode_form),
         "| ثابتة عند التكرار | %s (مختبرة) |" % ("نعم" if p.idempotent else "لا"),
         "| الحالة | إصدار تجريبي، arabic-normalize %s |" % an.__version__,
         "| الترخيص | CC BY 4.0 لملف السياسة، بيانات لابز |", "",
         "## الاستخدام", "", u[2] + " " + u[3], "",
         "## المراحل بالترتيب", "", "| # | المرحلة | الوضع | الأثر |", "|---|---|---|---|"]
    for i, (k, v) in enumerate(stage_rows(p), 1):
        L.append("| %d | %s (`%s`) | `%s` | %s |" % (i, STAGE_AR[k], k, v, EFFECT[(k, v)][1]))
    L += ["", "## القواعد الفاقدة للمعلومات", ""]
    L += ["- `%s`" % x for x in lossy] or ["لا توجد: لا يتغير أي حرف."]
    L += ["", "يُسجَّل كل تغيير فاقد للمعلومات في سجل التغييرات مع `lossy: true`، ويظهر في قائمة `lossy_flags`.", "",
          "## أمثلة من حالات الاختبار (ناتج محسوب)", "", "| الحالة | المدخل | الناتج | القواعد |", "|---|---|---|---|"]
    for fx, r in examples:
        L.append("| %s | %s | %s | %s |" % (fx["fixture_id"], esc(fx["input"]), esc(r.text_norm) or "(فارغ)", ", ".join(r.rules)))
    L += ["", "## القيود", ""] + ["- " + x for x in LIMITS[pid][1]]
    L += ["", "## طريقة الإشارة", "", "وُحِّد النص بسياسة `%s` (البصمة `%s`)، مكتبة arabic-normalize %s، بيانات لابز." % (pid, p.policy_hash, an.__version__),
          "", "النسخة الإنجليزية: [%s.md](%s.md). تعريف المراحل: [SPEC.md](../SPEC.md). أُنشئت هذه الصفحة بالبرنامج `scripts/make_docs.py`." % (pid, pid),
          "", "</div>", ""]
    return "\n".join(L)


def readme_example():
    r = an.normalize_detailed(WORKED)
    ch = [c for c in r.changes if c.rule_id == "alef_maqsura.to_yeh"][0]
    lines = ["```python", ">>> from arabic_normalize import normalize, normalize_detailed",
             '>>> text = "%s"' % WORKED,
             ">>> normalize(text)                        # bayanat-norm-v1, the default", repr(an.normalize(WORKED)),
             '>>> normalize(text, "asr-eval-v1")         # for WER/CER scoring', repr(an.normalize(WORKED, "asr-eval-v1")),
             '>>> normalize(text, "raw-safe-v1")         # cleaning only, letters untouched', repr(an.normalize(WORKED, "raw-safe-v1")),
             ">>> r = normalize_detailed(text)", ">>> r.lossy_flags", repr(r.lossy_flags), ">>> r.flags", repr(r.flags),
             ">>> round(r.diacritization_ratio, 3)", repr(round(r.diacritization_ratio, 3)),
             ">>> r.policy_hash", repr(r.policy_hash),
             '>>> [c for c in r.changes if c.rule_id == "alef_maqsura.to_yeh"]', repr([ch]), "```", "",
             "```console", '$ echo "%s" | arnorm normalize' % WORKED, an.normalize(WORKED),
             '$ echo "%s" | arnorm normalize --policy asr-eval-v1' % WORKED, an.normalize(WORKED, "asr-eval-v1"), "```"]
    return "\n".join(lines)


def readme_policies():
    L = ["| Policy | SHA-256 | Use | Lossy rules | Card |", "|---|---|---|---|---|"]
    for pid in ["bayanat-norm-v1", "asr-eval-v1", "raw-safe-v1"]:
        p = an.load_policy(pid)
        L.append("| `%s` | `%s` | %s | %s | [EN](docs/policies/%s.md) · [AR](docs/policies/%s.ar.md) |" % (
            pid, p.policy_hash, USE[pid][0], ", ".join(policy_lossy(p)) or "none", pid, pid))
    return "\n".join(L)


def js_counts():
    """JavaScript port counts (js/conformance.json), or None when the port is absent."""
    if not os.path.exists(JS_COUNTS):
        return None
    with open(JS_COUNTS, encoding="utf-8") as f:
        js = json.load(f)
    if js["lib_version"] != an.__version__:
        raise SystemExit("js/conformance.json is for %s, the package is %s" % (js["lib_version"], an.__version__))
    return js


def js_all_pass(js):
    if js is None:
        return False
    ref = js["python_reference"]
    return (all(v["fixtures"] == v["passing_js"] for v in js["by_split"].values())
            and js["rejected"]["fixtures"] == js["rejected"]["rejected_with_documented_reason"]
            and ref["cases"] == ref["cases_identical"] and ref["diffs"] == ref["diffs_identical"])


def counts_block(dev, acc, rej, res, rej_ok):
    by_split = {"dev": [0, 0], "acceptance": [0, 0]}
    by_policy = {}
    for fx, r, ok in res:
        by_split[fx["split"]][0] += 1
        by_split[fx["split"]][1] += ok
        bp = by_policy.setdefault(fx["policy_id"], [0, 0])
        bp[0] += 1
        bp[1] += ok
    js = js_counts()
    if js is None:
        L = ["| Split | Fixtures | Passing (Python) |", "|---|---|---|",
             "| dev | %d | %d |" % tuple(by_split["dev"]), "| acceptance | %d | %d |" % tuple(by_split["acceptance"]),
             "| rejected inputs | %d | %d |" % (len(rej), rej_ok), ""]
    else:
        L = ["| Split | Fixtures | Passing (Python) | Passing (JavaScript) |", "|---|---|---|---|",
             "| dev | %d | %d | %d |" % (by_split["dev"][0], by_split["dev"][1], js["by_split"]["dev"]["passing_js"]),
             "| acceptance | %d | %d | %d |" % (by_split["acceptance"][0], by_split["acceptance"][1],
                                              js["by_split"]["acceptance"]["passing_js"]),
             "| rejected inputs | %d | %d | %d |" % (len(rej), rej_ok, js["rejected"]["rejected_with_documented_reason"]), ""]
    L.append("By policy (dev + acceptance): %s. Computed by `scripts/make_docs.py` from the fixture files on %s." % (
        ", ".join("%s %d/%d" % (k, v[1], v[0]) for k, v in sorted(by_policy.items())), DOC_DATE))
    if js is not None:
        ref = js["python_reference"]
        L.append("")
        L.append("JavaScript port (`js/`): %d of %d reference cases (the 80 fixtures under %d policies) and %d of %d policy "
                 "comparisons are identical to the Python engine, including the offset map and change log; counts from "
                 "`js/conformance.json` (`js/scripts/conformance_counts.mjs`)." % (
                     ref["cases_identical"], ref["cases"], ref["policies"], ref["diffs_identical"], ref["diffs"]))
    return "\n".join(L), by_split, by_policy


def changelog_hashes():
    L = []
    for pid in an.list_policies():
        L.append("- `%s`: sha256 `%s`" % (pid, an.load_policy(pid).policy_hash))
    return "\n".join(L)


def replace_block(text, name, body):
    pat = re.compile(r"(<!-- BEGIN:%s -->\n).*?(\n<!-- END:%s -->)" % (name, name), re.S)
    if not pat.search(text):
        raise SystemExit("marker %s not found" % name)
    return pat.sub(lambda m: m.group(1) + body + m.group(2), text)


def claims(by_split, by_policy, rej, rej_ok):
    with open(CENSUS, encoding="utf-8") as f:
        c = json.load(f)
    pypi = {r["name"]: r for r in c["pypi"]}
    npm = {r["name"]: r for r in c["npm_packages"]}
    n_fix = by_split["dev"][0] + by_split["acceptance"][0]
    n_pass = by_split["dev"][1] + by_split["acceptance"][1]
    js = js_counts()
    langs = "Python and JavaScript" if js_all_pass(js) else "Python"
    count_script = "scripts/make_docs.py, js/scripts/conformance_counts.mjs" if js is not None else "scripts/make_docs.py"
    L = ["# CLAIMS.md: arabic-normalize v%s (Bayanat Labs)" % an.__version__, "",
         "Status: `draft` (no superlative is used anywhere). Rules: RULES.md section 10. Generated by `scripts/make_docs.py` on %s from the released files and `evidence/census_2026-10-15.json`." % DOC_DATE, "",
         "## 1. Ledger", "",
         "| Claim ID | Allowed wording (exact) | Unit and counting rule | Our released count | Licence class | As of | Evidence | Count script | Status |",
         "|---|---|---|---|---|---|---|---|---|"]
    for pid in ["bayanat-norm-v1", "asr-eval-v1", "raw-safe-v1"]:
        h = an.load_policy(pid).policy_hash
        L.append('| TL-003-%s | "arabic-normalize (Bayanat Labs, Apache-2.0) applies named, versioned Arabic normalisation policies; any result normalised with %s can be reproduced exactly from policy hash %s. Version %s, %d conformance cases passing in %s, as of %s." | fixtures in tests/fixtures/{dev,acceptance} that pass every assertion | %d of %d | code Apache-2.0; policies and fixtures CC BY 4.0 | %s | tests/fixtures, src/arabic_normalize/policies/%s.json | %s | draft |' % (
            pid, pid, h, an.__version__, n_pass, langs, DOC_DATE, n_pass, n_fix, DOC_DATE, pid, count_script))
    st_path = os.path.join(ROOT, "docs", "stress", "stats.json")
    with open(st_path, encoding="utf-8") as f:
        st = json.load(f)
    n_art = st["articles"]
    n_lossy = st["articles_with_any_lossy"]["bayanat-norm-v1"]
    n_crash = sum(st["crashes"].values())
    L.append('| TL-003-stress-wikipedia | "In a stress test on {:,} Arabic Wikipedia articles, bayanat-norm-v1 made at least one lossy change in {:,} of them ({:.1f}%), with {} crashes." | main-namespace, non-redirect articles of one arwiki dump part ({}), raw wikitext; an article counts when its change log has any lossy rule | {:,} of {:,} | Wikipedia text CC BY-SA 4.0, statistics only, nothing redistributed | {} | docs/stress/stats.json (sha256 {}) | scripts/stress/stress_run.py, scripts/stress/stress_report.py | draft |'.format(
        n_art, n_lossy, 100.0 * n_lossy / n_art, n_crash, st["dump"].get("dated_name", st["dump"]["file"]), n_lossy, n_art,
        st["dump"]["retrieved_at"][:10], sha256_file(st_path)))
    L += ["", "No 'first', 'only', 'largest' or 'best' wording is used. A 'first/only open Arabic normaliser with hash-identified policies and offset maps' claim would need the full RULES.md section 10 search (Hugging Face, Masader, Kaggle, Zenodo, ACL Anthology, arXiv) and is not made.", "",
          "## 2. Name availability (15 Oct 2026)", "",
          "| Registry | Name | HTTP status | Registered |", "|---|---|---|---|"]
    for name in ["arabic-normalize", "arabic-normalizer", "arabic-normaliser", "arabic-normalization", "arnorm"]:
        r = pypi[name]
        L.append("| PyPI JSON API | %s | %s | %s |" % (name, r["http_status"], "yes" if r.get("registered") else "no"))
    L.append("| PyPI Simple API | arabic-normalize | %s | %s |" % (c["pypi_simple"]["http_status"], "no" if c["pypi_simple"]["http_status"] == 404 else "check"))
    for name in ["arabic-normalize", "@bayanat-labs/arabic-normalize"]:
        r = npm[name]
        L.append("| npm registry | %s | %s | %s |" % (name, r["http_status"], ("yes (v%s, %s, %s)" % (r.get("latest"), r.get("license"), (r.get("latest_published") or "")[:10])) if r.get("registered") else "no"))
    L += ["", "The pypi.org web project page answered with a CAPTCHA client challenge on 15 Oct 2026; it was not bypassed, and the JSON and Simple APIs were used instead.", "",
          "## 3. Comparators (registry facts, 15 Oct 2026)", "",
          "| Tool | Registry | Version | Licence (registry) | Last upload |", "|---|---|---|---|---|"]
    for name in ["camel-tools", "pyarabic", "tnkeeh", "qalsadi", "maha"]:
        r = pypi[name]
        L.append("| %s | PyPI | %s | %s | %s |" % (name, r.get("version"), r.get("license") or "; ".join(r.get("classifier_licenses") or []) or "not stated", (r.get("last_upload") or "")[:10]))
    r = npm["arabic-normalize"]
    L.append("| arabic-normalize (third party, unrelated) | npm | %s | %s | %s |" % (r.get("latest"), r.get("license"), (r.get("latest_published") or "")[:10]))
    L += ["", "Apache Lucene's ArabicNormalizer (Apache-2.0) and OpenAI Whisper's BasicTextNormalizer (MIT) are also used for Arabic; they are libraries inside larger projects and are not listed by package here.", "",
          "GitHub repository search (unauthenticated API, sorted by stars), top results:", "",
          "| Query | Total | Top repositories (stars, licence) |", "|---|---|---|"]
    for q in c["github"]:
        top = ", ".join("%s (%s, %s)" % (x["full_name"], x["stars"], x["license"] or "no licence file") for x in q["results"][:5])
        L.append("| %s | %s | %s |" % (q["query"], q["total_count"], top))
    L += ["", "Hugging Face API search:", "", "| Kind | Query | Results |", "|---|---|---|"]
    for q in c["huggingface"]:
        L.append("| %s | %s | %d |" % (q["kind"], q["query"], len(q["results"])))
    L += ["", "Feature comparison: arabic-normalize provides named immutable policies with a SHA-256 identity, an offset map, a change log with lossy flags and pinned Unicode data. For the comparators above, `evidence/census_2026-10-15.json` records a keyword scan of registry descriptions only; it is not evidence that a tool lacks a feature, and no comparative claim is made from it. " + (
              "The JavaScript port (`js/`, npm `@bayanat-labs/arabic-normalize`) gives the same output as the Python engine on every fixture (`js/conformance.json`). The compatibility policies (compat-camel, compat-lucene, compat-whisper, compat-pyarabic) are not part of v0.1." if js_all_pass(js) else
              "The JavaScript port and compatibility policies (compat-camel, compat-lucene, compat-whisper, compat-pyarabic) are not part of v0.1."), "",
          "## 4. Script-computed QA records", "",
          "Every number in these files is computed by the script named next to it from the inputs named there. The hashes identify the exact files the numbers above and the public pages quote.", "",
          "| File | SHA-256 | Produced by | Inputs |", "|---|---|---|---|"] + qa_records() + ["",
          "## 5. Gates", "",
          "- [x] Counts computed by script from the released files (`scripts/make_docs.py`)",
          "- [x] Licence class and date stated with the claim",
          "- [x] No superlative used",
          "- [ ] Founder approval of the claim wording (RULES.md section 13)", ""]
    return "\n".join(L)


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


QA_RECORDS = [
    ("docs/stress/report.md", "scripts/stress/stress_report.py", "the stress_run.py JSON of one arwiki dump part (deleted after the run)"),
    ("docs/stress/stats.json", "scripts/stress/stress_run.py, scripts/stress/stress_report.py", "one arwiki dump part (sha256 in the file)"),
    ("docs/stress/fleurs.md", "scripts/stress/stress_report.py", "the stress_run.py JSON of the FLEURS ar_eg transcripts"),
    ("docs/stress/fleurs.json", "scripts/stress/stress_run.py, scripts/stress/stress_report.py", "FLEURS ar_eg train, dev and test TSV files (sha256 in the file)"),
    ("docs/stress/tanzil.md", "scripts/stress/stress_report.py", "the stress_run.py JSON of the Tanzil Uthmani text"),
    ("docs/stress/tanzil.json", "scripts/stress/stress_run.py, scripts/stress/stress_report.py", "Tanzil Uthmani text with aya numbers (sha256 in the file)"),
    ("docs/compat/agreement.json", "scripts/compat/compare.py with scripts/compat/harness/ (PyArabic harness kept outside)", "tests/fixtures/{dev,acceptance}, oracle venvs listed in the file"),
    ("docs/compat/README.md", "scripts/compat/compare.py", "docs/compat/agreement.json data"),
    ("docs/compat/fixtures.md", "scripts/compat/compare.py", "docs/compat/agreement.json data"),
]


def qa_records():
    rows = []
    for rel, script, inputs in QA_RECORDS:
        path = os.path.join(ROOT, rel)
        if os.path.exists(path):
            rows.append("| %s | `%s` | %s | %s |" % (rel, sha256_file(path), script, inputs))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    dev, acc, rej, res, rej_ok = fixture_results()
    counts, by_split, by_policy = counts_block(dev, acc, rej, res, rej_ok)
    outputs = {}
    for pid in ["bayanat-norm-v1", "asr-eval-v1", "raw-safe-v1"]:
        outputs["docs/policies/%s.md" % pid] = card(pid, res, "en")
        outputs["docs/policies/%s.ar.md" % pid] = card(pid, res, "ar")
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
        readme = f.read()
    readme = replace_block(readme, "example", readme_example())
    readme = replace_block(readme, "policies", readme_policies())
    readme = replace_block(readme, "counts", counts)
    outputs["README.md"] = readme
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as f:
        outputs["CHANGELOG.md"] = replace_block(f.read(), "hashes", changelog_hashes())
    outputs["CLAIMS.md"] = claims(by_split, by_policy, rej, rej_ok)
    stale = []
    for rel, text in outputs.items():
        path = os.path.join(ROOT, rel)
        cur = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if cur != text:
            stale.append(rel)
            if not a.check:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
    if a.check:
        if stale:
            raise SystemExit("stale generated docs: %s (run scripts/make_docs.py)" % ", ".join(stale))
        print("generated docs are up to date")
    else:
        print("updated: %s" % (", ".join(stale) or "nothing"))
    print("fixtures: dev %d/%d, acceptance %d/%d, rejected %d/%d" % (
        by_split["dev"][1], by_split["dev"][0], by_split["acceptance"][1], by_split["acceptance"][0], rej_ok, len(rej)))


if __name__ == "__main__":
    main()

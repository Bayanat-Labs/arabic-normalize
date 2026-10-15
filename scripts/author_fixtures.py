#!/usr/bin/env python3
# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Hand-authored pilot conformance fixtures for arabic-normalize (80 cases: 64 dev + 16 acceptance)
and explicit rejected-input examples.

The expected values below were written by hand from docs/SPEC.md before any engine code existed
(git history: fixtures are committed before src/arabic_normalize/engine.py). This script only
serialises them; it never calls the engine. Text is original Bayanat Labs text written for the
fixtures: no corpus text, no personal data. Every fixture is labelled synthetic/illustrative.

Fixture data (tests/fixtures/**) is licensed CC BY 4.0 (Bayanat Labs); this script is Apache-2.0.

Run: python scripts/author_fixtures.py   (writes tests/fixtures/{dev,acceptance,rejected}/*.jsonl and
tests/fixtures/PROVENANCE.jsonl)
"""
import hashlib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tests", "fixtures")
AUTHOR = "Bayanat Labs (arabic-normalize maintainers; pilot fixture set)"
CREATED = "2026-10-15"
LABEL = "synthetic/illustrative, authored by Bayanat Labs"

B, A, R = "bayanat-norm-v1", "asr-eval-v1", "raw-safe-v1"


def fx(fid, family, policy, inp, out, rules=(), lossy=(), flags=(), offsets=None, rejected=None, ratio=None,
       en="", ar=""):
    return {
        "fixture_id": fid, "family": family, "policy_id": policy,
        "input": inp, "expected_output": out,
        "expected_rules": sorted(set(rules)), "expected_lossy_flags": sorted(set(lossy)),
        "expected_flags": sorted(set(flags)), "expected_offset_map": offsets,
        "expected_rejected_spans": rejected if rejected is not None else [],
        "expected_diacritization_ratio": ratio,
        "rationale_en": en, "rationale_ar": ar,
    }


AV, AM, TM = "alef_variants.map", "alef_maqsura.to_yeh", "taa_marbuta.to_heh"
DS, TS, NFC = "diacritics.strip", "tatweel.strip", "canonical_order.nfc"
PFM, DIG, PS, WC = "presentation_forms.map", "digits.to_ascii", "punctuation.strip", "whitespace.collapse"
TMF, LHF = "taa_marbuta.flag", "ligatures_honorific.flag"

DEV = [
    # --- diacritics (harakat) ---------------------------------------------------------------
    fx("dev-001", "diacritics", B, "\u0643\u064e\u062a\u064e\u0628\u064e", "\u0643\u062a\u0628",
       [DS], offsets=[[0, 1], [2, 3], [4, 5]], ratio=1.0,
       en="Fatha on every letter is removed; offsets point back to the base letters.",
       ar="تُحذف الفتحة من كل حرف، وتشير الإزاحات إلى الحروف الأصلية."),
    fx("dev-002", "diacritics", B, "\u0645\u064f\u062f\u064e\u0631\u0650\u0651\u0633\u064c", "\u0645\u062f\u0631\u0633",
       [DS], ratio=1.25,
       en="Damma, fatha, kasra+shadda (canonical order) and dammatan removed; 5 marks over 4 letters.",
       ar="تُحذف الضمة والفتحة والكسرة مع الشدة وتنوين الضم؛ خمس علامات على أربعة حروف."),
    fx("dev-003", "diacritics", B, "\u0645\u064f\u0639\u064e\u0644\u0651\u064e\u0645", "\u0645\u0639\u0644\u0645",
       [NFC, DS], ratio=1.0,
       en="Shadda typed before fatha is reordered by NFC (fatha ccc 30 < shadda ccc 33), then all harakat are removed.",
       ar="الشدة المكتوبة قبل الفتحة يعيد NFC ترتيبها، ثم تُحذف الحركات كلها."),
    fx("dev-004", "diacritics", R, "\u0645\u064f\u0639\u064e\u0644\u0651\u064e\u0645",
       "\u0645\u064f\u0639\u064e\u0644\u064e\u0651\u0645", [NFC],
       offsets=[[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [6, 7], [5, 6], [7, 8]], ratio=1.0,
       en="raw-safe keeps harakat but puts them in canonical order; the offset map shows the swapped marks.",
       ar="سياسة التنظيف الآمن تُبقي الحركات وترتبها ترتيبًا قانونيًا؛ وتُظهر خريطة الإزاحات تبادل العلامتين."),
    fx("dev-005", "diacritics", B, "\u0642\u064e\u0644\u0652\u0628\u064b\u0627", "\u0642\u0644\u0628\u0627",
       [DS], ratio=0.75,
       en="Sukun and fathatan are harakat and are removed; the alef after tanween stays.",
       ar="السكون وتنوين الفتح من الحركات فيُحذفان، وتبقى الألف بعد التنوين."),
    fx("dev-006", "diacritics", A, "\u0627\u0644\u0639\u0650\u0644\u0652\u0645\u064f \u0646\u064f\u0648\u0631\u064c",
       "\u0627\u0644\u0639\u0644\u0645 \u0646\u0648\u0631", [DS],
       en="asr-eval removes harakat like bayanat-norm-v1.",
       ar="سياسة تقييم التعرف على الكلام تحذف الحركات كما في التوحيد القياسي."),
    # --- tatweel ---------------------------------------------------------------------------
    fx("dev-007", "tatweel", B, "\u062c\u0645\u0640\u0640\u0640\u064a\u0644", "\u062c\u0645\u064a\u0644",
       [TS], offsets=[[0, 1], [1, 2], [5, 6], [6, 7]],
       en="A run of three tatweels inside a word is removed.",
       ar="تُحذف ثلاث تطويلات متتالية داخل الكلمة."),
    fx("dev-008", "tatweel", B, "\u0643\u0640\u064e\u062a\u0628", "\u0643\u062a\u0628", [TS, DS],
       en="A fatha written on a tatweel is removed together with the tatweel.",
       ar="تُحذف الفتحة المكتوبة على التطويل مع التطويل نفسه."),
    fx("dev-009", "tatweel", R, "\u0633\u0640\u0644\u0627\u0645", "\u0633\u0640\u0644\u0627\u0645", [],
       en="raw-safe keeps tatweel.", ar="سياسة التنظيف الآمن تُبقي التطويل."),
    # --- alef and hamza variants ----------------------------------------------------------------
    fx("dev-010", "alef_hamza", B, "\u0623\u0645\u0633 \u0625\u0644\u0649 \u0622\u062e\u0631",
       "\u0627\u0645\u0633 \u0627\u0644\u064a \u0627\u062e\u0631", [AV, AM], lossy=[AV, AM],
       en="Hamza-above, hamza-below and madda alefs map to bare alef; alef maqsura maps to yeh. Both are lossy.",
       ar="تتحول الألف ذات الهمزة فوقها وتحتها والممدودة إلى ألف مجردة، والألف المقصورة إلى ياء؛ وكلاهما تغيير فاقد للمعلومات."),
    fx("dev-011", "alef_hamza", B, "\u0671\u0644\u0643\u062a\u0627\u0628", "\u0627\u0644\u0643\u062a\u0627\u0628",
       [AV], lossy=[AV], en="Alef wasla maps to bare alef.", ar="تتحول همزة الوصل إلى ألف مجردة."),
    fx("dev-012", "alef_hamza", B, "\u0627\u0654\u0645\u0631", "\u0627\u0645\u0631", [NFC, AV], lossy=[AV],
       offsets=[[0, 2], [2, 3], [3, 4]],
       en="Decomposed alef + combining hamza composes to U+0623 under NFC, then maps to bare alef; the alef maps to both source code points.",
       ar="الألف مع الهمزة المركبة تُدمج بـ NFC في حرف واحد ثم تتحول إلى ألف مجردة، وتشير إزاحتها إلى المحرفين الأصليين."),
    fx("dev-013", "alef_hamza", R, "\u0627\u0654\u0645\u0631", "\u0623\u0645\u0631", [NFC],
       en="raw-safe composes the decomposed sequence to U+0623 and keeps the hamza.",
       ar="سياسة التنظيف الآمن تدمج التسلسل المفكك في الحرف أ وتُبقي الهمزة."),
    fx("dev-014", "alef_hamza", A, "\u0625\u0646\u0651", "\u0627\u0646", [AV, DS], lossy=[AV],
       en="asr-eval maps hamza-below alef and removes shadda.", ar="تتحول إ إلى ا وتُحذف الشدة."),
    fx("dev-015", "alef_hamza", B, "\u0625\u0650\u0646\u064e\u0651 \u0623\u064e\u0646\u064e\u0651",
       "\u0627\u0646 \u0627\u0646", [AV, DS], lossy=[AV],
       en="Two different words (inna, anna) become identical: this is why alef_variants.map is lossy.",
       ar="كلمتان مختلفتان (إنّ وأنّ) تصبحان متطابقتين؛ ولهذا يُعد توحيد الألف تغييرًا فاقدًا للمعلومات."),
    fx("dev-016", "alef_hamza", B, "\u0633\u0645\u0627\u0621 \u0645\u0622\u0630\u0646",
       "\u0633\u0645\u0627\u0621 \u0645\u0627\u0630\u0646", [AV], lossy=[AV],
       en="Hamza on the line (U+0621) is kept; alef madda maps to bare alef.",
       ar="تبقى الهمزة على السطر، وتتحول الألف الممدودة إلى ألف مجردة."),
    # --- alef maqsura and yeh ------------------------------------------------------------------
    fx("dev-017", "alef_maqsura", B, "\u0639\u0644\u0649", "\u0639\u0644\u064a", [AM], lossy=[AM],
       en="The preposition 'ala becomes identical to the name Ali: alef_maqsura.to_yeh is lossy.",
       ar="حرف الجر «على» يصبح مطابقًا للاسم «علي»؛ ولهذا يُعد التحويل فاقدًا للمعلومات."),
    fx("dev-018", "alef_maqsura", B, "\u0645\u0635\u0637\u0641\u0649", "\u0645\u0635\u0637\u0641\u064a", [AM],
       lossy=[AM], en="Names ending in alef maqsura change spelling in text_norm; text_raw keeps the original.",
       ar="تتغير كتابة الأسماء المنتهية بألف مقصورة في الحقل الموحد، ويحفظ الحقل الخام الأصل."),
    fx("dev-019", "alef_maqsura", R, "\u0645\u0633\u062a\u0634\u0641\u0649", "\u0645\u0633\u062a\u0634\u0641\u0649", [],
       en="raw-safe keeps alef maqsura.", ar="سياسة التنظيف الآمن تُبقي الألف المقصورة."),
    fx("dev-020", "alef_maqsura", A, "\u0645\u0628\u0646\u0649 \u0648\u0645\u0639\u0646\u0649",
       "\u0645\u0628\u0646\u064a \u0648\u0645\u0639\u0646\u064a", [AM], lossy=[AM],
       en="asr-eval maps every alef maqsura to yeh.", ar="سياسة تقييم الكلام تحوّل كل ألف مقصورة إلى ياء."),
    # --- taa marbuta --------------------------------------------------------------------------
    fx("dev-021", "taa_marbuta", B, "\u0645\u062f\u0631\u0633\u0629", "\u0645\u062f\u0631\u0633\u0629", [],
       flags=[TMF], ratio=0.0,
       en="bayanat-norm-v1 keeps taa marbuta and raises the taa_marbuta.flag (RULES.md 5.1).",
       ar="التوحيد القياسي يُبقي التاء المربوطة ويرفع علامة التنبيه الخاصة بها."),
    fx("dev-022", "taa_marbuta", A, "\u0645\u062f\u0631\u0633\u0629 \u062c\u0645\u064a\u0644\u0629",
       "\u0645\u062f\u0631\u0633\u0647 \u062c\u0645\u064a\u0644\u0647", [TM], lossy=[TM],
       en="asr-eval folds taa marbuta to heh (lossy).", ar="سياسة تقييم الكلام تحوّل التاء المربوطة إلى هاء، وهو تغيير فاقد للمعلومات."),
    fx("dev-023", "taa_marbuta", R, "\u0645\u0643\u062a\u0628\u0629", "\u0645\u0643\u062a\u0628\u0629", [],
       en="raw-safe keeps taa marbuta and raises no flag.", ar="سياسة التنظيف الآمن تُبقي التاء المربوطة دون علامة تنبيه."),
    fx("dev-024", "taa_marbuta", B, "\u0631\u0633\u0627\u0644\u0629\u064c", "\u0631\u0633\u0627\u0644\u0629", [DS],
       flags=[TMF], en="Tanween on taa marbuta is removed; the letter is kept and flagged.",
       ar="يُحذف التنوين على التاء المربوطة، ويبقى الحرف مع علامة التنبيه."),
    # --- hamza carriers --------------------------------------------------------------------------
    fx("dev-025", "hamza_carriers", B, "\u0645\u0624\u062a\u0645\u0631 \u0648\u0633\u0627\u0626\u0644",
       "\u0645\u0624\u062a\u0645\u0631 \u0648\u0633\u0627\u0626\u0644", [],
       en="Hamza on waw and on yeh is kept in bayanat-norm-v1.", ar="تبقى الهمزة على الواو وعلى الياء في التوحيد القياسي."),
    fx("dev-026", "hamza_carriers", A, "\u0633\u0624\u0627\u0644", "\u0633\u0624\u0627\u0644", [],
       en="asr-eval also keeps hamza carriers (folding them is reserved for search-v1).",
       ar="سياسة تقييم الكلام تُبقي الهمزة على الواو أيضًا، ويُترك طيّها لسياسة البحث."),
    # --- Persian and Urdu lookalikes ----------------------------------------------------------------
    fx("dev-027", "persian_urdu", B, "\u06a9\u062a\u0627\u0628", "\u06a9\u062a\u0627\u0628", [],
       en="Keheh (U+06A9) is not mapped to kaf: mapping would corrupt Persian and Urdu text.",
       ar="لا تُحوَّل الكاف الفارسية إلى كاف عربية، لأن ذلك يُفسد النص الفارسي والأردي."),
    fx("dev-028", "persian_urdu", B, "\u0641\u0627\u0631\u0633\u06cc", "\u0641\u0627\u0631\u0633\u06cc", [],
       en="Farsi yeh (U+06CC) is kept; it is not alef maqsura.", ar="تبقى الياء الفارسية كما هي؛ فهي ليست ألفًا مقصورة."),
    fx("dev-029", "persian_urdu", B, "\u0634\u06c1\u0631", "\u0634\u06c1\u0631", [],
       en="Heh goal (U+06C1) is kept.", ar="تبقى الهاء الأردية (هاء گول) كما هي."),
    # --- digits ---------------------------------------------------------------------------------
    fx("dev-030", "digits", B, "\u0661\u0662\u0663", "123", [DIG], offsets=[[0, 1], [1, 2], [2, 3]],
       en="Arabic-Indic digits map to ASCII one to one.", ar="تتحول الأرقام العربية المشرقية إلى أرقام لاتينية رقمًا برقم."),
    fx("dev-031", "digits", B, "\u06f4\u06f5\u06f6", "456", [DIG],
       en="Extended Arabic-Indic (Persian) digits map to ASCII.", ar="تتحول الأرقام الفارسية إلى أرقام لاتينية."),
    fx("dev-032", "digits", R, "\u0662\u0660\u0662\u0666", "\u0662\u0660\u0662\u0666", [],
       en="raw-safe keeps Arabic-Indic digits.", ar="سياسة التنظيف الآمن تُبقي الأرقام المشرقية."),
    fx("dev-033", "digits", B, "\u0663\u066b\u0665", "3\u066b5", [DIG],
       en="Digits map to ASCII but the Arabic decimal separator is punctuation and is kept by bayanat-norm-v1.",
       ar="تتحول الأرقام إلى لاتينية، أما الفاصلة العشرية العربية فهي علامة ترقيم يُبقيها التوحيد القياسي."),
    # --- presentation forms ------------------------------------------------------------------------
    fx("dev-034", "presentation_forms", B, "\ufefb", "\u0644\u0627", [PFM], offsets=[[0, 1], [0, 1]],
       en="The lam-alef ligature becomes two letters; both map back to the single source code point.",
       ar="يتحول حرف لام ألف المركب إلى حرفين، ويشير كلاهما إلى المحرف الأصلي الواحد."),
    fx("dev-035", "presentation_forms", B, "\ufef7", "\u0644\u0627", [PFM, AV], lossy=[AV],
       offsets=[[0, 1], [0, 1]],
       en="Lam-alef with hamza: NFKC gives lam + U+0623, then the alef rule removes the hamza.",
       ar="لام ألف مع الهمزة: يعطي التفكيك لامًا وألفًا مهموزة، ثم تُحذف الهمزة بقاعدة الألف."),
    fx("dev-036", "presentation_forms", B, "\ufe91\ufef4\ufe96", "\u0628\u064a\u062a", [PFM],
       en="Initial, medial and final contextual forms map to the base letters.",
       ar="تتحول أشكال الحروف الأولية والوسطية والنهائية إلى الحروف الأساسية."),
    fx("dev-037", "presentation_forms", R, "\ufefb", "\ufefb", [],
       en="raw-safe keeps presentation forms (NFC does not change them).",
       ar="سياسة التنظيف الآمن تُبقي أشكال العرض كما هي، لأن NFC لا يغيرها."),
    fx("dev-038", "presentation_forms", A, "\ufee3\ufeaa\ufead\ufeb3\ufe94", "\u0645\u062f\u0631\u0633\u0647",
       [PFM, TM], lossy=[TM],
       en="A word written in presentation forms is mapped, then taa marbuta is folded by asr-eval.",
       ar="كلمة مكتوبة بأشكال العرض تُحوَّل إلى حروفها، ثم تُحوَّل التاء المربوطة إلى هاء."),
    # --- honorific ligatures ---------------------------------------------------------------------------
    fx("dev-039", "ligatures_honorific", B, "\u0627\u0644\u0646\u0628\u064a \ufdfa",
       "\u0627\u0644\u0646\u0628\u064a \ufdfa", [], flags=[LHF],
       en="U+FDFA is kept as one code point and flagged; full NFKC would expand it to four words.",
       ar="يبقى الرمز ﷺ محرفًا واحدًا مع علامة تنبيه؛ أما NFKC الكامل فيفكه إلى أربع كلمات."),
    fx("dev-040", "ligatures_honorific", B, "\u0628\u0633\u0645 \ufdf2", "\u0628\u0633\u0645 \ufdf2", [],
       flags=[LHF], en="U+FDF2 (Allah ligature) is kept and flagged.", ar="يبقى رمز لفظ الجلالة المركب مع علامة تنبيه."),
    fx("dev-041", "ligatures_honorific", R, "\ufdfa", "\ufdfa", [],
       en="raw-safe keeps honorific ligatures without a flag.", ar="سياسة التنظيف الآمن تُبقي الرموز المركبة دون علامة تنبيه."),
    # --- zero-width characters ---------------------------------------------------------------------
    fx("dev-042", "zero_width", B, "\u0645\u06cc\u200c\u062e\u0648\u0627\u0647\u0645",
       "\u0645\u06cc\u200c\u062e\u0648\u0627\u0647\u0645", [],
       en="A Persian ZWNJ between two dual-joining letters is meaningful and is kept.",
       ar="يبقى الفاصل غير الواصل في الفارسية بين حرفين يتصلان من الجهتين، لأن له أثرًا في الكتابة."),
    fx("dev-043", "zero_width", B, "\u062f\u0627\u0631\u200c\u0647\u0627", "\u062f\u0627\u0631\u0647\u0627",
       ["bidi_zw.zwnj"],
       en="A ZWNJ after reh (right-joining only) prevents no join and is removed.",
       ar="يُحذف الفاصل غير الواصل بعد الراء، لأن الراء لا تتصل بما بعدها أصلًا."),
    fx("dev-044", "zero_width", B, "\u0643\u062a\u0627\u0628\u200b \u062c\u062f\u064a\u062f",
       "\u0643\u062a\u0627\u0628 \u062c\u062f\u064a\u062f", ["bidi_zw.zwsp"],
       en="A zero-width space is removed.", ar="تُحذف المسافة الصفرية العرض."),
    fx("dev-045", "zero_width", B, "\u0647\u200d \u0628", "\u0647 \u0628", ["bidi_zw.zwj"],
       en="A ZWJ used only to force a joining form in Arabic is removed (it is not part of an emoji sequence).",
       ar="يُحذف الواصل الصفري المستخدم لإظهار شكل الاتصال فقط، لأنه ليس جزءًا من تسلسل رموز تعبيرية."),
    fx("dev-046", "zero_width", B, "\u0643\u062a\u0627\u0628\u064f\u200c\u0647\u0627",
       "\u0643\u062a\u0627\u0628\u200c\u0647\u0627", [DS],
       en="The ZWNJ context skips the damma, so the ZWNJ between beh and heh is meaningful and kept; the damma is removed.",
       ar="يتخطى فحص السياق الضمة، فيبقى الفاصل غير الواصل بين الباء والهاء، وتُحذف الضمة."),
    # --- bidi controls and BOM ---------------------------------------------------------------------------
    fx("dev-047", "bidi_bom", B, "\u200f\u0645\u0631\u062d\u0628\u0627\u200f", "\u0645\u0631\u062d\u0628\u0627",
       ["bidi_zw.bidi_control"], en="Right-to-left marks are removed.", ar="تُحذف علامات الاتجاه من اليمين إلى اليسار."),
    fx("dev-048", "bidi_bom", B, "\ufeff\u0646\u0635", "\u0646\u0635", ["strip_controls.bom"],
       en="A leading byte-order mark is removed.", ar="تُحذف علامة ترتيب البايتات في بداية النص."),
    fx("dev-049", "bidi_bom", R, "\u0627\u0644\u0646\u0633\u062e\u0629 \u202bv2\u202c",
       "\u0627\u0644\u0646\u0633\u062e\u0629 v2", ["bidi_zw.bidi_control"],
       en="raw-safe removes embedding controls (RLE, PDF) and changes nothing else.",
       ar="سياسة التنظيف الآمن تحذف محارف التضمين الاتجاهي ولا تغير شيئًا آخر."),
    fx("dev-050", "bidi_bom", A, "\u0627\u0644\u0633\u0627\u0639\u0629 \u0663\u200e:\u0663\u0660",
       "\u0627\u0644\u0633\u0627\u0639\u0647 3 30", ["bidi_zw.bidi_control", DIG, PS, TM], lossy=[TM],
       en="asr-eval: LRM removed, digits to ASCII, the colon becomes a space, taa marbuta folded.",
       ar="تُحذف علامة الاتجاه، وتتحول الأرقام، وتصبح النقطتان مسافة، وتتحول التاء المربوطة إلى هاء."),
    # --- punctuation ------------------------------------------------------------------------------
    fx("dev-051", "punctuation", B,
       "\u0646\u0639\u0645\u060c \u0634\u0643\u0631\u0627\u061b \u0647\u0644 \u0623\u0646\u062a \u0628\u062e\u064a\u0631\u061f",
       "\u0646\u0639\u0645\u060c \u0634\u0643\u0631\u0627\u061b \u0647\u0644 \u0627\u0646\u062a \u0628\u062e\u064a\u0631\u061f",
       [AV], lossy=[AV], en="bayanat-norm-v1 keeps Arabic punctuation.", ar="التوحيد القياسي يُبقي علامات الترقيم العربية."),
    fx("dev-052", "punctuation", A,
       "\u0646\u0639\u0645\u060c \u0634\u0643\u0631\u0627\u061b \u0647\u0644 \u0623\u0646\u062a \u0628\u062e\u064a\u0631\u061f",
       "\u0646\u0639\u0645 \u0634\u0643\u0631\u0627 \u0647\u0644 \u0627\u0646\u062a \u0628\u062e\u064a\u0631",
       [AV, PS, WC], lossy=[AV],
       en="asr-eval turns punctuation into spaces, collapses the double spaces and trims the end.",
       ar="تتحول علامات الترقيم إلى مسافات، وتُدمج المسافات المزدوجة، ويُقص الفراغ في النهاية."),
    fx("dev-053", "punctuation", A, "\u0665\u0660\u066a", "50", [DIG, PS, WC],
       en="The Arabic percent sign is punctuation (Po): it becomes a space that is then trimmed.",
       ar="علامة النسبة المئوية العربية علامة ترقيم، فتصبح مسافة ثم تُقص."),
    fx("dev-054", "punctuation", B, "\u0642\u0627\u0644: \u00ab\u0625\u0644\u0649 \u0627\u0644\u0644\u0642\u0627\u0621\u00bb",
       "\u0642\u0627\u0644: \u00ab\u0627\u0644\u064a \u0627\u0644\u0644\u0642\u0627\u0621\u00bb", [AV, AM], lossy=[AV, AM],
       en="Colon and guillemets are kept by bayanat-norm-v1; letters inside the quotes are normalised.",
       ar="تبقى النقطتان وعلامتا التنصيص، وتُوحَّد الحروف داخل الاقتباس."),
    # --- mixed Latin ---------------------------------------------------------------------------------
    fx("dev-055", "mixed_latin", B, "\u0646\u0645\u0648\u0630\u062c GPT-4 \u062c\u062f\u064a\u062f",
       "\u0646\u0645\u0648\u0630\u062c GPT-4 \u062c\u062f\u064a\u062f", [],
       en="Latin letters, ASCII digits and the hyphen are untouched.", ar="لا تتغير الحروف اللاتينية والأرقام اللاتينية والشرطة."),
    fx("dev-056", "mixed_latin", A, "\u0627\u0633\u062a\u062e\u062f\u0645\u062a Python \u0648 PyTorch.",
       "\u0627\u0633\u062a\u062e\u062f\u0645\u062a Python \u0648 PyTorch", [PS, WC],
       en="asr-eval keeps Latin case (latin_case: keep); the final full stop becomes a space and is trimmed.",
       ar="تحتفظ سياسة تقييم الكلام بحالة الحروف اللاتينية، وتصبح النقطة الأخيرة مسافة ثم تُقص."),
    fx("dev-057", "mixed_latin", R, "cafe\u0301 \u0639\u0631\u0628\u064a", "caf\u00e9 \u0639\u0631\u0628\u064a", [NFC],
       en="NFC composes e + combining acute into U+00E9.", ar="يدمج NFC الحرف e مع علامة النبرة في محرف واحد."),
    # --- Quranic marks and superscript alef ---------------------------------------------------------
    fx("dev-058", "quranic_superscript", B, "\u0647\u0670\u0630\u0627", "\u0647\u0630\u0627",
       ["superscript_alef.strip"], ratio=1.0 / 3.0,
       en="The superscript (dagger) alef is removed, giving the standard spelling.",
       ar="تُحذف الألف الخنجرية فينتج الرسم المعتاد للكلمة."),
    fx("dev-059", "quranic_superscript", B, "\u0642\u0627\u0644\u064e\u06d6 \u0646\u0639\u0645\u06da",
       "\u0642\u0627\u0644 \u0646\u0639\u0645", [DS, "quranic_marks.strip"],
       en="Small high Quranic annotation marks (U+06D6, U+06DA) are removed with the harakat.",
       ar="تُحذف علامات الضبط القرآنية الصغيرة مع الحركات."),
    fx("dev-060", "quranic_superscript", A, "\u0671\u0644\u0652\u0643\u0650\u062a\u064e\u0670\u0628\u064f",
       "\u0627\u0644\u0643\u062a\u0628", [AV, DS, "superscript_alef.strip"], lossy=[AV], ratio=1.0,
       en="Uthmani-style spelling: removing the dagger alef gives the consonantal skeleton, not the modern spelling with a full alef.",
       ar="في الرسم العثماني يؤدي حذف الألف الخنجرية إلى الهيكل الحرفي دون ألف، لا إلى الرسم الحديث بالألف."),
    fx("dev-061", "quranic_superscript", R, "\u0646\u0639\u0645\u06da", "\u0646\u0639\u0645\u06da", [],
       en="raw-safe keeps Quranic marks.", ar="سياسة التنظيف الآمن تُبقي العلامات القرآنية."),
    # --- whitespace --------------------------------------------------------------------------------
    fx("dev-062", "whitespace", A, "  \u0643\u0644\u0645\u0629\t\t\u0623\u062e\u0631\u0649 \n ",
       "\u0643\u0644\u0645\u0647 \u0627\u062e\u0631\u064a", [AV, AM, TM, WC], lossy=[AV, AM, TM],
       offsets=[[2, 3], [3, 4], [4, 5], [5, 6], [6, 8], [8, 9], [9, 10], [10, 11], [11, 12]],
       en="Leading and trailing whitespace is removed and the tab run becomes one space mapped to both tabs.",
       ar="يُحذف الفراغ في البداية والنهاية، ويصبح تتابع علامتي الجدولة مسافة واحدة تشير إليهما."),
    fx("dev-063", "whitespace", B, "\u0643\u0644\u0645\u0629\t\u0643\u0644\u0645\u0629",
       "\u0643\u0644\u0645\u0629\t\u0643\u0644\u0645\u0629", [], flags=[TMF],
       en="bayanat-norm-v1 keeps whitespace as written.", ar="التوحيد القياسي يُبقي المسافات كما كُتبت."),
    # --- rejected spans ------------------------------------------------------------------------------
    fx("dev-064", "rejected_span", B, "\u0646\u0635\u0007\u0646\u0635", "\u0646\u0635\u0646\u0635",
       ["reject_invalid.control"], rejected=[{"start": 2, "end": 3, "reason": "control"}],
       en="A BEL control character is dropped and reported in rejected_spans.",
       ar="يُحذف محرف التحكم BEL ويُسجَّل في قائمة المقاطع المرفوضة."),
]

ACCEPTANCE = [
    fx("acc-001", "emoji_zwj", B, "\u0639\u0627\u0626\u0644\u0629 \U0001f468\u200d\U0001f469\u200d\U0001f467 \u0633\u0639\u064a\u062f\u0629",
       "\u0639\u0627\u0626\u0644\u0629 \U0001f468\u200d\U0001f469\u200d\U0001f467 \u0633\u0639\u064a\u062f\u0629", [], flags=[TMF],
       en="ZWJs inside an emoji ZWJ sequence are meaningful and kept.",
       ar="يبقى الواصل الصفري داخل تسلسل الرموز التعبيرية لأنه جزء منه."),
    fx("acc-002", "emoji_zwj", A, "\U0001f469\U0001f3fd\u200d\U0001f4bb \u0645\u0628\u0631\u0645\u062c\u0629",
       "\U0001f469\U0001f3fd\u200d\U0001f4bb \u0645\u0628\u0631\u0645\u062c\u0647", [TM], lossy=[TM],
       en="The ZWJ check skips the skin-tone modifier; the sequence survives asr-eval.",
       ar="يتخطى الفحص معدِّل لون البشرة، فيبقى التسلسل سليمًا في سياسة تقييم الكلام."),
    fx("acc-003", "bidi_isolates", B, "\u2067\u0627\u0644\u0631\u0645\u0632\u2069 \u061c\u0645\u062b\u0627\u0644",
       "\u0627\u0644\u0631\u0645\u0632 \u0645\u062b\u0627\u0644", ["bidi_zw.bidi_control"],
       en="Bidi isolates (RLI, PDI) and the Arabic letter mark are removed.",
       ar="تُحذف محارف العزل الاتجاهي وعلامة الحرف العربي."),
    fx("acc-004", "pf_marks", B, "\u0628\ufe77\u062a", "\u0628\u062a", [PFM, TS, DS], offsets=[[0, 1], [2, 3]], ratio=0.5,
       en="A medial fatha presentation form maps to tatweel + fatha (NFKC); both are then removed.",
       ar="شكل الفتحة الوسطي يتحول إلى تطويل وفتحة، ثم يُحذف الاثنان."),
    fx("acc-005", "pf_marks", B, "\u0643\u062a\u0627\u0628\u0627\ufe70", "\u0643\u062a\u0627\u0628\u0627 ", [PFM, DS], ratio=0.2,
       en="The isolated fathatan form maps to space + fathatan exactly as NFKC does; the space remains after the mark is removed.",
       ar="شكل تنوين الفتح المنفصل يتحول إلى مسافة وتنوين كما في NFKC، وتبقى المسافة بعد حذف التنوين."),
    fx("acc-006", "arabic_extended_letters", B, "\u0750\u08a0\u0649", "\u0750\u08a0\u064a", [AM], lossy=[AM],
       en="Arabic Supplement and Extended-A letters pass through unchanged; the alef maqsura still maps.",
       ar="حروف الملحق العربي والامتداد أ تمر دون تغيير، وتتحول الألف المقصورة."),
    fx("acc-007", "arabic_compat_outside_pf", B, "\u0675 \U0001ee01", "\u0675 \U0001ee01", [],
       en="High hamza alef (U+0675) and Arabic mathematical beh have compatibility decompositions but are outside the presentation-form ranges, so they are kept (full NFKC would change them).",
       ar="الألف ذات الهمزة العالية والباء الرياضية لهما تفكيك توافقي لكنهما خارج نطاق أشكال العرض، فيبقيان كما هما."),
    fx("acc-008", "format_controls", R, "\u0645\u0639\u00ad\u0644\u0648\u0645\u0627\u062a\u2060\u0646\u0635",
       "\u0645\u0639\u0644\u0648\u0645\u0627\u062a\u0646\u0635", ["strip_controls.format"],
       en="Soft hyphen and word joiner are invisible format controls and are removed even by raw-safe.",
       ar="الواصلة المرنة ومحرف الربط غير المرئي يُحذفان حتى في سياسة التنظيف الآمن."),
    fx("acc-009", "c1_controls", B, "\u0633\u0637\u0631\u0085\u0633\u0637\u0631\u0080", "\u0633\u0637\u0631\u0085\u0633\u0637\u0631",
       ["reject_invalid.control"], rejected=[{"start": 7, "end": 8, "reason": "control"}],
       en="NEL (U+0085) is whitespace and allowed; U+0080 is a C1 control and is rejected.",
       ar="محرف السطر التالي مسافة مسموح بها، أما U+0080 فمحرف تحكم مرفوض."),
    fx("acc-010", "surrogates_nonchars", B, "\u0646\u0635\ud800\u0646\u0635\ufffe", "\u0646\u0635\u0646\u0635",
       ["reject_invalid.lone_surrogate", "reject_invalid.noncharacter"],
       rejected=[{"start": 2, "end": 3, "reason": "lone_surrogate"}, {"start": 5, "end": 6, "reason": "noncharacter"}],
       en="A lone surrogate and a noncharacter are dropped with their reasons.",
       ar="يُحذف بديل منفرد ومحرف غير صالح، ويُسجَّل سبب كل منهما."),
    fx("acc-011", "honorific_signs_extended_marks", B, "\u0631\u0633\u0648\u0644\u0610 \u0639\u0644\u0645\u08f0",
       "\u0631\u0633\u0648\u0644\u0610 \u0639\u0644\u0645", ["quranic_marks.strip"], flags=[LHF],
       en="The combining honorific sign U+0610 is kept and flagged; the open fathatan U+08F0 is a Quranic mark and is removed.",
       ar="تبقى علامة الصلاة المركبة مع علامة تنبيه، ويُحذف تنوين الفتح المفتوح لأنه من العلامات القرآنية."),
    fx("acc-012", "nbsp_ornate", A, "\ufd3f\u0646\u0635\ufd3e\u00a0\u202f\u0622\u062e\u0631",
       "\u0646\u0635 \u0627\u062e\u0631", [PS, WC, AV], lossy=[AV],
       en="Ornate parentheses are punctuation; no-break spaces are whitespace; the run collapses to one space.",
       ar="القوسان المزخرفان علامتا ترقيم، والمسافات غير الفاصلة فراغات تُدمج في مسافة واحدة."),
    fx("acc-013", "decomposed_residue", B, "\u0627\u0640\u0654\u0645\u0644", "\u0627\u0645\u0644", [TS, AV], lossy=[AV],
       offsets=[[0, 1], [3, 4], [4, 5]],
       en="After the tatweel is removed, the combining hamza sits on the alef; the alef rule removes it.",
       ar="بعد حذف التطويل تقع الهمزة المركبة على الألف، فتحذفها قاعدة الألف."),
    fx("acc-014", "final_nfc", B, "\u0634\u0649\u0654", "\u0634\u0626", [AM, "canonical_order.final"], lossy=[AM],
       offsets=[[0, 1], [1, 3]],
       en="Alef maqsura + combining hamza becomes yeh + hamza, which the final NFC pass composes to U+0626.",
       ar="الألف المقصورة مع الهمزة المركبة تصبح ياء مع همزة، فيدمجهما المرور الأخير لـ NFC في الحرف ئ."),
    fx("acc-015", "nfc_compose_reorder", R, "\u06d2\u0654 a\u0302\u0323", "\u06d3 \u1ead", [NFC],
       en="Yeh barree + hamza composes to U+06D3; Latin marks are reordered (220 before 230) and composed to U+1EAD.",
       ar="تُدمج الياء البارية مع الهمزة، ويُعاد ترتيب العلامات اللاتينية ثم تُدمج."),
    fx("acc-016", "digits_separators", A, "\u061c\u06f1\u066c\u06f2\u06f5\u06f0\u066b\u06f5 \u0644\u064a\u0631\u0629",
       "1 250 5 \u0644\u064a\u0631\u0647", ["bidi_zw.bidi_control", DIG, PS, TM], lossy=[TM],
       en="asr-eval splits numbers at Arabic thousands and decimal separators because they are punctuation; documented limitation.",
       ar="تقسم سياسة تقييم الكلام الأعداد عند الفواصل العربية لأنها علامات ترقيم؛ وهذا قيد موثق."),
]

# Explicit rejected inputs (whole input or policy rejected; the call raises InputRejected or PolicyError).
REJECTED = [
    {"fixture_id": "rej-001", "kind": "bytes", "input_hex": "d8a7ff", "expected_reason": "invalid_utf8",
     "rationale_en": "0xFF never occurs in UTF-8."},
    {"fixture_id": "rej-002", "kind": "bytes", "input_hex": "d8a7d8", "expected_reason": "invalid_utf8",
     "rationale_en": "Truncated two-byte sequence at the end."},
    {"fixture_id": "rej-003", "kind": "bytes", "input_hex": "c0af", "expected_reason": "invalid_utf8",
     "rationale_en": "Overlong encoding of '/'."},
    {"fixture_id": "rej-004", "kind": "bytes", "input_hex": "eda080", "expected_reason": "invalid_utf8",
     "rationale_en": "UTF-8 encoded surrogate (CESU-8) is not valid UTF-8."},
    {"fixture_id": "rej-005", "kind": "text_strict", "policy_id": B, "input": "\u0646\u0635\ud800",
     "expected_reason": "lone_surrogate", "rationale_en": "Lone surrogate under strict=True."},
    {"fixture_id": "rej-006", "kind": "text_strict", "policy_id": B, "input": "\u0646\u0635\u0007",
     "expected_reason": "control", "rationale_en": "C0 control BEL under strict=True."},
    {"fixture_id": "rej-007", "kind": "text_strict", "policy_id": R, "input": "\u009b\u0646\u0635",
     "expected_reason": "control", "rationale_en": "C1 control CSI under strict=True."},
    {"fixture_id": "rej-008", "kind": "text_strict", "policy_id": A, "input": "\u0646\u0635\U0010ffff",
     "expected_reason": "noncharacter", "rationale_en": "Noncharacter U+10FFFF under strict=True."},
    {"fixture_id": "rej-009", "kind": "generated_text", "policy_id": B, "generate": {"repeat": "\u0627", "count": 5242881},
     "expected_reason": "over_cap_bytes", "rationale_en": "10,485,762 UTF-8 bytes, 2 bytes over the 10 MiB cap."},
    {"fixture_id": "rej-010", "kind": "generated_records", "policy_id": B, "generate": {"text": "\u0646\u0635", "count": 10001},
     "expected_reason": "over_cap_records", "rationale_en": "10,001 records in one request; the cap is 10,000."},
    {"fixture_id": "rej-011", "kind": "policy_id", "policy_id": "bayanat-norm-v9", "expected_reason": "unknown_policy",
     "rationale_en": "No such built-in policy."},
    {"fixture_id": "rej-012", "kind": "policy", "policy": {"$ref": "https://example.org/remote-policy.json"},
     "expected_reason": "remote_ref_not_allowed", "rationale_en": "Remote references are never resolved."},
    {"fixture_id": "rej-013", "kind": "policy_patch", "base": B, "patch": {"policy_id": "custom-test", "stages.stem_words": "on"},
     "expected_reason": "unknown_stage", "rationale_en": "A stage name that the spec does not define."},
    {"fixture_id": "rej-014", "kind": "policy_patch", "base": B, "patch": {"policy_id": "custom-test", "stages.tatweel": "explode"},
     "expected_reason": "invalid_stage_value", "rationale_en": "A mode that the tatweel stage does not have."},
    {"fixture_id": "rej-015", "kind": "policy_patch", "base": B, "patch": {"policy_id": "custom-test", "unicode_form": "NFKC"},
     "expected_reason": "inconsistent_policy", "rationale_en": "NFKC with honorific ligatures flagged instead of expanded."},
    {"fixture_id": "rej-016", "kind": "policy_patch", "base": B, "patch": {"policy_id": "custom-test", "comment": "x"},
     "expected_reason": "unknown_member", "rationale_en": "Unknown top-level member."},
    {"fixture_id": "rej-017", "kind": "policy_patch", "base": B, "patch": {"policy_id": "custom-test", "unicode_version": "15.1.0"},
     "expected_reason": "unsupported_unicode_version", "rationale_en": "Only the pinned UCD 18.0.0 tables ship with this release."},
    {"fixture_id": "rej-018", "kind": "jsonl_line", "policy_id": B, "line": "{\"id\": 1, \"body\": \"\u0646\u0635\"}",
     "field": "text", "expected_reason": "missing_text_field", "rationale_en": "The record has no 'text' field."},
    {"fixture_id": "rej-019", "kind": "jsonl_line", "policy_id": B, "line": "{\"text\": 42}", "field": "text",
     "expected_reason": "text_not_string", "rationale_en": "The text field is a number."},
    {"fixture_id": "rej-020", "kind": "jsonl_line", "policy_id": B, "line": "{\"text\": \"\u0646\u0635\"", "field": "text",
     "expected_reason": "invalid_json", "rationale_en": "The JSON line is not closed."},
]

_SURR = re.compile("[\ud800-\udfff]")


def dumps(rec):
    s = json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    # Lone surrogates cannot be written as UTF-8: escape them as JSON \\u sequences (json.loads restores them).
    return _SURR.sub(lambda m: "\\u%04x" % ord(m.group()), s)


def escaped(s):
    return "".join(c if 0x20 <= ord(c) < 0x7F else ("\\u%04x" % ord(c) if ord(c) < 0x10000 else "\\U%08x" % ord(c))
                   for c in s)


def finish(rec, split):
    rec = dict(rec)
    rec["split"] = split
    rec["input_escaped"] = escaped(rec["input"])
    rec["author"] = AUTHOR
    rec["created"] = CREATED
    rec["label"] = LABEL
    rec["synthetic"] = True
    rec["reviewed_by"] = None
    rec["review_verdict"] = None
    return rec


def write(path, recs):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in recs:
            f.write(dumps(r) + "\n")


def main():
    assert len(DEV) == 64 and len(ACCEPTANCE) == 16, (len(DEV), len(ACCEPTANCE))
    ids = [r["fixture_id"] for r in DEV + ACCEPTANCE + REJECTED]
    assert len(ids) == len(set(ids))
    dev = [finish(r, "dev") for r in DEV]
    acc = [finish(r, "acceptance") for r in ACCEPTANCE]
    rej = []
    for r in REJECTED:
        r = dict(r)
        r.update({"split": "rejected", "author": AUTHOR, "created": CREATED, "label": LABEL, "synthetic": True})
        rej.append(r)
    write(os.path.join(OUT, "dev", "dev.jsonl"), dev)
    write(os.path.join(OUT, "acceptance", "acceptance.jsonl"), acc)
    write(os.path.join(OUT, "rejected", "rejected.jsonl"), rej)
    prov = []
    for r in dev + acc + rej:
        line = dumps(r)
        prov.append({"fixture_id": r["fixture_id"], "split": r["split"], "author": AUTHOR, "created": CREATED,
                     "label": LABEL, "license": "CC-BY-4.0",
                     "sha256": hashlib.sha256(line.encode("utf-8")).hexdigest()})
    write(os.path.join(OUT, "PROVENANCE.jsonl"), prov)
    print("dev=%d acceptance=%d rejected=%d" % (len(dev), len(acc), len(rej)))


if __name__ == "__main__":
    main()

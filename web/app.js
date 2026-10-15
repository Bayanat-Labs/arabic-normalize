// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
//
// Arabic Text Normalizer: the user interface of the static page. All processing runs in this browser tab
// (a Web Worker when available); nothing is uploaded, stored or logged. The text is never put in the URL.
import { EXAMPLES } from './examples.js';
import { LIB_VERSION, UNICODE_VERSION, listPolicies, loadPolicy, LOSSY_RULES } from './lib/index.js';
import { MARKS, toCodePoints, fromCodePoints } from './lib/ucd.js';
import { DISPLAY_LIMIT } from './compute.js';

// --- Strings ------------------------------------------------------------------------------------------
// Western digits are used for numbers in both languages, because the tool itself converts digits.
const LRI = '⁦';
const PDI = '⁩';
const RLI = '\u2067';
const ltr = (s) => `${LRI}${s}${PDI}`;
const rtl = (s) => `${RLI}${s}${PDI}`;

const STR = {
  en: {
    docTitle: 'Arabic Text Normalizer – Bayanat Labs',
    skip: 'Skip to the tool',
    brand: 'Bayanat Labs',
    title: 'Arabic Text Normalizer',
    lede: 'Apply a named, hash-identified normalisation policy to Arabic text and see every change: before and after, the change log, the lossy changes and the policy SHA-256.',
    privacy: 'Normalisation runs in your browser. Your text is not uploaded, stored or logged.',
    inputH: 'Text',
    inputLabel: 'Text to normalise',
    placeholder: 'Paste Arabic text here',
    worked: 'Worked example',
    moreExamples: 'More examples',
    examplesPlaceholder: 'More examples…',
    clear: 'Clear',
    count: (n) => `${fmt(n)} code points`,
    policyLabel: 'Policy',
    hashLabel: 'Policy SHA-256',
    copy: 'Copy',
    copied: 'Copied',
    lossyRules: 'Lossy rules in this policy:',
    none: 'none',
    canonSummary: 'What is hashed?',
    canonText: 'The hash is the SHA-256 of the policy’s canonical JSON without its meta member: keys sorted, no whitespace, UTF-8.',
    downloadPolicy: 'Download the policy file (JSON)',
    outputH: 'Normalised text',
    outputLabel: 'Normalised text',
    copyOutput: 'Copy output',
    downloadResult: 'Download the detailed result (JSON)',
    statChanges: 'Changes',
    statLossy: 'Lossy changes',
    statRatio: 'Diacritization ratio',
    statLen: 'Code points before → after',
    lossyH: 'Lossy flags',
    flagsH: 'Informational flags',
    noLossy: 'No lossy change',
    noFlags: 'No flag',
    rejected: (n) => `Invalid code points removed and reported in rejected_spans: ${fmt(n)}.`,
    diffH: 'Before and after',
    showInvisible: 'Show invisible characters',
    legendChanged: 'changed',
    legendLossy: 'lossy change',
    legendRemoved: 'removed',
    legendInvisible: 'invisible character',
    before: 'Before',
    after: 'After',
    diffNote: (n) => `Highlighting covers the first ${fmt(n)} code points only.`,
    logH: 'Change log',
    logNote: 'One row per changed character, in the order the stages ran. Positions count code points in the original text.',
    colStage: 'Stage',
    colRule: 'Rule',
    colSpan: 'Position in input',
    colBefore: 'Before',
    colAfter: 'After',
    colLossy: 'Lossy',
    yes: 'yes',
    no: 'no',
    removedCell: '(removed)',
    logEmpty: 'No change: the text is already normalised under this policy.',
    logTrunc: (shown, total) => `Showing changes 1 to ${fmt(shown)} of ${fmt(total)}. Download the detailed result to see all of them.`,
    cmpH: 'Compare with another policy',
    cmpWith: 'Compare with',
    cmpSource: 'Input',
    cmpSame: 'Choose a different policy to compare.',
    cmpIdentical: 'Both policies give the same text.',
    cmpRegions: (n) => `Regions that differ: ${fmt(n)}.`,
    cmpOnly: 'Rules that only this policy applies:',
    cmpSkipped: 'This text is too long to compare here.',
    howH: 'How it is computed',
    how1: 'A policy sets one mode for each of the 18 normalisation stages; the stages always run in the same order.',
    how2: 'Character data comes from the Unicode 18.0.0 database bundled with the library, so the output does not change from one browser to another.',
    how3: 'Every change is logged with its position in the original text, and the offset map links each output character to its position in the input.',
    how4: `Changes that can make two different words identical, such as ${rtl('ى')} to ${rtl('ي')}, are flagged as lossy.`,
    how5: 'The SHA-256 identifies the policy exactly: cite the policy id and its hash, and anyone can reproduce the same output.',
    howLib: 'This page runs the JavaScript library @bayanat-labs/arabic-normalize, which gives the same output as the Python library arabic-normalize on every conformance case.',
    ctaH: 'Need production-grade, rights-cleared Arabic data?',
    ctaText: 'Bayanat Labs builds licensed Arabic datasets with documented normalisation.',
    ctaLink: 'See Bayanat Labs Knowledge',
    licence: 'Code: Apache-2.0. Policy files and examples: CC BY 4.0. Unicode tables: Unicode License V3. Font: IBM Plex Sans Arabic, SIL OFL 1.1.',
    errCap: 'The text is over the 10 MiB limit.',
    outputShort: (n) => `The box shows the first ${fmt(n)} characters. Copy output and the download contain the full text.`,
    errGeneric: (m) => `The text could not be normalised: ${m}`,
    policyNote: 'Policy:',
    langToggle: 'العربية',
    langToggleLang: 'ar',
    ctaHref: 'https://www.bayanatlabs.com/products/knowledge',
  },
  ar: {
    docTitle: 'توحيد النص العربي وتنظيفه – بيانات لابز',
    skip: 'انتقل إلى الأداة',
    brand: 'بيانات لابز',
    title: 'توحيد النص العربي وتنظيفه',
    lede: 'طبّق على نصك العربي سياسة توحيد مسمّاة ذات بصمة ثابتة، وشاهد كل تغيير: النص قبل التوحيد وبعده، وسجل التغييرات، والتغييرات الفاقدة للمعلومات، وبصمة SHA-256 للسياسة.',
    privacy: 'يجري التوحيد داخل متصفحك، فلا يُرفع نصك ولا يُخزَّن ولا يُسجَّل.',
    inputH: 'النص',
    inputLabel: 'النص المراد توحيده',
    placeholder: 'الصق نصًا عربيًا هنا',
    worked: 'المثال المشروح',
    moreExamples: 'أمثلة أخرى',
    examplesPlaceholder: 'أمثلة أخرى…',
    clear: 'مسح',
    count: (n) => `عدد نقاط الترميز: ${fmt(n)}`,
    policyLabel: 'السياسة',
    hashLabel: 'بصمة SHA-256 للسياسة',
    copy: 'نسخ',
    copied: 'نُسخ',
    lossyRules: 'القواعد الفاقدة للمعلومات في هذه السياسة:',
    none: 'لا توجد',
    canonSummary: 'ممّ تُحسب البصمة؟',
    canonText: 'البصمة هي قيمة SHA-256 لنص JSON القانوني للسياسة بعد حذف الحقل meta: مفاتيح مرتبة، بلا مسافات، بترميز UTF-8.',
    downloadPolicy: 'تنزيل ملف السياسة (JSON)',
    outputH: 'النص الموحَّد',
    outputLabel: 'النص بعد التوحيد',
    copyOutput: 'نسخ الناتج',
    downloadResult: 'تنزيل النتيجة المفصّلة (JSON)',
    statChanges: 'التغييرات',
    statLossy: 'التغييرات الفاقدة للمعلومات',
    statRatio: 'نسبة التشكيل',
    statLen: 'نقاط الترميز قبل ← بعد',
    lossyH: 'تنبيهات فقد المعلومات',
    flagsH: 'تنبيهات لا تغيّر النص',
    noLossy: 'لا تغيير فاقد للمعلومات',
    noFlags: 'لا تنبيه',
    rejected: (n) => `حُذفت محارف غير صالحة وسُجّلت في ${ltr('rejected_spans')}، وعددها: ${fmt(n)}.`,
    diffH: 'قبل التوحيد وبعده',
    showInvisible: 'إظهار المحارف غير المرئية',
    legendChanged: 'تغيير',
    legendLossy: 'تغيير فاقد للمعلومات',
    legendRemoved: 'محذوف',
    legendInvisible: 'محرف غير مرئي',
    before: 'قبل',
    after: 'بعد',
    diffNote: (n) => `يقتصر التلوين على أول ${fmt(n)} من نقاط الترميز.`,
    logH: 'سجل التغييرات',
    logNote: 'سطر لكل محرف تغيّر، بالترتيب الذي جرت به المراحل. تُعدّ المواضع بنقاط الترميز في النص الأصلي.',
    colStage: 'المرحلة',
    colRule: 'القاعدة',
    colSpan: 'الموضع في المدخل',
    colBefore: 'قبل',
    colAfter: 'بعد',
    colLossy: 'فاقد للمعلومات',
    yes: 'نعم',
    no: 'لا',
    removedCell: '(حُذف)',
    logEmpty: 'لا تغيير: النص موحَّد أصلًا وفق هذه السياسة.',
    logTrunc: (shown, total) => `تُعرض التغييرات من 1 إلى ${fmt(shown)}، ومجموعها ${fmt(total)}. نزّل النتيجة المفصّلة لرؤيتها كلها.`,
    cmpH: 'قارن بسياسة أخرى',
    cmpWith: 'السياسة المقارَن بها',
    cmpSource: 'المدخل',
    cmpSame: 'اختر سياسة مختلفة للمقارنة.',
    cmpIdentical: 'تعطي السياستان النص نفسه.',
    cmpRegions: (n) => `عدد المواضع المختلفة: ${fmt(n)}.`,
    cmpOnly: 'قواعد لا تطبّقها إلا هذه السياسة:',
    cmpSkipped: 'النص أطول من أن تُجرى مقارنته هنا.',
    howH: 'كيف يُحسب الناتج',
    how1: 'تحدد السياسة وضعًا لكل مرحلة من مراحل التوحيد الثماني عشرة، وتجري المراحل دائمًا بالترتيب نفسه.',
    how2: 'تأتي خصائص المحارف من قاعدة بيانات يونيكود 18.0.0 المضمّنة في المكتبة، فلا يتغير الناتج بتغيّر المتصفح.',
    how3: 'يُسجَّل كل تغيير مع موضعه في النص الأصلي، وتربط خريطة الإزاحات كل محرف في الناتج بموضعه في المدخل.',
    how4: 'التغييرات التي قد تجعل كلمتين مختلفتين متطابقتين، مثل تحويل ى إلى ي، تُعلَّم بأنها فاقدة للمعلومات.',
    how5: 'تعرّف بصمة SHA-256 السياسة تعريفًا تامًّا: اذكر معرّف السياسة وبصمتها ليتمكن غيرك من إعادة إنتاج الناتج نفسه.',
    howLib: `تعمل هذه الصفحة بمكتبة JavaScript ‏${ltr('@bayanat-labs/arabic-normalize')}، وهي تعطي الناتج نفسه الذي تعطيه مكتبة Python ‏${ltr('arabic-normalize')} في جميع حالات الاختبار.`,
    ctaH: 'هل تحتاج إلى بيانات عربية جاهزة للإنتاج وواضحة الحقوق؟',
    ctaText: 'تبني بيانات لابز مجموعات بيانات عربية مرخّصة، مع توثيق طريقة توحيد نصوصها.',
    ctaLink: 'اطّلع على مجموعات البيانات النصية العربية المرخّصة',
    licence: 'الشيفرة البرمجية: Apache-2.0. ملفات السياسات والأمثلة: CC BY 4.0. جداول يونيكود: Unicode License V3. الخط: IBM Plex Sans Arabic بترخيص SIL OFL 1.1.',
    errCap: `النص يتجاوز الحد الأقصى البالغ ${ltr('10 MiB')}.`,
    outputShort: (n) => `يعرض المربع أول ${fmt(n)} من المحارف، أما زر نسخ الناتج والملف المنزَّل ففيهما النص كاملًا.`,
    errGeneric: (m) => `تعذّر توحيد النص: ${ltr(m)}`,
    policyNote: 'السياسة:',
    langToggle: 'English',
    langToggleLang: 'en',
    ctaHref: 'https://www.bayanatlabs.com/ar/products/knowledge',
  },
};

const STAGES = {
  reject_invalid: ['Invalid characters', 'رفض المحارف غير الصالحة'],
  strip_controls: ['Invisible format characters', 'محارف التنسيق غير المرئية'],
  presentation_forms: ['Presentation forms', 'أشكال العرض'],
  ligatures_honorific: ['Honorific ligatures', 'الرموز المركبة التعظيمية'],
  bidi_zw: ['Bidi and zero-width characters', 'محارف الاتجاه والمحارف الصفرية العرض'],
  canonical_order: ['Canonical order (NFC)', 'الترتيب القانوني (NFC)'],
  tatweel: ['Tatweel', 'التطويل'],
  diacritics: ['Harakat', 'الحركات'],
  quranic_marks: ['Quranic marks', 'العلامات القرآنية'],
  superscript_alef: ['Superscript alef', 'الألف الخنجرية'],
  alef_variants: ['Alef variants', 'صور الألف'],
  alef_maqsura: ['Alef maqsura', 'الألف المقصورة'],
  taa_marbuta: ['Taa marbuta', 'التاء المربوطة'],
  hamza_carriers: ['Hamza carriers', 'الهمزة على الواو والياء'],
  persian_urdu_letters: ['Persian and Urdu letters', 'الحروف الفارسية والأردية'],
  digits: ['Digits', 'الأرقام'],
  punctuation: ['Punctuation', 'علامات الترقيم'],
  whitespace: ['Whitespace', 'المسافات'],
  latin_case: ['Latin letter case', 'حالة الحروف اللاتينية'],
};

// English descriptions isolate the Arabic letters so the arrow keeps pointing from the old to the new letter.
const RULES = {
  'alef_variants.map': [`${rtl('أ إ آ ٱ')} → ${rtl('ا')} (alef variants)`, 'تحويل أ وإ وآ وٱ إلى ا'],
  'alef_maqsura.to_yeh': [`${rtl('ى')} → ${rtl('ي')} (alef maqsura to yeh)`, 'تحويل الألف المقصورة ى إلى ي'],
  'taa_marbuta.to_heh': [`${rtl('ة')} → ${rtl('ه')} (taa marbuta to heh)`, 'تحويل التاء المربوطة ة إلى ه'],
  'hamza_carriers.fold': [`${rtl('ؤ')} → ${rtl('و')}, ${rtl('ئ')} → ${rtl('ي')} (hamza carriers)`, 'تحويل ؤ إلى و وئ إلى ي'],
  'persian_urdu_letters.map': [`${rtl('ی ک ہ ھ')} → ${rtl('ي ك ه')} (Persian and Urdu letters)`, 'تحويل الحروف الفارسية والأردية إلى نظائرها العربية'],
  'latin_case.lower': ['Latin letters lower-cased', 'تحويل الحروف اللاتينية إلى حروف صغيرة'],
  'canonical_order.nfkc': ['NFKC compatibility folding', 'تحويلات التوافق في NFKC'],
  'taa_marbuta.flag': [`${rtl('ة')} kept and flagged`, 'التاء المربوطة ة باقية مع تنبيه'],
  'alef_maqsura.flag': [`${rtl('ى')} kept and flagged`, 'الألف المقصورة ى باقية مع تنبيه'],
  'presentation_forms.flag': ['Arabic presentation forms present', 'في النص أشكال عرض عربية'],
  'ligatures_honorific.flag': [`Honorific ligature kept, for example ${rtl('ﷺ')}`, 'رمز تعظيمي مركب باقٍ، مثل ﷺ'],
};

const INVISIBLE = new Map([
  [0x200B, 'ZWSP'], [0x200C, 'ZWNJ'], [0x200D, 'ZWJ'], [0x200E, 'LRM'], [0x200F, 'RLM'], [0x061C, 'ALM'],
  [0x202A, 'LRE'], [0x202B, 'RLE'], [0x202C, 'PDF'], [0x202D, 'LRO'], [0x202E, 'RLO'], [0x2066, 'LRI'],
  [0x2067, 'RLI'], [0x2068, 'FSI'], [0x2069, 'PDI'], [0xFEFF, 'BOM'], [0x00AD, 'SHY'], [0x2060, 'WJ'],
  [0x2061, 'U+2061'], [0x2062, 'U+2062'], [0x2063, 'U+2063'], [0x2064, 'U+2064'], [0x034F, 'CGJ'],
  [0x00A0, 'NBSP'], [0x202F, 'NNBSP'], [0x0085, 'NEL'], [0xFE0E, 'VS15'], [0xFE0F, 'VS16'],
]);
const hexcp = (c) => `U+${c.toString(16).toUpperCase().padStart(4, '0')}`;
function invisibleLabel(c) {
  if (INVISIBLE.has(c)) return INVISIBLE.get(c);
  if (c < 0x20 && c !== 0x0A && c !== 0x09 && c !== 0x0D) return hexcp(c);
  if ((c >= 0x7F && c <= 0x9F) || (c >= 0xD800 && c <= 0xDFFF) || (c >= 0xFDD0 && c <= 0xFDEF) || (c & 0xFFFE) === 0xFFFE
    || (c >= 0x206A && c <= 0x206F) || (c >= 0xFFF9 && c <= 0xFFFB) || (c >= 0xE0000 && c <= 0xE007F)) return hexcp(c);
  return null;
}

// --- State ----------------------------------------------------------------------------------------------
const $ = (id) => document.getElementById(id);
const els = {
  input: $('input'), output: $('output'), policy: $('policy'), policyB: $('policy-b'), examples: $('examples'),
  count: $('count'), exampleNote: $('example-note'), error: $('error'), before: $('before'), after: $('after'),
  showInvisible: $('show-invisible'), logBody: document.querySelector('#log tbody'), logNote: $('log-note'),
  diffNote: $('diff-note'), cmpBody: document.querySelector('#cmp tbody'), cmpSummary: $('cmp-summary'),
};
const POLICIES = listPolicies().map((id) => loadPolicy(id));
let lang = 'en';
let last = null; // {text, policy, compare, response}
let seq = 0;
let currentExample = null;
let fullOutput = '';
const MAX_OUTPUT_DISPLAY = 300000; // UTF-16 units shown in the output box; Copy and Download use the full text

function fmt(n) {
  return Number(n).toLocaleString('en-US');
}
function t(key, ...args) {
  const v = STR[lang][key];
  return typeof v === 'function' ? v(...args) : v;
}
function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null) continue;
    if (k === 'class') e.className = v;
    else if (k === 'text') e.textContent = v;
    else e.setAttribute(k, v);
  }
  for (const c of children) e.append(c);
  return e;
}

// --- Worker (falls back to the main thread) ----------------------------------------------------------
// The worker is started from a blob: URL whose only line imports worker.js. A worker created from a
// blob: URL inherits this page's Content-Security-Policy (connect-src 'none'), so the code that processes
// the text cannot open network connections either. A worker loaded from its own URL would take its policy
// from the HTTP response instead, and static hosts such as Hugging Face Spaces send none.
let worker = null;
const pending = new Map();
try {
  const workerModule = new URL('./worker.js', import.meta.url).href;
  const workerBlobUrl = URL.createObjectURL(
    new Blob([`import ${JSON.stringify(workerModule)};\n`], { type: 'text/javascript' }));
  worker = new Worker(workerBlobUrl, { type: 'module' });
  worker.onmessage = (ev) => {
    URL.revokeObjectURL(workerBlobUrl);
    const cb = pending.get(ev.data.id);
    pending.delete(ev.data.id);
    if (cb) cb(ev.data);
  };
  worker.onerror = () => {
    worker = null;
    for (const [id, cb] of pending) { pending.delete(id); localCompute(cb.request).then(cb); }
  };
} catch (e) {
  worker = null;
}
let computeModule = null;
async function localCompute(request) {
  if (!computeModule) computeModule = await import('./compute.js');
  return computeModule.compute(request);
}
function request(req) {
  if (!worker) return localCompute(req);
  const id = ++seq;
  return new Promise((resolve) => {
    resolve.request = req;
    pending.set(id, resolve);
    worker.postMessage({ id, ...req });
  });
}

// --- Language -------------------------------------------------------------------------------------------
function initialLang() {
  try {
    const q = new URLSearchParams(location.search).get('lang');
    if (q === 'en' || q === 'ar') return q;
  } catch (e) { /* ignore */ }
  try {
    const saved = localStorage.getItem('arnorm.lang');
    if (saved === 'en' || saved === 'ar') return saved;
  } catch (e) { /* storage may be blocked */ }
  return 'en';
}

function applyLang() {
  const root = document.documentElement;
  root.lang = lang;
  root.dir = lang === 'ar' ? 'rtl' : 'ltr';
  document.title = t('docTitle');
  for (const node of document.querySelectorAll('[data-i18n]')) {
    const v = STR[lang][node.dataset.i18n];
    if (typeof v === 'string') node.textContent = v;
  }
  for (const node of document.querySelectorAll('[data-i18n-placeholder]')) node.placeholder = t(node.dataset.i18nPlaceholder);
  const toggle = $('lang-toggle');
  toggle.textContent = t('langToggle');
  toggle.lang = t('langToggleLang');
  toggle.dir = t('langToggleLang') === 'ar' ? 'rtl' : 'ltr';
  $('cta-link').href = t('ctaHref');
  $('version').textContent = `arabic-normalize ${LIB_VERSION} · Unicode ${UNICODE_VERSION}`;
  fillExamples();
  showPolicy();
  showExampleNote();
  if (last && last.response) render(last.response);
  else updateCount();
}

// --- Policy and examples ------------------------------------------------------------------------------
function fillPolicies() {
  for (const sel of [els.policy, els.policyB]) {
    sel.textContent = '';
    for (const p of POLICIES) sel.append(el('option', { value: p.policy_id, text: p.policy_id }));
  }
  els.policy.value = 'bayanat-norm-v1';
  els.policyB.value = 'raw-safe-v1';
}

function policyTitle(p) {
  const meta = p.data.meta || {};
  return (lang === 'ar' ? meta.title_ar : meta.title_en) || p.policy_id;
}

function lossyRulesOf(p) {
  const s = p.stages;
  const out = [];
  if (s.alef_variants === 'map') out.push('alef_variants.map');
  if (s.alef_maqsura === 'to-yeh') out.push('alef_maqsura.to_yeh');
  if (s.taa_marbuta === 'to-heh') out.push('taa_marbuta.to_heh');
  if (s.hamza_carriers === 'fold') out.push('hamza_carriers.fold');
  if (s.persian_urdu_letters === 'map') out.push('persian_urdu_letters.map');
  if (s.latin_case === 'lower') out.push('latin_case.lower');
  if (p.unicode_form === 'NFKC') out.push('canonical_order.nfkc');
  return out.filter((r) => LOSSY_RULES.has(r));
}

function showPolicy() {
  const p = loadPolicy(els.policy.value);
  $('policy-title').textContent = policyTitle(p);
  $('policy-hash').textContent = p.policy_hash;
  const rules = lossyRulesOf(p);
  $('policy-lossy').textContent = rules.length ? rules.map((r) => ruleText(r)).join(' · ') : t('none');
  $('policy-canonical').textContent = p.canonical();
}

function ruleText(r) {
  const d = RULES[r];
  return d ? (lang === 'ar' ? d[1] : d[0]) : r;
}

function fillExamples() {
  const sel = els.examples;
  const cur = sel.value;
  sel.textContent = '';
  sel.append(el('option', { value: '', text: t('examplesPlaceholder') }));
  for (const ex of EXAMPLES) {
    if (ex.id === 'worked') continue;
    const preview = [...ex.input].slice(0, 24).map((ch) => (invisibleLabel(ch.codePointAt(0)) ? '·' : ch)).join('');
    sel.append(el('option', { value: ex.id, text: `${preview}  (${ex.policy_id})` }));
  }
  sel.value = cur;
}

function loadExample(id) {
  const ex = EXAMPLES.find((e) => e.id === id);
  if (!ex) return;
  currentExample = ex;
  els.input.value = ex.input;
  els.policy.value = ex.policy_id;
  if (els.policyB.value === ex.policy_id) els.policyB.value = ex.policy_id === 'raw-safe-v1' ? 'bayanat-norm-v1' : 'raw-safe-v1';
  showPolicy();
  showExampleNote();
  run();
}

function showExampleNote() {
  const n = els.exampleNote;
  if (!currentExample || currentExample.input !== els.input.value) {
    n.hidden = true;
    return;
  }
  n.textContent = '';
  n.append(`${lang === 'ar' ? currentExample.note_ar : currentExample.note_en} ${t('policyNote')} `,
    el('code', { dir: 'ltr', text: currentExample.policy_id }));
  n.hidden = false;
}

// --- Running --------------------------------------------------------------------------------------------
function updateCount() {
  els.count.textContent = t('count', toCodePoints(els.input.value).length);
}

let timer = null;
function schedule() {
  clearTimeout(timer);
  timer = setTimeout(run, 120);
}

async function run() {
  const req = { text: els.input.value, policy: els.policy.value, compare: els.policyB.value };
  updateCount();
  showExampleNote();
  const marker = {};
  last = { ...req, marker, response: null };
  const response = await request(req);
  if (last.marker !== marker) return; // a newer request superseded this one
  last.response = response;
  render(response);
}

// --- Rendering ------------------------------------------------------------------------------------------
function clusters(cps, n) {
  // A base code point with the combining marks that follow it, so Arabic letters keep their marks.
  const out = [];
  let i = 0;
  while (i < n) {
    let j = i + 1;
    if (!invisibleLabel(cps[i])) while (j < n && MARKS.has(cps[j]) && !invisibleLabel(cps[j])) j += 1;
    out.push([i, j]);
    i = j;
  }
  return out;
}

function renderText(container, cps, n, markOf, reveal) {
  container.textContent = '';
  const frag = document.createDocumentFragment();
  let plain = '';
  const flush = () => {
    if (plain) frag.append(document.createTextNode(plain));
    plain = '';
  };
  for (const [i, j] of clusters(cps, n)) {
    const label = invisibleLabel(cps[i]);
    let m = 0;
    let removed = true;
    for (let k = i; k < j; k++) {
      const v = markOf(k);
      if ((v & 3) > m) m = v & 3;
      if (!(v & 8)) removed = false;
    }
    const cls = [m === 2 ? 'lossy' : m === 1 ? 'chg' : '', removed ? 'del' : ''].filter(Boolean).join(' ');
    if (label && reveal) {
      flush();
      frag.append(el('span', { class: `inv ${cls}`.trim(), title: `${hexcp(cps[i])}`, text: label }));
    } else if (cls) {
      flush();
      frag.append(el('span', { class: cls, title: cps.slice(i, j).map(hexcp).join(' '), text: fromCodePoints(cps, i, j) }));
    } else {
      plain += fromCodePoints(cps, i, j);
    }
  }
  flush();
  container.append(frag);
}

function cpCell(s, cls) {
  const cps = toCodePoints(s);
  const td = el('td', { class: cls });
  if (cps.length === 0) {
    td.append(el('span', { class: 'cp', text: t('removedCell') }));
    return td;
  }
  // A combining mark shown on its own gets a dotted circle (U+25CC) as its base, so it stays visible.
  const lead = MARKS.has(cps[0]) && !invisibleLabel(cps[0]) ? '\u25CC' : '';
  const visible = lead + cps.map((c) => (invisibleLabel(c) ? `[${invisibleLabel(c)}]` : String.fromCodePoint(c))).join('');
  td.append(el('span', { dir: 'auto', text: visible }), el('span', { class: 'cp', text: ltr(cps.map(hexcp).join(' ')) }));
  return td;
}

function render(resp) {
  if (resp.error) {
    els.output.value = '';
    fullOutput = '';
    els.error.hidden = false;
    els.error.textContent = resp.error.reason === 'over_cap_bytes' ? t('errCap') : t('errGeneric', resp.error.message);
    return;
  }
  els.error.hidden = true;
  const r = resp.result;
  fullOutput = r.text_norm;
  const shortened = r.text_norm.length > MAX_OUTPUT_DISPLAY;
  els.output.value = shortened ? r.text_norm.slice(0, MAX_OUTPUT_DISPLAY) : r.text_norm;
  $('output-note').hidden = !shortened;
  $('output-note').textContent = shortened ? t('outputShort', MAX_OUTPUT_DISPLAY) : '';
  $('s-changes').textContent = fmt(r.changes_total);
  $('s-lossy').textContent = fmt(r.lossy_total);
  $('s-ratio').textContent = r.diacritization_ratio.toFixed(3);
  $('s-len').textContent = `${fmt(r.input_length)} → ${fmt(r.offset_map_total)}`;

  const lossy = $('lossy-flags');
  lossy.textContent = '';
  if (r.lossy_flags.length === 0) lossy.append(el('li', { class: 'none', text: t('noLossy') }));
  for (const f of r.lossy_flags) {
    const total = r.stats.rules[f] || 0;
    lossy.append(el('li', { class: 'lossy' }, el('code', { dir: 'ltr', text: f }), ` ${ruleText(f)} · ${fmt(total)}`));
  }
  const flags = $('flags');
  flags.textContent = '';
  if (r.flags.length === 0) flags.append(el('li', { class: 'none', text: t('noFlags') }));
  for (const f of r.flags) flags.append(el('li', {}, el('code', { dir: 'ltr', text: f }), ` ${ruleText(f)}`));
  const rej = $('rejected');
  const nRej = r.stats.classes.rejected;
  rej.hidden = nRej === 0;
  rej.textContent = nRej ? t('rejected', nRej) : '';

  // Before and after
  const reveal = els.showInvisible.checked;
  const inCps = toCodePoints(last.text);
  const outCps = toCodePoints(r.text_norm);
  const inMark = resp.inMark;
  const outMark = resp.outMark;
  // input: bit 4 set = kept; convert to bit 8 = removed for renderText
  renderText(els.before, inCps, inMark.length, (k) => (inMark[k] & 3) | (inMark[k] & 4 ? 0 : 8), reveal);
  renderText(els.after, outCps, outMark.length, (k) => outMark[k], reveal);
  const truncated = inCps.length > DISPLAY_LIMIT || outCps.length > DISPLAY_LIMIT;
  els.diffNote.hidden = !truncated;
  els.diffNote.textContent = truncated ? t('diffNote', DISPLAY_LIMIT) : '';

  // Change log
  const body = els.logBody;
  body.textContent = '';
  const frag = document.createDocumentFragment();
  r.changes.forEach((c, idx) => {
    const st = STAGES[c.stage];
    const tr = el('tr', { class: c.lossy ? 'is-lossy' : null },
      el('td', { text: String(idx + 1) }),
      el('td', { text: st ? (lang === 'ar' ? st[1] : st[0]) : c.stage }),
      el('td', {}, el('code', { dir: 'ltr', text: c.rule_id })),
      el('td', { dir: 'ltr', text: `${c.src_start}–${c.src_end}` }),
      cpCell(c.before, 'txt'),
      cpCell(c.after, 'txt'),
      el('td', { class: c.lossy ? 'yes' : null, text: c.lossy ? t('yes') : t('no') }));
    frag.append(tr);
  });
  body.append(frag);
  if (r.changes_total === 0) {
    els.logNote.hidden = false;
    els.logNote.textContent = t('logEmpty');
  } else if (r.changes_total > r.changes.length) {
    els.logNote.hidden = false;
    els.logNote.textContent = t('logTrunc', r.changes.length, r.changes_total);
  } else {
    els.logNote.hidden = true;
  }

  // Comparison
  renderCompare(resp);
}

function renderCompare(resp) {
  const a = els.policy.value;
  const b = els.policyB.value;
  $('cmp-a-h').textContent = a;
  $('cmp-b-h').textContent = b;
  els.cmpBody.textContent = '';
  if (a === b) {
    els.cmpSummary.textContent = t('cmpSame');
    return;
  }
  if (resp.compareSkipped || !resp.diff) {
    els.cmpSummary.textContent = resp.compareSkipped ? t('cmpSkipped') : '';
    return;
  }
  const d = resp.diff;
  els.cmpSummary.textContent = '';
  if (d.identical) {
    els.cmpSummary.textContent = t('cmpIdentical');
  } else {
    const only = (pid, rules) => el('span', { class: 'only' }, el('code', { dir: 'ltr', text: pid }), ` ${t('cmpOnly')} `,
      ...(rules.length ? rules.flatMap((r) => [el('code', { dir: 'ltr', class: 'rule', text: r }), ' ']) : [t('none')]));
    els.cmpSummary.append(t('cmpRegions', d.regions.length), el('br'), only(a, d.rules_only_a), el('br'), only(b, d.rules_only_b));
  }
  const frag = document.createDocumentFragment();
  for (const reg of d.regions.slice(0, 500)) {
    frag.append(el('tr', {}, cpCell(reg.source, 'txt'), cpCell(reg.a, 'txt'), cpCell(reg.b, 'txt')));
  }
  els.cmpBody.append(frag);
}

// --- Copy and download --------------------------------------------------------------------------------
async function copyText(text, button) {
  let ok = false;
  try {
    await navigator.clipboard.writeText(text);
    ok = true;
  } catch (e) {
    const ta = el('textarea', { readonly: '', 'aria-hidden': 'true' });
    ta.value = text;
    ta.className = 'sr';
    document.body.append(ta);
    ta.select();
    try { ok = document.execCommand('copy'); } catch (e2) { ok = false; }
    ta.remove();
  }
  if (ok) {
    const old = button.textContent;
    button.textContent = t('copied');
    setTimeout(() => { button.textContent = old; }, 1200);
  }
}

function download(name, text) {
  const url = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
  const a = el('a', { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function downloadResult() {
  const text = els.input.value;
  const resp = await request({ text, policy: els.policy.value, full: true });
  if (resp.error) return;
  const r = resp.result;
  const out = { original_hash: r.original_hash, text_raw: text };
  for (const [k, v] of Object.entries(r)) if (k !== 'original_hash') out[k] = v;
  download('arabic-normalize-result.json', `${JSON.stringify(out, null, 2)}\n`);
}

// --- Wiring ----------------------------------------------------------------------------------------------
function init() {
  lang = initialLang();
  fillPolicies();
  els.input.addEventListener('input', schedule);
  els.policy.addEventListener('change', () => {
    if (els.policyB.value === els.policy.value) {
      els.policyB.value = els.policy.value === 'raw-safe-v1' ? 'bayanat-norm-v1' : 'raw-safe-v1';
    }
    showPolicy();
    run();
  });
  els.policyB.addEventListener('change', run);
  els.examples.addEventListener('change', () => {
    if (els.examples.value) loadExample(els.examples.value);
  });
  $('worked').addEventListener('click', () => {
    els.examples.value = '';
    loadExample('worked');
  });
  $('clear').addEventListener('click', () => {
    els.input.value = '';
    currentExample = null;
    els.examples.value = '';
    run();
    els.input.focus();
  });
  els.showInvisible.addEventListener('change', () => last && last.response && render(last.response));
  $('copy-hash').addEventListener('click', (e) => copyText($('policy-hash').textContent, e.currentTarget));
  $('copy-output').addEventListener('click', (e) => copyText(fullOutput, e.currentTarget));
  $('download-policy').addEventListener('click', () => {
    const p = loadPolicy(els.policy.value);
    download(`${p.policy_id}.json`, `${p.toJSONString(2)}\n`);
  });
  $('download-result').addEventListener('click', downloadResult);
  $('lang-toggle').addEventListener('click', () => {
    lang = lang === 'ar' ? 'en' : 'ar';
    try { localStorage.setItem('arnorm.lang', lang); } catch (e) { /* storage may be blocked */ }
    applyLang();
  });
  applyLang();
  loadExample('worked');
}

init();

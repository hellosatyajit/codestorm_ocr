"""Translation service layer.

Defines the `TranslationService` Protocol and a `MockTranslationService`
that returns canned output per target language so the rebuild step
exercises every font/script/RTL code path.

Swap this out for an Ollama/DeepL/Google client later with the same
signature.
"""
from __future__ import annotations

from typing import Protocol


class TranslationService(Protocol):
    def translate(self, text: str, src_lang: str, tgt_lang: str) -> str: ...


# ---------------------------------------------------------------------------
# Canned fixtures: one small pool per target language, indexed by hash
# so the same block always gets the same translated string (idempotent).
# ---------------------------------------------------------------------------

_EN_POOL = [
    "This is the mock English translation for block {i}.",
    "Sample translated sentence #{i} produced by MockTranslationService.",
    "[EN mock] Lorem ipsum dolor sit amet - block {i}.",
    "The quick brown fox jumps over block {i}.",
    "Translated headline {i} (mock output).",
]

_AR_POOL = [
    "\u0647\u0630\u0647 \u062a\u0631\u062c\u0645\u0629 \u0648\u0647\u0645\u064a\u0629 \u0644\u0644\u0643\u062a\u0644\u0629 {i}.",
    "\u0645\u062b\u0627\u0644 \u0644\u0646\u0635 \u0639\u0631\u0628\u064a \u0644\u0644\u0643\u062a\u0644\u0629 \u0631\u0642\u0645 {i}.",
    "\u0646\u0635 \u062a\u062c\u0631\u064a\u0628\u064a \u0628\u0627\u0644\u0644\u063a\u0629 \u0627\u0644\u0639\u0631\u0628\u064a\u0629 - {i}.",
]

_HI_POOL = [
    "\u092f\u0939 \u0939\u093f\u0928\u094d\u0926\u0940 \u0915\u093e \u0928\u092e\u0942\u0928\u093e \u0905\u0928\u0941\u0935\u093e\u0926 \u0939\u0948 ({i}).",
    "\u092c\u094d\u0932\u0949\u0915 {i} \u0915\u0947 \u0932\u093f\u090f \u0905\u0928\u0941\u0935\u093e\u0926\u093f\u0924 \u0935\u093e\u0915\u094d\u092f.",
    "\u0939\u093f\u0928\u094d\u0926\u0940 \u092e\u0947\u0902 \u090f\u0915 \u092a\u0930\u0940\u0915\u094d\u0937\u0923 \u0915\u0947 \u0932\u093f\u090f \u0905\u0928\u0941\u0935\u093e\u0926 {i}.",
]

_ZH_POOL = [
    "\u8fd9\u662f\u5757 {i} \u7684\u6a21\u62df\u4e2d\u6587\u7ffb\u8bd1\u3002",
    "\u6587\u672c\u5757 {i} \u7684\u7ffb\u8bd1\u793a\u4f8b\u3002",
    "\u7531 MockTranslationService \u751f\u6210\u7684\u4e2d\u6587\u7ffb\u8bd1 {i}\u3002",
]

_JA_POOL = [
    "\u3053\u308c\u306f\u30d6\u30ed\u30c3\u30af {i} \u306e\u6a21\u64ec\u65e5\u672c\u8a9e\u8a33\u3067\u3059\u3002",
    "\u30d6\u30ed\u30c3\u30af {i} \u306e\u7ffb\u8a33\u30b5\u30f3\u30d7\u30eb\u3002",
    "MockTranslationService \u306b\u3088\u308b\u65e5\u672c\u8a9e\u51fa\u529b {i}\u3002",
]

_KO_POOL = [
    "\uc774\uac83\uc740 \ube14\ub85d {i}\uc758 \ubaa8\uc758 \ud55c\uad6d\uc5b4 \ubc88\uc5ed\uc785\ub2c8\ub2e4.",
    "\ube14\ub85d {i}\uc758 \ud55c\uad6d\uc5b4 \ubc88\uc5ed \uc608\uc2dc.",
]

_RU_POOL = [
    "\u042d\u0442\u043e \u0442\u0435\u0441\u0442\u043e\u0432\u044b\u0439 \u043f\u0435\u0440\u0435\u0432\u043e\u0434 \u0431\u043b\u043e\u043a\u0430 {i}.",
    "\u0420\u0443\u0441\u0441\u043a\u0438\u0439 \u043f\u0440\u0438\u043c\u0435\u0440 \u0434\u043b\u044f \u0431\u043b\u043e\u043a\u0430 {i}.",
]

_POOLS: dict[str, list[str]] = {
    "en": _EN_POOL,
    "ar": _AR_POOL,
    "hi": _HI_POOL,
    "zh": _ZH_POOL,
    "zh-cn": _ZH_POOL,
    "zh-tw": _ZH_POOL,
    "ja": _JA_POOL,
    "ko": _KO_POOL,
    "ru": _RU_POOL,
}


class MockTranslationService:
    """Returns deterministic canned translations per target language.

    - Same (text, tgt_lang) pair always returns the same output.
    - Short text is returned as-is to avoid rendering garbage.
    - Unknown target language falls back to the English pool with a tag.
    """

    MIN_TEXT_LEN = 2

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> str:
        clean = (text or "").strip()
        if len(clean) < self.MIN_TEXT_LEN:
            return clean
        # If someone passes src == tgt, no-op so the UI doesn't get confused.
        if src_lang and tgt_lang and src_lang.lower() == tgt_lang.lower():
            return clean
        tgt = (tgt_lang or "en").lower()
        pool = _POOLS.get(tgt)
        if pool is None:
            return f"[{tgt.upper()} mock] {clean[:80]}"
        # Deterministic slot selection based on the source text itself.
        idx = (hash(clean) & 0x7FFFFFFF) % len(pool)
        template = pool[idx]
        return template.format(i=(abs(hash(clean)) % 1000))

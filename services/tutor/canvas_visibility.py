"""Server-owned wording guard for a newly requested Canvas composition."""

from __future__ import annotations

import re
import unicodedata


_VISUAL = re.compile(
    r"\b(?:canvas|drawing|diagram|visual|picture|image|scene|graph|chart|sketch|illustration)s?\b"
    r"|(?:ال)?(?:رسم(?:ا|ه)?|صور(?:ه)?|لوح(?:ه)?|مشهد|مخطط|شكل)\b"
    r"|كانفاس",
    re.IGNORECASE,
)
_UNQUALIFIED_NEW_VISUAL = re.compile(
    r"\b(?:canvas|drawing|diagram|visual|picture|image|scene|graph|chart|sketch|illustration)s?\b"
    r"|(?:ال)?(?:رسم(?:ا|ه)?|لوح(?:ه)?|مشهد|مخطط)\b"
    r"|(?:ال)?صور(?:ه)?\b|كانفاس",
    re.IGNORECASE,
)
_PHYSICAL_FORM = re.compile(r"\bفي صوره (?:غاز(?:يه)?|سائل(?:ه)?|صلب(?:ه)?)\b", re.IGNORECASE)
_PRESENT_VISUAL = re.compile(
    r"\b(?:look at|take a look|see|watch|notice|observe|shown|shows|displayed|visible|ready|"
    r"here is|here's|on (?:the )?screen|in (?:the )?drawing|on (?:the )?canvas|"
    r"i (?:have |already )?(?:drew|drawn|made|prepared|created|opened)|let's use)\b"
    r"|(?:انظر[يي]?|شاهدي|شوفي|لاحظي|راقبي|تأملي|ترين|تشاهدين|"
    r"امامك|قدامك|ظاهر[ه]?|جاهز[ه]?|اعددت|جهزت|حضرت|رسمت لك|"
    r"في الرسم|علي اللوح[ه]?|يوضح الرسم|الرسم يوضح|لنستخدم)",
    re.IGNORECASE,
)
_DEICTIC = re.compile(
    r"\b(?:here (?:it|they) (?:is|are)|there (?:it|they) (?:is|are)|what do you see|look at this)\b"
    r"|(?:ها هو|ها هي|ماذا ترين|ماذا تشاهدين|انظري الي هذا)",
    re.IGNORECASE,
)
_PREPARING = re.compile(
    r"\b(?:prepar(?:e|ing)|working on|building|will (?:draw|make|show)|i'?ll (?:draw|make|show)|"
    r"(?:i am|i['’]?m) (?:drawing|creating|making)|when (?:it|the (?:visual|drawing|diagram)) is ready)\b"
    r"|(?:اجهز|ساجهز|نجهز|ارسم لك|سارسم|سار[يي]ك|جار[يي] تجهيز|عندما يجهز|بعد ان يجهز)",
    re.IGNORECASE,
)
_STUDENT_SOURCE = re.compile(
    r"\b(?:your uploaded (?:image|picture)|the (?:image|picture) you sent|your photo)\b"
    r"|(?:صورتك|الصورة التي ارسلتها)",
    re.IGNORECASE,
)
_FUTURE_CONDITION = re.compile(
    r"\b(?:when|once|after)\b.{0,60}\b(?:ready|finished|appears)\b"
    r"|(?:عندما|حين|بعد ان).{0,60}(?:جاهز|يجهز|يظهر)",
    re.IGNORECASE,
)
_PARTS = re.compile(r"(?<=[.!?؟,،;؛:])\s+|\n+")


def _normalized(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u064b-\u065f\u0670]", "", text)
    return text.translate(str.maketrans("أإآٱىة", "اااايه")).casefold()


def _premature_visual_reference(part: str) -> bool:
    normalized = _normalized(part)
    if _DEICTIC.search(normalized):
        return True
    if not _VISUAL.search(normalized) or _STUDENT_SOURCE.search(normalized):
        return False
    if _FUTURE_CONDITION.search(normalized):
        return False
    if _PRESENT_VISUAL.search(normalized):
        return True
    # An unqualified reference to the new drawing is ambiguous before a Scene
    # exists. Keep only an explicit future/preparation statement.
    # "In gas form" names a state of matter, not an image being displayed.
    unqualified = _PHYSICAL_FORM.sub("", normalized)
    return bool(_UNQUALIFIED_NEW_VISUAL.search(unqualified)) and _PREPARING.search(normalized) is None


def ensure_new_canvas_is_not_claimed_visible(text: str, *, new_composition_requested: bool) -> tuple[str, bool]:
    """Drop visual-dependent clauses, retain teaching, and state preparation once.

    This runs only after server admission of a new Canvas request, before the
    Tutor text is persisted or streamed. It never interprets Student work.
    """

    if not new_composition_requested:
        return text, False
    parts = [part.strip() for part in _PARTS.split(text) if part.strip()]
    unsafe = [_premature_visual_reference(part) for part in parts]
    if not any(unsafe):
        return text, False

    arabic = any("\u0600" <= char <= "\u06ff" for char in text)
    preparation = "أجهّز لكِ التمثيل البصري الآن." if arabic else "I’m preparing the visual for you now."
    already_preparing = any(
        _PREPARING.search(_normalized(part)) for part, remove in zip(parts, unsafe) if not remove
    )
    kept: list[str] = []
    added = False
    for part, remove in zip(parts, unsafe):
        if remove:
            if kept and kept[-1].endswith((",", "،", ";", "؛", ":")):
                kept[-1] = kept[-1][:-1].rstrip() + "."
            if not added and not already_preparing:
                kept.append(preparation)
                added = True
            continue
        kept.append(part)
    repaired = " ".join(kept).strip()
    return repaired or preparation, True


def ensure_unavailable_canvas_is_not_promised(
    text: str,
    *,
    canvas_unavailable: bool,
) -> tuple[str, bool]:
    """Remove claims/promises about a Canvas request that cannot be admitted."""

    if not canvas_unavailable:
        return text, False
    parts = [part.strip() for part in _PARTS.split(text) if part.strip()]
    unsafe: list[bool] = []
    for part in parts:
        normalized = _normalized(part)
        if _STUDENT_SOURCE.search(normalized):
            unsafe.append(False)
            continue
        if _DEICTIC.search(normalized):
            unsafe.append(True)
            continue
        unqualified = _PHYSICAL_FORM.sub("", normalized)
        unsafe.append(bool(_UNQUALIFIED_NEW_VISUAL.search(unqualified)))
    if not any(unsafe):
        return text, False

    kept = [part for part, remove in zip(parts, unsafe) if not remove]
    repaired = " ".join(kept).strip()
    if repaired:
        return repaired, True
    arabic = any("؀" <= char <= "ۿ" for char in text)
    return (
        "خلّينا نكملها هنا خطوة خطوة." if arabic
        else "Let’s work through it here step by step.",
        True,
    )

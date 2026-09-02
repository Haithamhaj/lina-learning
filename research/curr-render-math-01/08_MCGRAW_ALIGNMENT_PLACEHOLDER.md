# CURR-RENDER-MATH-01 — McGraw-Hill My Math Alignment Placeholder

## Current known and unknown facts

| Field | Status |
|---|---|
| Publisher | McGraw Hill — known |
| Program | *My Math* — known |
| Grade | 5 — known |
| Edition / copyright year | unknown |
| ISBN | unknown |
| Student volumes / teacher materials | unknown |
| Chapter/unit/lesson order | unknown |
| School pacing, terminology, assessment expectations | unknown |

Public McGraw-Hill pages show that *My Math* is a PreK–5 program with standards-oriented conceptual understanding, procedural fluency, application, hands-on resources, and digital tools. They do **not** prove Lina's edition, chapter order, or assigned sequence. This study does not infer any of those facts.

## Future alignment record

When a verified physical or licensed digital book is available, create one source-linked row per school item:

| Verified source ID | McGraw edition/year/ISBN | Chapter | Lesson | Exact school terminology | Grade 5 concept key(s) | Standards | Preferred representation | Renderer(s) | Interaction pattern | Expected depth | Typical question form | Current school relevance | Rights/provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| required | required | required | required | required | one or more `G5-*` keys | source-backed | selected from catalog | selected from catalog | selected from catalog | factual only | description, not copied exercise | current/advisory | source location and permission |

The mapping adds **alignment metadata** only. It must not rename renderer keys, fork a My Math-specific renderer library, put publisher content in runtime prompts without permission, or change Studio Core. A lesson can map to several concept keys and one renderer can serve several lessons.

## Collect when the book arrives

1. Cover/copyright page: copyright year, title, edition statement, ISBN, volume identifiers, and access/license circumstances.
2. Table of contents: exact unit/chapter/lesson names and order.
3. The school's pacing guide, if available, separated from publisher sequence.
4. Only the minimum licensed sample/page references needed to identify terminology, representation, expected depth, and question form; retain original source provenance.
5. Any official McGraw alignment/standards documents corresponding to the exact edition.

## Mapping workflow

```text
verified book/source → source/rights decision → chapter/lesson metadata
→ map to existing G5 concept keys → choose catalog renderer/configuration
→ mark terminology/depth/school relevance → preserve provenance
```

If a genuine repeated capability gap appears, record it as a proposed catalog gap for Product Owner review. Do not invent a new renderer merely because a publisher used a distinctive page layout.

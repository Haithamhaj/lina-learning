# Lina capability roadmap

This roadmap sequences product evolution. It is not execution authority: an explicit current Product Owner instruction authorizes its requested working slice, while this roadmap and `TASKS.md` provide planning/context. Historical status labels do not override that instruction.

## Completed foundation

The accepted baseline includes the primary Tutor, safety/Parent Boundaries, ownership, optional content/RAG, Learning Intelligence foundation, Personal Facts/Core Profile, Voice/STT, Student image/PDF/DOCX sources with multimodal safety, durable Studio/Canvas runtime, Chat–Canvas continuity, and Studio subjects MATH/SCIENCE/ENGLISH/ARABIC.

## Current

1. Student UI refinement: improve the Daily Student experience without reopening protected contracts.
2. Authenticated Daily end-to-end acceptance: prove the complete disposable Student journey.
3. Real Lina use: observe natural use before treating implementation as learning benefit.
4. Evidence/personalization calibration: assess real, observable outcomes and revise only through approved work.

## Near next, usage-driven

- Fraction Canvas capability.
- Division Canvas capability.
- Other narrowly evidenced visual capabilities.

## Version 2 — Educational Generated Images

- Add generated educational images as a distinct V2 capability, not as a workaround for current Canvas defects.
- Outside mathematics, when the learning goal depends on visualizing an object, natural structure, scene, or process, prefer a generated educational image or image-led representation over a generic chart/plot. Science is the first priority domain.
- Mathematics remains structured-Canvas-first unless an actual image is the better representation for the learning goal.
- Generated images should be child-appropriate, instructional, and clear rather than optimized for photorealistic or marketing-grade quality. Cost/latency efficiency is preferred when educational usefulness is preserved.
- Delivery should integrate with Canvas. The default educational output is an instructional image with simple labels/arrows/stages when those annotations materially improve understanding; a plain image is acceptable only when annotation adds no learning value.
- Generated images are illustrative learning aids, not literal scientific reference images. When exact scientific form, terminology, or relationships matter, learner-visible text and labels must come from trusted grounded information rather than guesses inferred from generated pixels.
- Image generation is available through two paths: an explicit learner request within the V2 eligibility scope, or a contextually offered image CTA when the current concept/turn is genuinely image-appropriate.
- Initial V2 eligibility is intentionally narrow: the active subject must be Science and the visual need must be one of shape, structure, process, or scene. Requests outside that boundary stay on existing Tutor/Canvas capabilities until a later approved expansion.
- Eligibility uses a hybrid authority: the Tutor may signal that an image would help, but server-owned/system rules decide whether the image CTA is actually eligible to appear and whether generation may proceed. The Tutor signal cannot bypass the subject/category/quota rules.
- The image CTA is contextual only; it must not be permanently visible in every conversation or every Tutor turn.
- Per learner, at most 10 successful generated images that are actually delivered/visible count toward the daily allowance. Failed generations, invisible internal retries, and redisplay of the same generated image do not consume an additional allowance.
- When the daily allowance is exhausted, hide the image CTA for the rest of that day. If the learner explicitly asks for another image, Lina should state simply that today's image allowance is finished and continue with the available structured Canvas/drawing or verbal explanation instead.
- The daily image allowance resets at local midnight according to the learner's stored timezone.
- High-level scientific-grounding and annotated-output principles are decided. Remaining V2 work includes provider/model selection, questionable-output validation/rejection behavior, quota persistence/enforcement, exact Canvas annotation implementation, and acceptance before implementation.

## Later

- Age/grade-aware evolution and progression across school years toward primary-to-secondary product maturity.
- Trusted-reference pilot.
- Broader Science and language visual coverage beyond the initial V2 generated-image slice.
- A separately designed Parent experience/dashboard.
- Grade transition.
- Wider productization only after real-use evidence.

## Permanent sequencing rules

Tutor availability never depends on curriculum. Current behavior outranks historical personalization. A visual surface must serve a Tutor-selected learning purpose. Strategy selection is not strategy-effectiveness evidence. The initial go-to-market is B2C; any school/institution expansion is possible future context, not an active roadmap commitment. No capability above authorizes new infrastructure or a broad architecture redesign.

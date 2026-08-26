# Lina Personal Learning System

## CHILD_SAFETY_POLICY.md

**Status:** Approved policy framework — configurable family-topic defaults remain runtime settings  
**Authority:** Governing child-safety and parent-controlled learning-boundary policy  
**Audience:** Product owner, Codex, AI agents, developers, reviewers  
**Depends on:** `PROJECT_REFERENCE.md`  

---

# 1. Purpose

Lina Personal Learning System serves a child around ten years old. Student-facing behavior must therefore be age-appropriate by design and must not rely on a Tutor prompt alone for enforcement.

This policy separates two different concerns:

1. **Non-overridable child-safety baseline** — system rules that Parent/Admin settings may never weaken.
2. **Parent-controlled learning boundaries** — family-sensitive or age-sensitive topics that a Parent/Admin may configure from the dashboard.

The non-overridable baseline must be enforced before any student-facing generation. For a normal Tutor turn, configurable Parent Boundary applicability is semantically determined inside the same primary Tutor call; the server then resolves the effective Parent setting and enforces the final visible response before it is streamed or persisted.

---

# 2. Authority Order

```text
System / platform safety requirements
        ↓
Non-overridable child-safety baseline
        ↓
Parent-controlled learning boundaries
        ↓
Age-appropriateness policy
        ↓
Tutor / Vision / Artifact / Web behavior
```

Parent settings may restrict discussion further but may never weaken the non-overridable baseline.

---

# 3. Non-Overridable Child-Safety Baseline

The following categories are protected at system level and are not exposed as “Allow” switches to the Parent/Admin:

- explicit sexual content, sexual exploitation, or grooming behavior,
- self-harm or dangerous self-injury guidance,
- practical instruction for weapons, dangerous substances, or hazardous activities,
- drug-related or other clearly dangerous behavior guidance,
- graphic or severely disturbing content inappropriate for a child,
- unsafe handling or disclosure of sensitive personal information,
- unsafe requests involving real-world danger,
- other content prohibited by the platform's applicable safety requirements.

The exact classifier/enforcement implementation may evolve, but the baseline itself is protected.

## 3.1 Response Principle

When a topic is restricted by the non-overridable baseline:

- do not elaborate on harmful details,
- do not shame or alarm Lina,
- keep the response short and age-appropriate,
- redirect toward a safe alternative or a trusted adult when appropriate,
- preserve the learning session when a normal redirect is sufficient.

---

# 4. Parent-Controlled Learning Boundaries

Some topics are not inherently system-safety violations but may be sensitive for a family or intentionally reserved for parent discussion.

These topics are configurable in:

`Parent Dashboard → Settings → Learning Boundaries`

Every configurable topic uses exactly one of three states:

## 4.1 `ALLOW`

The Tutor may discuss the topic normally, subject to the non-overridable safety baseline and general age-appropriateness.

## 4.2 `AGE_APPROPRIATE_ONLY`

The Tutor may discuss the topic, but only with simplified framing appropriate for Lina's age and without adult-level detail.

## 4.3 `REDIRECT_TO_PARENT`

The Tutor should not elaborate. It should briefly and naturally suggest discussing the topic with a parent and then offer to continue with another safe learning topic.

Example behavior:

> “هذا موضوع أحسن تحكي فيه مع بابا أو ماما. إذا بدك نكمل سؤالك عن العلوم أنا معك.”

The restriction itself should not become a dramatic event.

---

# 5. Initial Configurable Topic Catalog

The catalog must be data/configuration-driven rather than hardcoded into Tutor prompts.

Initial categories:

| Topic category | Runtime states | Initial MVP default |
|---|---|---|
| Religion | Allow / Age-appropriate only / Redirect to parent | **Redirect to parent** |
| Restricted sexual content / sex behavior | Allow / Age-appropriate only / Redirect to parent | **Redirect to parent** |
| Relationships | Allow / Age-appropriate only / Redirect to parent | Age-appropriate only |
| Politics / current affairs | Allow / Age-appropriate only / Redirect to parent | Age-appropriate only |
| Death / grief | Allow / Age-appropriate only / Redirect to parent | Age-appropriate only |
| Money / family finances | Allow / Age-appropriate only / Redirect to parent | Age-appropriate only |

The Parent/Admin may change configurable categories at runtime. Additional family-sensitive categories may be added later without changing the core Tutor architecture.

---

# 6. Runtime Enforcement Contract

Student input follows this conceptual flow:

```text
Student input
    ↓
Deterministic hard baseline evaluation
    ├── protected baseline? → enforce protected behavior and stop
    ↓
Compact effective Parent Boundary settings
    ↓
One primary Tutor call emits semantic category / applicability / proposed action
    ↓
Server resolves effective Parent setting and enforces final visible response
```

The normal Tutor path must not add a second classifier or model call for Parent Boundary applicability. The typed Tutor metadata is not policy authority: the server-owned effective setting wins, and redirect wording is server-composed from bounded fragments or a deterministic fallback.

---

# 7. Coverage Across Student-Facing Capabilities

This policy applies to:

- Tutor text responses,
- speech/transcript-driven Tutor interactions,
- Vision interpretation of student images,
- annotations on student images,
- reconstructed visual explanations,
- interactive HTML/SVG learning artifacts,
- generated images if enabled later,
- web-derived information if enabled later,
- science experiments or hands-on activity suggestions.

No student-facing tool may bypass the policy because it is “only a visual” or “only a tool call.”

---

# 8. Parent Dashboard Requirements

The Learning Boundaries UI must:

- show the configurable topic catalog,
- expose only the three approved states,
- explain each state in plain language,
- make clear that some system-safety protections cannot be disabled,
- persist settings per student,
- record policy version and last update time,
- take effect without deployment.

The Parent/Admin must not be shown a switch that implies the protected safety baseline can be disabled.

---

# 9. Data and Audit Requirements

For policy-relevant student interactions, retain enough metadata to debug behavior without needlessly duplicating sensitive content.

Recommended audit fields:

- student ID,
- source message/interaction reference,
- policy category,
- baseline vs parent-boundary source,
- effective action,
- parent policy version,
- policy-engine version,
- timestamp,
- downstream tool/tutor action.

The original interaction remains governed by the project's raw-history policy.

---

# 10. Change Governance

Changes requiring Product Owner approval:

- weakening or removing a protected baseline category,
- adding a fourth parent-boundary state,
- changing the meaning of `ALLOW`, `AGE_APPROPRIATE_ONLY`, or `REDIRECT_TO_PARENT`,
- allowing Parent settings to override protected safety,
- moving enforcement to prompt-only behavior.

Implementation details that may evolve without changing the policy contract:

- same-call semantic metadata/provider parsing,
- deterministic hard-baseline implementation,
- UI layout,
- exact wording of safe redirects,
- internal logging mechanics.

---

# 11. Required Verification

Before Lina-facing release, test at minimum:

1. protected baseline content cannot be enabled from Parent settings,
2. Religion set to `REDIRECT_TO_PARENT` causes a calm redirect and no substantive discussion,
3. the same configurable category set to `ALLOW` is handled within age/safety rules,
4. `AGE_APPROPRIATE_ONLY` avoids adult-level detail,
5. artifacts and Vision-derived responses obey the same policy,
6. policy changes take effect without deployment,
7. policy decisions are auditable,
8. normal Math/Science requests are not unnecessarily blocked.

---

# 12. Policy Invariants

1. Safety baseline is not parent-overridable.
2. Parent boundaries may only restrict further, never weaken baseline safety.
3. Parent-configurable topics use only `ALLOW`, `AGE_APPROPRIATE_ONLY`, or `REDIRECT_TO_PARENT`.
4. Prompt instructions alone are not considered enforcement.
5. Student-facing redirects are calm, short, and non-shaming.
6. The same policy governs text, Vision, artifacts, and future tools.
7. Safety enforcement must not unnecessarily disrupt normal learning.

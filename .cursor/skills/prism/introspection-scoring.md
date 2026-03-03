# Introspection Scoring — Project Prism

> Playbook for the Agentic Readiness Score (ARS) and prompt quality assessment.

---

## 1. Overview

**Introspection** evaluates prompt quality before and after optimization. The **Agentic Readiness Score (ARS)** is a 0–100 composite score derived from five dimensions, each scored 0–10.

**Formula**: ARS = Structure + Specificity + Security + Cache-Friendliness + Model Alignment

Each dimension is independently scored; the sum gives the total ARS. A prompt with full marks in all dimensions scores 100.

---

## 2. Scoring Rubric

### Structure (0–10)

| Score | Band | Criteria |
|-------|------|----------|
| 0 | None | No discernible structure; instructions and context interleaved |
| 1–2 | Minimal | Single block of text; no sections or tags |
| 3–4 | Basic | Some paragraph breaks; implicit sections |
| 5 | Partial | Clear sections but no XML tags; task and context somewhat separated |
| 6–7 | Good | XML tags used for at least task and context; logical flow |
| 8–9 | Strong | Full XML tagging (task, context, constraints, format); well-organized |
| 10 | Full | Complete structure: XML tags, sections, examples; optimal for model parsing |

### Specificity (0–10)

| Score | Band | Criteria |
|-------|------|----------|
| 0 | Vague | All goals are subjective ("better", "good", "quick") |
| 1–2 | Mostly vague | Few measurable criteria |
| 3–4 | Mixed | Some specific targets; many vague adjectives |
| 5 | Moderate | Roughly half specific (word counts, formats, criteria) |
| 6–7 | Good | Most goals measurable; minor vagueness |
| 8–9 | Strong | Clear, measurable goals; minimal filler |
| 10 | Full | Fully measurable; no vague adjectives; explicit criteria |

### Security (0–10)

| Score | Band | Criteria |
|-------|------|----------|
| 0 | Critical | Unredacted PII (SSN, API key, etc.) or direct injection present |
| 1–2 | Severe | Multiple security issues; should not proceed |
| 3–4 | Poor | Soft PII present; injection risk; needs sanitization |
| 5 | Moderate | Warnings only; no critical issues; some redaction needed |
| 6–7 | Good | Clean after redaction; minor warnings logged |
| 8–9 | Strong | No PII or injection; minimal ambiguity |
| 10 | Full | Fully sanitized; no security concerns |

### Cache-Friendliness (0–10)

| Score | Band | Criteria |
|-------|------|----------|
| 0 | None | No stable prefix; fully dynamic; no cache opportunity |
| 1–2 | Minimal | Very short prompt; caching not applicable |
| 3–4 | Low | Some static content but not separated; mixed with dynamic |
| 5 | Partial | Static and dynamic content identified but not optimized |
| 6–7 | Good | Stable prefix identified; cache_control used in some places |
| 8–9 | Strong | Long stable prefix; clear cache_control breakpoints |
| 10 | Full | Optimal: long static context in cache_control blocks; dynamic content clearly separated |

### Model Alignment (0–10)

| Score | Band | Criteria |
|-------|------|----------|
| 0 | Anti-patterns | Uses patterns known to degrade performance for target model |
| 1–2 | Poor | Misaligned; wrong CoT triggers; incompatible format |
| 3–4 | Weak | Some anti-patterns; suboptimal structure |
| 5 | Neutral | No strong alignment or misalignment |
| 6–7 | Good | Uses recommended patterns for target model |
| 8–9 | Strong | CoT triggers, XML, prefill aligned with model best practices |
| 10 | Full | Fully aligned with target model's documented best practices |

---

## 3. Score Interpretation

| ARS Band | Label | Recommended Action |
|----------|-------|---------------------|
| **90–100** | Excellent | Proceed as-is. Optional minor tweaks. |
| **75–89** | Good | Minor tweaks suggested. Review dimension(s) below 8. |
| **60–74** | Needs work | Specific improvements listed. Consider `/prism improve-prompt`. |
| **40–59** | Poor | `/prism improve-prompt` strongly recommended. Do not use in production without refinement. |
| **0–39** | Unusable | Block or require rewrite. Critical issues (security, structure, or alignment) must be addressed. |

### Per-Dimension Guidance

When a dimension scores below 7, the Why Log should include:

- **Structure**: Suggest XML tags, section breaks, or task decomposition
- **Specificity**: List vague phrases and suggest measurable alternatives
- **Security**: List redactions applied or injection/injection risks
- **Cache-Friendliness**: Suggest cache_control placement or static/dynamic separation
- **Model Alignment**: Suggest model-specific optimizations (CoT, prefill, etc.)

---

## 4. Why Log Format

Every scored prompt is accompanied by a **Why Log** entry that explains the scores and provides actionable feedback.

### JSON Schema

```json
{
  "prompt_id": "uuid",
  "timestamp": "ISO8601",
  "ars_total": 72,
  "dimensions": {
    "structure": 6,
    "specificity": 7,
    "security": 10,
    "cache_friendliness": 5,
    "model_alignment": 8
  },
  "target_model": "claude-sonnet-4-20250514",
  "recommendations": [
    "Add <task> and <context> XML tags",
    "Replace 'brief' with '50-75 words'",
    "Consider cache_control for document block"
  ],
  "redactions_applied": ["EMAIL_REDACTED"],
  "warnings": []
}
```

### Plain-Text Format

```
ARS: 72/100 (Needs work)
Structure: 6 | Specificity: 7 | Security: 10 | Cache: 5 | Model: 8

Recommendations:
- Add <task> and <context> XML tags
- Replace 'brief' with '50-75 words'
- Consider cache_control for document block

Redactions: [EMAIL_REDACTED]
```

---

## 5. Verbosity Anti-Patterns

Reference: **verbosity_patterns.json** (in `.cursor/skills/prism/` or project config).

Verbosity patterns include filler phrases that reduce specificity and clarity:

- "kind of", "sort of", "basically", "actually", "just", "really"
- "I think", "I believe", "it seems like"
- "a lot of", "a bit", "somewhat", "quite"
- Redundant hedges: "perhaps maybe", "might possibly"

### Impact on Specificity Score

- **Filler phrase density** = (count of filler phrases) / (total words) × 100
- Density > 5%: Specificity score capped at 6
- Density > 10%: Specificity score capped at 4
- Density > 15%: Specificity score capped at 2

The verbosity_patterns.json file defines the full list of patterns and their weights for scoring.

---

## 6. Personal Efficiency Tracking

The prompt log feeds into long-term improvement by tracking:

- **Efficiency ratio** = (Successful completions) / (Total prompts sent)
- **ARS trend** = Average ARS over time (weekly or monthly)
- **Dimension gaps** = Most frequently low-scoring dimensions across users or sessions

### Efficiency Ratio Formula

```
Efficiency Ratio = (Prompts that achieved intended outcome) / (Total prompts)
```

A higher ARS correlates with a higher efficiency ratio. Logging ARS per prompt allows analysis of which dimensions most impact success.

### Feedback Loop

1. Score prompt → record ARS and Why Log
2. Apply recommendations → re-score
3. Track delta (improvement)
4. Aggregate: identify common improvement patterns for future prompts

---

## 7. Microsoft Prompt Advisor Comparison

Microsoft Prompt Advisor uses a **0–100 confidence scale** to assess prompt quality. ARS maps to this conceptually:

| ARS Band | MS Prompt Advisor Equivalent | Validation |
|----------|------------------------------|------------|
| 90–100 | High confidence (80–100) | Both indicate production-ready |
| 75–89 | Medium-high (60–80) | Minor improvements suggested |
| 60–74 | Medium (40–60) | Needs refinement |
| 40–59 | Low (20–40) | Significant work required |
| 0–39 | Very low (0–20) | Not suitable for use |

**Alignment**: ARS provides a structured, dimension-level breakdown that MS Prompt Advisor's single score does not. The five dimensions (Structure, Specificity, Security, Cache-Friendliness, Model Alignment) offer actionable guidance beyond a single confidence number, validating the multi-dimensional approach for prompt optimization.

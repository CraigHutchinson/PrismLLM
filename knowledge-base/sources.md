# Knowledge Base Sources

Bibliography for all entries in `rules.json`. Each source is tagged with the pillar(s) it informs, the model version scope, and the collection date.

---

## Official Anthropic Documentation

| ID | Title | URL | Pillar(s) | Model Scope | Source Type | Date |
|----|-------|-----|-----------|-------------|-------------|------|
| A-01 | Prompt Engineering Overview | https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview | Refraction, Introspection | all | official | 2025-03 |
| A-02 | Use XML Tags | https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags | Refraction | claude-3.5+ | official | 2025-03 |
| A-03 | Chain-of-Thought Prompting | https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/chain-of-thought | Refraction | all | official | 2025-03 |
| A-04 | Prompt Caching | https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching | Refraction, Introspection | claude-3.5+ | official | 2025-03 |
| A-05 | Claude 4 Best Practices | https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices | Refraction, Introspection | claude-4+ | official | 2025-05 |
| A-06 | Extended Thinking (Claude 3.7+) | https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking | Refraction | claude-3.7+ | official | 2025-03 |
| A-07 | Claude Models Overview | https://docs.anthropic.com/en/docs/about-claude/models/overview | Introspection | all | official | 2026-01 |
| A-08 | System Prompts | https://docs.anthropic.com/en/docs/build-with-claude/system-prompts | Refraction | all | official | 2025-03 |
| A-09 | Pre-filling Claude's Response | https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prefill-claudes-response | Refraction | claude-3.5+ | official | 2025-03 |

---

## Security & Sanitization

| ID | Title | URL | Pillar(s) | Model Scope | Source Type | Date |
|----|-------|-----|-----------|-------------|-------------|------|
| S-01 | OWASP Top 10 for LLM Applications | https://owasp.org/www-project-top-10-for-large-language-model-applications/ | Sanitization | all | official | 2025-01 |
| S-02 | LLM Guard — PII Scanner Patterns | https://llm-guard.com/ | Sanitization | all | research | 2025-02 |
| S-03 | Microsoft MSRC: Indirect Prompt Injection Defense | https://msrc.microsoft.com/blog/2024/02/announcing-microsoft-s-new-principles-and-safeguards-for-frontier-ai-security/ | Sanitization | all | official | 2024-02 |
| S-04 | ACL 2025: Evasion Attacks Against Prompt Injection Detection | https://aclanthology.org/ | Sanitization | all | research | 2025-05 |

---

## Community & Research

| ID | Title | URL | Pillar(s) | Model Scope | Source Type | Date |
|----|-------|-----|-----------|-------------|-------------|------|
| C-01 | PromptingGuide.ai | https://www.promptingguide.ai/ | Refraction, Introspection | all | community | 2025-06 |
| C-02 | dbreunig.com: System Prompt Evolution Across Claude Versions | https://dbreunig.com/2025/03/claude-system-prompts.html | Introspection | claude-3.5+, 3.7+, 4+ | community | 2025-03 |
| C-03 | pantaleone.net: Claude Opus 4.6 System Prompt Analysis | https://pantaleone.net/claude-opus-46-system-prompt | Introspection | claude-4+ | community | 2025-05 |
| C-04 | dbreunig.com: Overcoming Bad Prompts | https://dbreunig.com/2025/02/overcoming-bad-prompts.html | Refraction, Introspection | all | community | 2025-02 |
| C-05 | OpenAI Community: Prompt Engineering Showcase | https://community.openai.com/t/prompt-engineering-showcase | Refraction | all | community | 2025-01 |
| C-06 | ResearchRubrics: 6-Axis Agent Evaluation Framework | https://github.com/researchrubrics/rubrics | Introspection | all | research | 2025-04 |

---

## Prior Art Tools

These tools exist in the prompt optimization space. Each entry notes which Prism pillar and rule categories they inform.

### Microsoft Prompt Advisor
- **URL**: https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/kit-prompt-advisor
- **Type**: Enterprise SaaS (Power Platform + AI Builder credits required)
- **Prism Pillars**: Introspection (confidence scoring model)
- **Rule categories informed**: `scoring-structure`, `scoring-specificity` (int-001, int-002)
- **Key insight**: The 0–100 confidence scale with High/Medium/Low bands directly validates Prism's ARS tiering. Score calibration should use the same band boundaries (High ≥ 75, Medium 50–74, Low < 50).
- **Limitations**: UI-only, no IDE integration, requires Dataverse, no PII scanning, no personal pattern learning.

### Promptfoo
- **URL**: https://www.promptfoo.dev/
- **Type**: Open-source CLI for prompt regression testing
- **Prism Pillars**: Introspection (evaluation dimensions)
- **Rule categories informed**: `scoring-structure`, `scoring-specificity`, scoring rubric design (int-001 through int-010)
- **Key insight**: Promptfoo evaluates on dimensions: correctness, relevance, toxicity, latency. These map onto Prism's ARS dimensions and validate the multi-axis rubric approach.
- **Limitations**: Batch test-time evaluation only, not pre-flight, no PII scanning, no hook system.

### DSPy (Stanford NLP)
- **URL**: https://github.com/stanfordnlp/dspy
- **Type**: Research framework for programmatic prompt optimization
- **Prism Pillars**: Refraction (few-shot injection technique)
- **Rule categories informed**: `few-shot` (ref-007)
- **Key insight**: DSPy's "compiled" few-shot example injection demonstrates that selecting and injecting worked examples at prompt construction time is a proven refraction technique. Rule ref-007 is directly informed by this.
- **Limitations**: Requires Python expertise and labeled training data, not end-user facing, no sanitization.

### PromptLayer
- **URL**: https://promptlayer.com/
- **Type**: LLM observability and session replay platform
- **Prism Pillars**: Introspection (session replay concept → prompt log design)
- **Rule categories informed**: `verbosity-detection`, personal efficiency tracking (int-006)
- **Key insight**: PromptLayer's session replay confirms the value of logging prompts for post-hoc analysis. Prism's `.prism/prompt-log.jsonl` and pattern analysis loop is directly inspired by this pattern, but applied pre-flight and kept local.
- **Limitations**: Observational after the fact, prompts already sent to model, no pre-flight blocking, not local/private.

### Anthropic Prompt Improver (Claude.ai built-in)
- **URL**: https://claude.ai (built-in feature)
- **Type**: Single-turn rewrite using Claude's internal prompting knowledge
- **Prism Pillars**: Refraction
- **Rule categories informed**: All refraction categories — validates the refraction pillar concept
- **Key insight**: Validates that model-guided prompt rewriting is useful. Prism extends this with: multi-model support, pre-flight sanitization, scoring, personal pattern learning, and cross-platform IDE integration.
- **Limitations**: Claude.ai only, no scoring, no sanitization, no hook system, no pattern learning, no cross-platform.

### PromptPerfect (Jina AI)
- **URL**: https://promptperfect.jina.ai/
- **Type**: Cloud SaaS multi-model prompt optimizer
- **Prism Pillars**: Refraction, Introspection
- **Rule categories informed**: Validates multi-model optimization approach
- **Key insight**: Multi-model support (GPT, Claude, Gemini) confirms that prompt engineering rules need model-version awareness. Prism's `model_applies` field addresses this directly.
- **Limitations**: Subscription-based, no IDE integration, no security/sanitization, prompts sent to third party.

---

## KB Update Workflow

When adding new sources:

1. Add entry to the relevant table above with a new ID (A-xx, S-xx, C-xx).
2. Identify which rules the source informs and update `source_url` in `rules.json`.
3. If the source reveals a rule that should be added, create a new entry in `rules.json` following the schema.
4. Update `model_applies` on existing rules if the source clarifies version-specific behaviour.
5. Add `model_deprecated` to rules where the source indicates the advice no longer applies.

**Version tracking trigger**: Whenever Anthropic releases new model documentation, run a diff against the Confirmed Source Catalogue and update affected rules.

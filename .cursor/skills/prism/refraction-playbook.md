# Refraction Playbook — Project Prism

> Reference document for the Prism agent when analyzing prompts for structural optimization.

---

## 1. Overview

**Refraction** is the structural optimization of prompts to improve clarity, model comprehension, and output quality. It is applied when:

- A prompt is ambiguous or poorly structured
- Output format is unspecified or inconsistent
- Context is mixed with instructions
- The prompt would benefit from caching, tagging, or decomposition
- Model-specific optimizations are needed (Claude 3.5, 3.7, 4.0)

Refraction does **not** change the user's intent—it reorganizes and clarifies the prompt so the model can fulfill that intent more reliably.

---

## 2. XML Tagging Rules

XML tags provide explicit structure that helps models parse intent, separate context from instructions, and apply appropriate reasoning modes.

### When to Use XML Tags

- **Always** when the prompt has distinct sections (task, context, constraints)
- **Recommended** for prompts > 100 words
- **Required** when mixing static context with dynamic instructions (for cache optimization)

### Tag Names and Purposes

| Tag | Purpose | Example Use |
|-----|---------|-------------|
| `<task>` | Primary instruction or goal | "Summarize the following document" |
| `<context>` | Background information, documents, data | Pasted text, file contents, prior conversation |
| `<constraints>` | Hard limits, rules, boundaries | "Do not exceed 200 words", "No speculation" |
| `<format>` | Output structure specification | JSON schema, markdown layout, section order |
| `<document>` | Long-form static content (cache candidate) | Reference docs, knowledge bases |
| `<thinking>` | Explicit reasoning request | "Think step by step", "Show your work" |
| `<examples>` | Few-shot demonstrations | Input/output pairs for format or style |

### Claude Version Support

| Claude Version | XML Support | Best Practices |
|----------------|-------------|----------------|
| Claude 3.5 | Good | Use clear, consistent tags; avoid deeply nested tags |
| Claude 3.7 | Excellent | Full support; prefers well-formed tags |
| Claude 4.0 | Excellent | Strong adherence to tagged sections; benefits from `<thinking>` for complex tasks |

### Example

```
<task>
Summarize the key findings from the research document below.
</task>

<context>
<document>
[Long research document content...]
</document>
</context>

<constraints>
- Maximum 150 words
- Use bullet points
- No citations
</constraints>
```

---

## 3. Prompt Caching Strategy

Prompt caching reduces latency and cost by caching a stable prefix of the prompt. The model reuses cached tokens instead of reprocessing them.

### When to Cache

- **Large static context** (> 1,000 tokens): reference docs, codebases, knowledge bases
- **Repeated prefixes** across multiple turns: system prompts, long instructions
- **Stable document blocks** that change infrequently

### When NOT to Cache

- Highly dynamic content (user input, timestamps, session IDs)
- Content that changes every request
- Very short prompts (< 500 tokens) — overhead may outweigh benefit

### cache_control Breakpoints

Use `cache_control` blocks to mark boundaries. Content before a breakpoint can be cached; content after is treated as dynamic.

```
<document cache_control="ephemeral">
[Large static reference document - will be cached]
</document>

<task>
[User's specific question - not cached]
</task>
```

### Code Example (API)

```python
from anthropic import Anthropic

client = Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "<document cache_control=\"ephemeral\">\n[Your long reference content here]\n</document>"
        }
    ],
    messages=[
        {"role": "user", "content": "Based on the document above, answer: What is X?"}
    ]
)
```

### Claude Version Support

| Claude Version | Cache Support |
|----------------|---------------|
| Claude 3.5 | Yes |
| Claude 3.7 | Yes |
| Claude 4.0 | Yes (recommended for long contexts) |

---

## 4. Chain-of-Thought (CoT) Trigger Library

Trigger phrases activate extended reasoning mode. Choose triggers that match the task type and model.

### Mathematical / Numerical

| Trigger | Claude 3.5 | Claude 4+ | Notes |
|---------|------------|-----------|-------|
| "Think step by step" | ✓ | ✓✓ | Universal, reliable |
| "Show your work" | ✓ | ✓✓ | Good for math |
| "Reason through each step" | ✓ | ✓✓ | Explicit |
| "Let's solve this systematically" | ✓ | ✓ | Slightly softer |
| "Work through the calculation" | ✓ | ✓ | Math-specific |

### Analytical / Logical

| Trigger | Claude 3.5 | Claude 4+ | Notes |
|---------|------------|-----------|-------|
| "Analyze this carefully" | ✓ | ✓✓ | Strong for analysis |
| "Consider each factor" | ✓ | ✓ | Structured thinking |
| "Walk through your reasoning" | ✓ | ✓✓ | Clear CoT request |
| "What are the key considerations?" | ✓ | ✓ | Question-based |
| "Break down the logic" | ✓ | ✓✓ | Good for argumentation |

### Creative / Generative

| Trigger | Claude 3.5 | Claude 4+ | Notes |
|---------|------------|-----------|-------|
| "Explore different angles first" | ✓ | ✓ | Pre-generation thinking |
| "Consider alternatives before deciding" | ✓ | ✓✓ | Reduces premature commitment |
| "Brainstorm options, then choose" | ✓ | ✓ | Two-phase creative |

### Code / Technical

| Trigger | Claude 3.5 | Claude 4+ | Notes |
|---------|------------|-----------|-------|
| "Trace through the logic" | ✓ | ✓✓ | Debugging, code review |
| "Explain your approach before coding" | ✓ | ✓✓ | Design-first |
| "Identify edge cases first" | ✓ | ✓ | Defensive coding |

### Best Practices

- **Claude 4+**: Prefer explicit triggers like "Think step by step" or "Walk through your reasoning"
- **Claude 3.5**: "Think step by step" and "Show your work" are most reliable
- Place triggers in `<task>` or `<thinking>` sections
- Avoid stacking multiple triggers—one clear phrase is sufficient

---

## 5. Pre-filled Response Headers (Assistant-prefill)

Assistant-prefill guides the model to start its response in a specific format, reducing format drift and improving consistency.

### When to Use

- JSON output requirements
- Structured markdown (headings, tables)
- Code blocks with specific language
- Multi-section analysis with fixed structure

### Examples

**JSON Output**

```
Respond with a JSON object. Start your response with the opening brace.

Expected format:
{"summary": "...", "key_points": ["...", "..."], "recommendation": "..."}
```

Or with prefill:

```
Respond with valid JSON. Begin your response with: {"summary":
```

**Markdown Table**

```
Provide your analysis in a markdown table. Start with:

| Category | Finding | Impact |
|----------|---------|--------|
```

**Code Block**

```
Provide the solution as Python code. Begin with:

```python
```

**Structured Analysis**

```
Your response must follow this structure. Start with:

## Summary
[Your summary here]

## Key Findings
1.
```

### Claude Version Support

- Claude 3.5: Supports prefill; may need stronger format instructions
- Claude 3.7 / 4.0: Strong adherence to prefill; use for strict formats

---

## 6. Task Decomposition Patterns

Bundled prompts (multiple tasks in one) reduce clarity and make evaluation harder. Decomposition splits them into sequenced, single-purpose prompts.

### Decision Criteria

| Criterion | Action |
|----------|--------|
| 3+ independent tasks | **Suggest split** into separate prompts |
| Tasks with different output formats | **Suggest split** |
| Tasks with conflicting constraints | **Suggest split** |
| Tasks that depend on each other | **Sequence** (Task A → Task B) |
| Single task with sub-steps | **Keep together** but add structure |

### Detection Patterns

- Conjunctions: "and also", "as well as", "in addition"
- Numbered lists of distinct actions: "1. Summarize... 2. Translate... 3. Format..."
- Mixed verbs: "analyze, summarize, and recommend"
- Multiple output formats requested in one prompt

### Sequencing Patterns

**Pattern A: Linear dependency**
```
Step 1: Extract key facts from the document.
Step 2: Using those facts, write a one-paragraph summary.
```

**Pattern B: Parallel then merge**
```
Step 1: Analyze section A and section B separately.
Step 2: Combine findings into a unified report.
```

**Pattern C: Iterative refinement**
```
Step 1: Draft initial response.
Step 2: Review for clarity and conciseness.
Step 3: Apply final formatting.
```

---

## 7. Output Format Specification

Explicit format specification reduces ambiguity and improves consistency.

### Length Specification

| Spec Type | Example | Use Case |
|-----------|---------|----------|
| Word count | "Respond in 100–150 words" | Prose, summaries |
| Sentence count | "Provide 3–5 sentences" | Brief answers |
| Bullet count | "List exactly 5 key points" | Structured lists |
| Paragraph count | "Write 2 paragraphs" | Medium-length prose |
| Character limit | "Under 500 characters" | Tweets, snippets |

### Format Type

| Type | Specification Example |
|------|------------------------|
| JSON | "Respond with valid JSON matching this schema: {...}" |
| Markdown | "Use markdown with ## headings and bullet lists" |
| Prose | "Write in clear, formal prose" |
| Code | "Provide Python code in a fenced code block" |
| Table | "Format as a markdown table with columns: X, Y, Z" |

### Templates

**Template: Structured Summary**
```
<format>
- Length: 150–200 words
- Structure: 3 paragraphs (Overview, Key Points, Conclusion)
- Style: Professional, third person
</format>
```

**Template: JSON Response**
```
<format>
Output: Valid JSON
Schema: {"items": [{"id": "string", "value": "string"}], "count": number}
Start response with: {
</format>
```

**Template: Bullet List**
```
<format>
- Exactly 5 bullet points
- Each point: 1–2 sentences max
- Use • for bullets
</format>
```

---

## 8. Specificity Upgrade Patterns

Vague phrases reduce model precision. Replace with measurable, concrete alternatives.

| Vague Phrase | Specific Alternative |
|--------------|----------------------|
| "brief" | "50–75 words" or "3 sentences" |
| "detailed" | "Include X, Y, and Z" or "500+ words" |
| "soon" | "Within 24 hours" or "By [date]" |
| "better" | "10% faster" or "fewer than 3 errors" |
| "simple" | "No jargon" or "5th-grade reading level" |
| "comprehensive" | "Cover A, B, C, and D" |
| "quick" | "Under 2 minutes" or "3 bullet points" |
| "high quality" | "Grammatically correct, no filler" |
| "professional" | "Formal tone, third person, no contractions" |
| "thorough" | "Address each of the 5 criteria" |
| "concise" | "Maximum 100 words" |
| "as much as possible" | "Top 5" or "All items in the list" |

---

## 9. Role/Persona Assignment

Assigning a role helps the model adopt appropriate tone, domain knowledge, and constraints.

### When to Assign a Role

- Domain-specific tasks (legal, medical, technical)
- Tone requirements (formal, friendly, instructional)
- Expertise framing ("as an expert in X")
- Constraint enforcement ("as a security auditor")

### Template Pattern

```
You are [ROLE] with expertise in [DOMAIN]. Your task is to [TASK].
[Optional: Constraints specific to the role]
```

### Examples by Domain

**Technical**
```
You are a senior software engineer specializing in Python and API design.
Review the code below and suggest improvements for readability and performance.
```

**Legal**
```
You are a legal analyst (not a lawyer). Summarize the contract terms in plain language.
Do not provide legal advice.
```

**Creative**
```
You are a marketing copywriter. Write a tagline for [product] that is memorable and under 10 words.
```

**Educational**
```
You are a patient teacher explaining concepts to a beginner. Use simple language and one example per concept.
```

---

## 10. Format Selection — Which Structural Syntax to Use

Different model families respond best to different structural syntaxes. Always
select format **before** writing the prompt; Prism auto-detects this via
`scripts/format_output.py --detect-format` or `platform_model.detect_platform()`.

### The Three Formats

| Format | Syntax | Default for | Best when |
|--------|--------|-------------|-----------|
| **Markdown** | `## Task` / `## Context` | All unknown platforms | GPT-4 (Copilot), Gemini, cross-model portability |
| **XML** | `<task>` / `<context>` | Cursor, Claude Code | Claude 3.5+ — strongest adherence, cache_control support |
| **Prefixed** | `TASK:` / `CONTEXT:` | Explicit fallback only | Constrained contexts, older/smaller models |

### Decision Logic (rules ref-016, ref-017, ref-018)

```
platform == cursor or claude_code  →  use xml
platform == copilot or unknown     →  use markdown   ← default
explicit --format flag             →  use that format
constrained context window (<200t) →  use prefixed
```

Run `python scripts/format_output.py --detect-format` to check what format Prism
would choose in the current environment.

### Side-by-Side Example

**Markdown (default/portable)**
```markdown
## Task
Add a login page: form fields, validation, POST to /auth/login.

## Context
Flask backend, UserSession model already exists.

## Constraints
No third-party auth libs. Use the existing UserSession model.
```

**XML (Claude upgrade)**
```xml
<task>Add a login page: form fields, validation, POST to /auth/login.</task>

<context>Flask backend, UserSession model already exists.</context>

<constraints>No third-party auth libs. Use the existing UserSession model.</constraints>
```

**Prefixed (fallback)**
```
TASK: Add a login page: form fields, validation, POST to /auth/login.

CONTEXT: Flask backend, UserSession model already exists.

CONSTRAINTS: No third-party auth libs. Use the existing UserSession model.
```

### Using the Format Renderer

```bash
# Detect format for current environment
python scripts/format_output.py --detect-format

# Render a prompt (uses auto-detected format)
python scripts/format_output.py \
  --task "Add a login page" \
  --context "Flask app, UserSession model" \
  --constraints "No third-party auth libs"

# Force XML for a Claude-specific prompt
python scripts/format_output.py --task "..." --format xml

# Force Markdown for portability
python scripts/format_output.py --task "..." --format markdown

# JSON output (format name + rendered text)
python scripts/format_output.py --task "..." --json
```

### When Refracting a User Prompt

1. Call `select_format(platform)` or `--detect-format` first.
2. Use that format for all structural blocks in the rewritten prompt.
3. Note the format in the Why Log: `[REFRACTION] Format: markdown (portable default) [rule: ref-016]`
4. If the platform is Claude and XML is available, note the upgrade: `[REFRACTION] Format: xml (Claude upgrade) [rule: ref-017]`

---

## 11. Model-Version Alignment Notes

### Claude 3.5

- **Strengths**: Fast, good at code, reliable CoT with "Think step by step"
- **Behaviors**: May need explicit format instructions; XML support is good but not as strong as 4.0
- **Targeting**: Use clear structure, avoid overly complex nesting

### Claude 3.7

- **Strengths**: Balanced performance, strong instruction following
- **Behaviors**: Good XML adherence; benefits from well-formed tags
- **Targeting**: Use full XML structure; prefill works well

### Claude 4.0

- **Strengths**: Best reasoning, strongest structure adherence, excellent for long context
- **Behaviors**: Highly responsive to `<thinking>`; benefits from cache_control for long docs
- **Targeting**: Use `<thinking>` for complex analysis; leverage caching; explicit CoT triggers

### Summary Table

| Optimization | 3.5 | 3.7 | 4.0 |
|--------------|-----|-----|-----|
| XML tags | Good | Excellent | Excellent |
| cache_control | Yes | Yes | Yes (recommended) |
| CoT triggers | "Think step by step" | Same | Same + "Walk through reasoning" |
| Prefill | Good | Excellent | Excellent |
| Role assignment | Good | Good | Good |

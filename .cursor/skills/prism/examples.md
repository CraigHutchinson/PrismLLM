# Prism Examples: Before & After Prompt Transformations

Four complete walkthroughs showing how Prism transforms raw prompts into optimized, safe, and high-scoring versions. Each example includes the Why Log and ARS score.

---

## Example 1: The Bundled Task

**Scenario:** A developer is adding a new feature and writes a quick prompt in chat.

### Before (raw user prompt)
```
we shall add a login page to the auth module and also update the tests
```

**Prism analysis:**
- Stage 1 (PII scan): Safe ✓
- ARS before: 22/100 (structure: 2, specificity: 3, security: 10, cache: 2, alignment: 5)

### After (Prism-optimized)
```xml
<context>
Working on the auth module of an existing web application.
</context>

<task>
Add a login page to the auth module. Implement:
1. Login form with email + password fields
2. Client-side validation
3. POST to /auth/login endpoint
4. Error state handling (invalid credentials, network error)
</task>

<constraints>
- Follow the existing component patterns in the auth module
- Do not modify the public API surface
</constraints>

<task>
Write unit tests for the new login page component. Cover:
1. Form renders correctly
2. Validation fires on submit with empty fields
3. Error state displayed on failed API call
4. Success state redirects correctly
</task>
```

**Why Log:**
- `[REFRACTION]` Bundled task ("add login page ... and also update the tests") split into two sequential `<task>` blocks — each is independently testable and reviewable. [rule: ref-006, source: community]
- `[REFRACTION]` Removed "we shall" (royal_we pattern, ~2t saving). Rewrote as direct imperative. [rule: ref-009, source: community]
- `[REFRACTION]` Added `<context>` block to establish the working environment. [rule: ref-001, source: official]
- `[REFRACTION]` Added numbered sub-tasks within each `<task>` block for clarity. [rule: ref-011, source: community]
- `[REFRACTION]` Added `<constraints>` block with explicit acceptance criteria. [rule: ref-012, source: community]
- `[SANITIZATION]` No PII or injection risks detected. ✓ [rule: san-001]
- `[INTROSPECTION]` Structure improved from no XML to full block separation. [rule: int-001]

**ARS Score: 88/100**
- Structure:          9/10
- Specificity:        9/10
- Security:          10/10
- Cache-Friendliness: 8/10  _(static context block is cacheable)_
- Model Alignment:    8/10

---

## Example 2: The Vague Request

**Scenario:** Someone pastes a piece of code and asks for improvements — using only adjectives with no measurable criteria.

### Before (raw user prompt)
```
make it better
```

**Prism analysis:**
- Stage 1 (PII scan): Safe ✓
- ARS before: 8/100 (structure: 0, specificity: 0, security: 10, cache: 0, alignment: 8 — too short to evaluate)

Prism output for `/prism explain`:

```
⚠️ Prism Diagnosis: "make it better"

Issue 1 — Specificity (0/10): "Better" is not measurable. 
The model cannot know if you mean faster, more readable, more secure, 
better tested, or something else entirely.

Issue 2 — Structure (0/10): No context about what "it" refers to, 
no constraints, no format preference.

Issue 3 — Model Alignment: Claude 4 responds better to direct imperatives 
with specific goals than to open-ended improvement requests.

Suggested reframe — run /prism improve-prompt with:
  "Refactor [this function] to improve [readability|performance|security|test coverage].
   Apply [specific technique]. Keep [constraint]."
```

### After (user ran `/prism improve-prompt` with context):
```xml
<context>
The following Python function handles user authentication.
</context>

<task>
Refactor this function to improve readability:
1. Extract the database query into a helper function
2. Replace the nested if-statements with early returns
3. Add a docstring with Args and Returns sections
</task>

<constraints>
- Keep the public function signature unchanged
- Maintain backward compatibility with existing callers
- Output format: complete refactored function only, no explanation
</constraints>
```

**Why Log:**
- `[REFRACTION]` "make it better" → explicit, measurable 3-point refactoring goal. [rule: ref-009]
- `[REFRACTION]` Added `<context>` to identify the subject. [rule: ref-001]
- `[REFRACTION]` Output format constraint added ("complete refactored function only"). [rule: ref-003]
- `[REFRACTION]` Added `<constraints>` with backward compatibility requirement. [rule: ref-012]
- `[SANITIZATION]` No PII detected. ✓
- `[INTROSPECTION]` Specificity dimension: from 0/10 to 9/10. [rule: int-002]

**ARS Score: 91/100**

---

## Example 3: The PII Prompt

**Scenario:** A developer pastes a prompt containing an email address from a real bug report.

### Before (raw user prompt)
```
the user john.doe@example.com is getting a 403 error when accessing the admin panel. 
investigate why they don't have permission and fix it
```

**Stage 1 hook output (no model):**
```
⚡ Prism blocked this prompt.

PII detected: EMAIL
Remove or replace sensitive data before submitting.
Suggested replacement: replace "john.doe@example.com" with a placeholder like
"test-user@example.com" or "[EMAIL_REDACTED]" before submitting.

Edit your prompt and resend, or run /prism hook off to disable.
```

### After (user revised + Prism optimized):
```xml
<context>
A user account (role: regular_user) is receiving 403 Forbidden errors when 
accessing /admin/dashboard. The error occurs consistently after login.
</context>

<task>
Investigate why this account lacks admin panel access and provide the fix.
Work through:
1. Check the permission guard on the /admin routes
2. Verify the user's role assignment in the database schema
3. Identify the code path that sets/reads the admin permission flag
</task>

<constraints>
- Do not expose real user data in your response
- Output: diagnosis + minimal code change required
</constraints>
```

**Why Log:**
- `[SANITIZATION]` Email `john.doe@example.com` was replaced by generic description before submission. [rule: san-001]
- `[REFRACTION]` Vague "investigate and fix" → structured 3-step investigation plan. [rule: ref-006]
- `[REFRACTION]` Added `<context>` with the technical details needed for diagnosis. [rule: ref-001]
- `[REFRACTION]` Added output constraint: "diagnosis + minimal code change". [rule: ref-003]
- `[INTROSPECTION]` Security dimension: 10/10 — no PII in submitted prompt. [rule: int-003]

**ARS Score: 87/100**

---

## Example 4: The Expert Task (with caching)

**Scenario:** A developer regularly asks Claude to review code against a large architecture document. The document is static and should be cached.

### Before (raw user prompt)
```
I would like you to review the following code against our architecture guidelines
[30KB architecture document pasted inline]
Review this function: [function code]
```

**Prism analysis:**
- Verbosity: "I would like you to" → 5t filler
- Cache opportunity: the architecture document never changes — ideal for `cache_control`
- ARS before: 44/100

### After (Prism-optimized with caching):
```xml
<system>
You are a senior software architect reviewing code against the team's guidelines.
</system>

<context cache_control="ephemeral">
Architecture Guidelines (static — review against these on every request):
[30KB architecture document]
</context>

<task>
Review the following function for compliance with the architecture guidelines above.
Focus on: (1) layer violations, (2) dependency direction, (3) naming conventions.
</task>

<code>
[function to review]
</code>

<format>
Return a markdown checklist: ✓ for compliant, ✗ for violations with the specific guideline referenced.
</format>
```

**Why Log:**
- `[REFRACTION]` Added `cache_control="ephemeral"` to the 30KB static document — this prefix will be cached after the first request, saving ~7,500t on every subsequent review. [rule: ref-008, source: official]
- `[REFRACTION]` Removed "I would like you to" preamble (5t filler). [rule: ref-009]
- `[REFRACTION]` Added system prompt with reviewer persona. [rule: ref-010]
- `[REFRACTION]` Separated static document (`<context>`) from dynamic task (`<task>` + `<code>`). [rule: ref-002]
- `[REFRACTION]` Added `<format>` block specifying markdown checklist output. [rule: ref-003]
- `[SANITIZATION]` No PII detected. ✓
- `[INTROSPECTION]` Cache-Friendliness: 9/10 — long stable prefix + explicit `cache_control`. [rule: int-004]

**ARS Score: 94/100**
- Structure:          10/10
- Specificity:         9/10
- Security:           10/10
- Cache-Friendliness:  9/10  _(30KB cached after first call)_
- Model Alignment:     9/10

**Token economics:** First call: ~8,000t (document + task). Subsequent calls (cache hit): ~500t.
For 10 daily reviews, caching saves ~67,500t per day.

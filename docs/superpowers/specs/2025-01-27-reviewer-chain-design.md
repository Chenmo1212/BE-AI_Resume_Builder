# Reviewer Chain Design

**Date:** 2025-01-27  
**Status:** Approved  
**Scope:** Backend (`BE-AI_Resume_Builder`)

---

## Problem

The current pipeline generates resume content in a single pass with no quality gate. Despite having `<Plan>/<Verify>/<Final Answer>` steps in the writer prompts, the LLM self-review is insufficient — outputs consistently violate North American resume standards:

- Work experience highlights are too long (current criteria: >50 words, 2–3 sentences; standard: ≤25 words, 1 sentence)
- Professional summaries are too long (current criteria: 100–200 words; standard: 50–80 words)
- The `improve_final_resume()` step generates critique but its output is never fed back to correct the content

---

## Target Standard

All quality judgments are based on **North American (US/Canada) job market resume conventions**:

| Section | Rule |
|---|---|
| Experience highlight (bullet) | ≤ 25 words, exactly 1 sentence, starts with action verb, contains quantifiable metric when source data allows |
| Professional summary | 50–80 words total, 3–4 sentences, no first-person "I" |

---

## Solution: Independent Reviewer Chain with Retry Loop

Introduce a `reviewer` chain that is completely decoupled from the writer prompts. After each writer invocation, the reviewer evaluates the output against hard-coded resume standards. If the output fails, the reviewer's `revision_instruction` is appended to the writer's next invocation as a new message. This repeats up to **2 retries** (3 total writer calls). After 2 retries, the last result is used regardless and a warning is logged.

### Flow

```
writer(inputs)
  → reviewer(content, section_type, previous_feedback="None")
  → passed?  YES → return result
             NO  → writer(inputs + <Revision Required> message)
                    → reviewer(content, section_type, previous_feedback=issues)
                    → passed?  YES → return result
                               NO  → writer(inputs + <Revision Required> message)
                                      → return result (log warning)
```

This flow applies to:
- Each individual highlight in `_rewrite_experience_async`
- Each individual highlight in `_rewrite_project_async`
- The full summary text in `update_summary`

---

## Components

### 1. `prompts/reviewer.yaml` (new)

A new prompt file defining the reviewer's behavior. The reviewer:
- Receives `section_type`, `content`, and `previous_feedback`
- Applies hard-coded standards per section type
- Never rewrites content — only judges and provides revision instructions
- Outputs structured JSON via `ReviewerOutput`

```yaml
messages:
  - role: system
    content: "You are a strict resume quality reviewer. Your only job is to check whether the provided resume content meets the given standards. You do not rewrite content — you only judge and give precise revision instructions."
  - role: human
    content: |-
      <Section Type>
      {section_type}

      <Content to Review>
      {content}

      <Previous Reviewer Feedback> (if any)
      {previous_feedback}
  - role: human
    content: |-
      <Standards>
      For highlight:
      - Must be exactly 1 sentence
      - Must be 25 words or fewer
      - Must start with an action verb
      - Should contain a quantifiable metric (number or percentage); if source resume lacks data, this is acceptable — set passed=true but note it in issues

      For summary:
      - Must be 50–80 words total
      - Must contain 3–4 sentences
      - Must not use first-person pronoun "I"
  - role: human
    content: |-
      <Instruction>
      Check whether <Content to Review> meets ALL applicable <Standards> for the given <Section Type>.
      If <Previous Reviewer Feedback> is provided, also verify whether those issues have been addressed.
      Output your judgment as JSON only, following this schema:
      {format_instructions}
```

### 2. `chains/reviewer.py` (new)

```python
def build_reviewer_chain(llm: BaseChatModel) -> Runnable:
    """
    Build the reviewer LCEL chain.
    Inputs: section_type, content, previous_feedback
    Output: ReviewerOutput (passed, issues, revision_instruction)
    """
```

### 3. `prompts.py` — new Pydantic model (addition)

```python
class ReviewerOutput(BaseModel):
    passed: bool
    issues: List[str]
    revision_instruction: str
```

### 4. `pipeline.py` — retry loop (modification)

A shared async helper `_review_and_retry` encapsulates the retry logic to avoid duplication across `_rewrite_experience_async`, `_rewrite_project_async`, and `update_summary`:

```python
async def _review_and_retry(
    self,
    writer_chain,
    reviewer_chain,
    inputs: dict,
    extract_content: Callable,   # pulls the reviewable text from writer output
    section_type: str,
    max_retries: int = 2,
) -> Any:
    """
    Run writer → reviewer → retry loop.
    Returns the last writer result regardless of final review status.
    """
```

The `<Revision Required>` message is appended dynamically to the prompt via LangChain's message list — the existing YAML prompt files are not modified for this purpose.

### 5. Prompt criteria updates (modification)

Two existing YAML prompts need their length criteria corrected to align with the new standard. These changes make the writer prompt consistent with what the reviewer enforces, reducing the number of retries needed in practice.

**`prompts/section_highlighter.yaml`** — update `<Criteria>`:
- `"Each highlight must exceed 50 words, and include 2 - 3 sentence."` →  
  `"Each highlight must be exactly 1 sentence and 25 words or fewer."`

**`prompts/summary_writer.yaml`** — update `<Criteria>`:
- `"The summary should be concise, comprising 3–4 sentences totaling 100–200 words."` →  
  `"The summary must be concise, comprising 3–4 sentences totaling 50–80 words. Do not use first-person pronoun 'I'."`

---

## What Does NOT Change

- `improver.py` / `improver.yaml` — the improver chain is left as-is; its critique output remains informational
- MongoDB prompt storage and `prompt_loader.py` — reviewer prompt is loaded via the same `load_prompt()` mechanism (DB-first, YAML fallback)
- Frontend `defaultPrompts.js` — reviewer is a backend-internal chain, not user-editable
- All existing chain interfaces (`build_section_highlighter_chain`, etc.) — signatures unchanged
- `seed_prompts.py` — reviewer prompt added to the seed list so it is inserted into MongoDB on first run

---

## File Change Summary

| File | Change |
|---|---|
| `prompts/reviewer.yaml` | **New** |
| `chains/reviewer.py` | **New** |
| `prompts.py` | **Add** `ReviewerOutput` model |
| `pipeline.py` | **Modify** `_rewrite_experience_async`, `_rewrite_project_async`, `update_summary`; **add** `_review_and_retry` helper |
| `prompts/section_highlighter.yaml` | **Modify** highlight length criteria |
| `prompts/summary_writer.yaml` | **Modify** summary length + no first-person criteria |
| `llm/seed_prompts.py` | **Modify** add reviewer to seed list |

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Reviewer miscalibrated (too strict, always fails) | Hard cap of 2 retries; fallback to last result with warning log |
| Extra LLM cost | Retry only triggered on failure; reviewer can use a cheaper/faster model than writer |
| Reviewer tries to rewrite content | System prompt explicitly prohibits rewriting; output schema has no `rewritten_content` field |
| `previous_feedback` empty on first call | Always passed as string `"None"` — never null/empty |

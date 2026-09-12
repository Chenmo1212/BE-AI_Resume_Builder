# Reviewer Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan. Before dispatching subagents, analyze tasks for parallelism and group into batches. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an independent reviewer chain with retry loop that enforces North American resume standards (highlight ≤25 words/1 sentence, summary 50–80 words/3–4 sentences/no "I") after each writer invocation.

**Architecture:** A new `reviewer` chain evaluates writer output against hard-coded standards stored in its own `prompts/reviewer.yaml`. If the output fails, the reviewer's `revision_instruction` is appended as a new message to the writer's next call. A shared async helper `_review_and_retry` in `pipeline.py` encapsulates this loop (max 2 retries) and is called from `_rewrite_experience_async`, `_rewrite_project_async`, and `update_summary`.

**Tech Stack:** Python 3.11+, LangChain Core, Pydantic v2, PyYAML, pytest + unittest.mock

**Spec:** `docs/superpowers/specs/2025-01-27-reviewer-chain-design.md`

## Global Constraints

- All new code follows existing patterns: LCEL chain (`prompt | llm | parser`), `load_prompt()` for YAML loading, `PydanticOutputParser` for structured output
- `previous_feedback` is always passed as a string — never `None` or empty; default value is the string `"None"`
- Reviewer prompt is seeded with `is_show: False` so it is not exposed to the frontend
- Max retries hard-capped at 2 (3 total writer calls per section)
- After 2 retries, last result is used regardless; a `logger.warning` is emitted
- The reviewer chain is backend-internal and must NOT appear in `defaultPrompts.js`
- Existing chain interfaces (`build_section_highlighter_chain`, etc.) signatures are unchanged

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `prompts/reviewer.yaml` | **Create** | Reviewer prompt: standards, judgment instruction, format schema |
| `chains/reviewer.py` | **Create** | `build_reviewer_chain(llm)` → Runnable expecting `section_type`, `content`, `previous_feedback` |
| `prompts.py` | **Modify** | Add `ReviewerOutput(passed, issues, revision_instruction)` Pydantic model |
| `pipeline.py` | **Modify** | Add `_review_and_retry` helper; wire into `_rewrite_experience_async`, `_rewrite_project_async`, `update_summary` |
| `prompts/section_highlighter.yaml` | **Modify** | Update highlight length criteria: 50+ words/2-3 sentences → ≤25 words/1 sentence |
| `prompts/summary_writer.yaml` | **Modify** | Update summary length criteria: 100–200 words → 50–80 words; add no first-person "I" rule |
| `llm/seed_prompts.py` | **Modify** | Add reviewer to seed list with `is_show: False` |
| `tests/test_chains.py` | **Modify** | Add `test_build_reviewer_chain_returns_runnable` |
| `tests/test_reviewer.py` | **Create** | Unit tests for `ReviewerOutput` model and `_review_and_retry` retry logic |

---

### Task 1: Add `ReviewerOutput` Pydantic model to `prompts.py`

**Files:**
- Modify: `prompts.py`
- Test: `tests/test_reviewer.py` (create)

**Interfaces:**
- Produces: `ReviewerOutput` — imported by `chains/reviewer.py` (Task 2) and `pipeline.py` (Task 4)

---

- [ ] **Step 1: Write the failing test**

Create `tests/test_reviewer.py`:

```python
import pytest
from pydantic import ValidationError


def test_reviewer_output_passed_true():
    from prompts import ReviewerOutput
    r = ReviewerOutput(passed=True, issues=[], revision_instruction="")
    assert r.passed is True
    assert r.issues == []
    assert r.revision_instruction == ""


def test_reviewer_output_passed_false_with_issues():
    from prompts import ReviewerOutput
    r = ReviewerOutput(
        passed=False,
        issues=["Highlight exceeds 25 words (actual: 38)"],
        revision_instruction="Shorten to one concise sentence under 25 words starting with an action verb.",
    )
    assert r.passed is False
    assert len(r.issues) == 1
    assert "25 words" in r.issues[0]


def test_reviewer_output_missing_field_raises():
    from prompts import ReviewerOutput
    with pytest.raises(ValidationError):
        ReviewerOutput(passed=True)  # missing issues and revision_instruction
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd BE-AI_Resume_Builder && source .venv/bin/activate && pytest tests/test_reviewer.py -v
```

Expected: `ImportError` or `AttributeError` — `ReviewerOutput` not yet defined.

- [ ] **Step 3: Add `ReviewerOutput` to `prompts.py`**

Add after the `Resume_Improver_Output` class (after line 169):

```python
class ReviewerOutput(BaseModel):
    """Quality review result for a single resume section."""

    passed: bool = Field(
        ..., description="True if the content meets all applicable resume standards"
    )
    issues: List[str] = Field(
        ...,
        description="List of specific issues found. Empty list if passed=True.",
    )
    revision_instruction: str = Field(
        ...,
        description=(
            "Precise instruction for the writer to fix all issues. "
            "Empty string if passed=True."
        ),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd BE-AI_Resume_Builder && source .venv/bin/activate && pytest tests/test_reviewer.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd BE-AI_Resume_Builder && git add prompts.py tests/test_reviewer.py && git commit -m "feat: add ReviewerOutput pydantic model"
```

---

### Task 2: Create `prompts/reviewer.yaml` and `chains/reviewer.py`

**Files:**
- Create: `prompts/reviewer.yaml`
- Create: `chains/reviewer.py`
- Modify: `tests/test_chains.py`

**Interfaces:**
- Consumes: `ReviewerOutput` from `prompts.py` (Task 1)
- Produces: `build_reviewer_chain(llm: BaseChatModel) -> Runnable` — expects keys `section_type`, `content`, `previous_feedback`; returns `ReviewerOutput`

---

- [ ] **Step 1: Write the failing test**

Add to `tests/test_chains.py`:

```python
def test_build_reviewer_chain_returns_runnable():
    from chains.reviewer import build_reviewer_chain
    mock_llm = make_mock_llm()
    chain = build_reviewer_chain(mock_llm)
    assert chain is not None


def test_reviewer_chain_invokes_with_correct_keys():
    """Reviewer chain must accept section_type, content, previous_feedback."""
    try:
        from langchain_core.language_models.fake_chat_models import FakeListChatModel
    except ImportError:
        from langchain_core.language_models.fake import FakeListChatModel
    from chains.reviewer import build_reviewer_chain
    fake_response = '{"passed": true, "issues": [], "revision_instruction": ""}'
    llm = FakeListChatModel(responses=[fake_response])
    chain = build_reviewer_chain(llm)
    result = chain.invoke({
        "section_type": "highlight",
        "content": "Led backend development reducing latency by 40%.",
        "previous_feedback": "None",
    })
    assert result is not None
    assert result.passed is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd BE-AI_Resume_Builder && source .venv/bin/activate && pytest tests/test_chains.py::test_build_reviewer_chain_returns_runnable tests/test_chains.py::test_reviewer_chain_invokes_with_correct_keys -v
```

Expected: `ImportError` — `chains/reviewer.py` does not exist yet.

- [ ] **Step 3: Create `prompts/reviewer.yaml`**

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
      If <Previous Reviewer Feedback> is provided and is not "None", also verify whether those issues have been addressed.
      Output your judgment as JSON only, following this schema:
      {format_instructions}
```

- [ ] **Step 4: Create `chains/reviewer.py`**

```python
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.language_models import BaseChatModel
from llm.prompt_loader import load_prompt
from prompts import ReviewerOutput


def build_reviewer_chain(llm: BaseChatModel) -> Runnable:
    """
    Build the reviewer LCEL chain.

    Evaluates resume content against hard-coded North American resume standards.
    Never rewrites content — only judges and provides revision instructions.

    Args:
        llm: A LangChain BaseChatModel instance.

    Returns:
        A LangChain Runnable expecting keys:
        section_type ("highlight" or "summary"), content, previous_feedback
    """
    parser = PydanticOutputParser(pydantic_object=ReviewerOutput)
    prompt = load_prompt("reviewer").partial(
        format_instructions=parser.get_format_instructions()
    )
    return prompt | llm | parser
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd BE-AI_Resume_Builder && source .venv/bin/activate && pytest tests/test_chains.py -v
```

Expected: all chain tests PASS including the two new reviewer tests.

- [ ] **Step 6: Commit**

```bash
cd BE-AI_Resume_Builder && git add prompts/reviewer.yaml chains/reviewer.py tests/test_chains.py && git commit -m "feat: add reviewer chain and prompt"
```

---

### Task 3: Update `prompts/section_highlighter.yaml` and `prompts/summary_writer.yaml`

**Files:**
- Modify: `prompts/section_highlighter.yaml`
- Modify: `prompts/summary_writer.yaml`

**Interfaces:**
- No interface changes — these are YAML prompt files, not Python modules.

---

- [ ] **Step 1: Update `prompts/section_highlighter.yaml` highlight length criteria**

Find and replace this line in `<Criteria>`:
```
      - Each highlight must exceed 50 words, and include 2 - 3 sentence.
```
Replace with:
```
      - Each highlight must be exactly 1 sentence and 25 words or fewer.
```

- [ ] **Step 2: Update `prompts/summary_writer.yaml` summary length and first-person criteria**

Find and replace this line in `<Criteria>`:
```
      - The summary should be concise, comprising 3–4 sentences totaling 100–200 words.
```
Replace with:
```
      - The summary must be concise, comprising 3–4 sentences totaling 50–80 words. Do not use the first-person pronoun "I".
```

- [ ] **Step 3: Verify YAML files are valid**

```bash
cd BE-AI_Resume_Builder && source .venv/bin/activate && python -c "
import yaml
for f in ['prompts/section_highlighter.yaml', 'prompts/summary_writer.yaml']:
    with open(f) as fh:
        yaml.safe_load(fh)
    print(f'OK: {f}')
"
```

Expected: `OK: prompts/section_highlighter.yaml` and `OK: prompts/summary_writer.yaml`

- [ ] **Step 4: Run full test suite to confirm no regressions**

```bash
cd BE-AI_Resume_Builder && source .venv/bin/activate && pytest tests/ -v
```

Expected: all existing tests PASS.

- [ ] **Step 5: Commit**

```bash
cd BE-AI_Resume_Builder && git add prompts/section_highlighter.yaml prompts/summary_writer.yaml && git commit -m "fix: tighten highlight and summary length criteria to NA resume standards"
```

---

### Task 4: Add `_review_and_retry` helper and wire into `pipeline.py`

**Files:**
- Modify: `pipeline.py`
- Modify: `tests/test_reviewer.py`

**Interfaces:**
- Consumes:
  - `build_reviewer_chain(llm)` from `chains/reviewer.py` (Task 2) — returns `ReviewerOutput`
  - `ReviewerOutput` fields: `passed: bool`, `issues: List[str]`, `revision_instruction: str`
- Produces: `_review_and_retry(self, writer_chain, reviewer_chain, inputs, extract_content, section_type, max_retries=2)` — returns the writer's result object (same type as `writer_chain.ainvoke(inputs)`)

---

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_reviewer.py`:

```python
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


def make_pipeline_stub():
    """Return a minimal Pipeline-like object for testing _review_and_retry."""
    from pipeline import Pipeline
    p = Pipeline.__new__(Pipeline)
    p.ai_config = {}
    return p


def test_review_and_retry_passes_on_first_try():
    """If reviewer passes immediately, writer is called only once."""
    from prompts import ReviewerOutput

    writer_chain = MagicMock()
    writer_result = MagicMock()
    writer_result.final_answer = "Reduced latency by 40% via caching."
    writer_chain.ainvoke = AsyncMock(return_value=writer_result)

    reviewer_chain = MagicMock()
    reviewer_chain.ainvoke = AsyncMock(
        return_value=ReviewerOutput(passed=True, issues=[], revision_instruction="")
    )

    p = make_pipeline_stub()

    result = asyncio.run(p._review_and_retry(
        writer_chain=writer_chain,
        reviewer_chain=reviewer_chain,
        inputs={"section": "Built APIs"},
        extract_content=lambda r: r.final_answer,
        section_type="highlight",
    ))

    assert result is writer_result
    assert writer_chain.ainvoke.call_count == 1
    assert reviewer_chain.ainvoke.call_count == 1


def test_review_and_retry_retries_on_failure_then_passes():
    """Writer is called twice when reviewer fails once then passes."""
    from prompts import ReviewerOutput

    writer_chain = MagicMock()
    writer_result_1 = MagicMock()
    writer_result_1.final_answer = "This is a very long sentence that exceeds the twenty five word limit by quite a lot."
    writer_result_2 = MagicMock()
    writer_result_2.final_answer = "Reduced API latency by 40% via Redis caching."
    writer_chain.ainvoke = AsyncMock(side_effect=[writer_result_1, writer_result_2])

    reviewer_chain = MagicMock()
    reviewer_chain.ainvoke = AsyncMock(side_effect=[
        ReviewerOutput(
            passed=False,
            issues=["Highlight exceeds 25 words"],
            revision_instruction="Shorten to one sentence under 25 words.",
        ),
        ReviewerOutput(passed=True, issues=[], revision_instruction=""),
    ])

    p = make_pipeline_stub()

    result = asyncio.run(p._review_and_retry(
        writer_chain=writer_chain,
        reviewer_chain=reviewer_chain,
        inputs={"section": "Built APIs"},
        extract_content=lambda r: r.final_answer,
        section_type="highlight",
    ))

    assert result is writer_result_2
    assert writer_chain.ainvoke.call_count == 2
    assert reviewer_chain.ainvoke.call_count == 2


def test_review_and_retry_returns_last_result_after_max_retries(caplog):
    """After max_retries=2 failures, last result is returned and a warning is logged."""
    import logging
    from prompts import ReviewerOutput

    writer_chain = MagicMock()
    writer_results = [MagicMock(), MagicMock(), MagicMock()]
    for i, r in enumerate(writer_results):
        r.final_answer = f"result_{i}"
    writer_chain.ainvoke = AsyncMock(side_effect=writer_results)

    reviewer_chain = MagicMock()
    reviewer_chain.ainvoke = AsyncMock(return_value=ReviewerOutput(
        passed=False,
        issues=["Still too long"],
        revision_instruction="Make it shorter.",
    ))

    p = make_pipeline_stub()

    with caplog.at_level(logging.WARNING):
        result = asyncio.run(p._review_and_retry(
            writer_chain=writer_chain,
            reviewer_chain=reviewer_chain,
            inputs={"section": "Built APIs"},
            extract_content=lambda r: r.final_answer,
            section_type="highlight",
            max_retries=2,
        ))

    assert result is writer_results[2]
    assert writer_chain.ainvoke.call_count == 3
    assert any("reviewer" in record.message.lower() or "retry" in record.message.lower()
               for record in caplog.records)


def test_review_and_retry_appends_revision_message_on_retry():
    """On retry, inputs must contain the revision instruction from the reviewer."""
    from prompts import ReviewerOutput

    captured_inputs = []

    async def capture_ainvoke(inputs):
        captured_inputs.append(dict(inputs))
        r = MagicMock()
        r.final_answer = "result"
        return r

    writer_chain = MagicMock()
    writer_chain.ainvoke = AsyncMock(side_effect=capture_ainvoke)

    reviewer_chain = MagicMock()
    reviewer_chain.ainvoke = AsyncMock(side_effect=[
        ReviewerOutput(
            passed=False,
            issues=["Too long"],
            revision_instruction="Shorten to under 25 words.",
        ),
        ReviewerOutput(passed=True, issues=[], revision_instruction=""),
    ])

    p = make_pipeline_stub()

    asyncio.run(p._review_and_retry(
        writer_chain=writer_chain,
        reviewer_chain=reviewer_chain,
        inputs={"section": "Built APIs"},
        extract_content=lambda r: r.final_answer,
        section_type="highlight",
    ))

    # First call has no revision key; second call has revision_instruction key
    assert "revision_instruction" not in captured_inputs[0]
    assert captured_inputs[1].get("revision_instruction") == "Shorten to under 25 words."
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd BE-AI_Resume_Builder && source .venv/bin/activate && pytest tests/test_reviewer.py -v -k "retry"
```

Expected: `AttributeError` — `Pipeline` has no `_review_and_retry`.

- [ ] **Step 3: Add imports and `_review_and_retry` to `pipeline.py`**

Add these imports at the top of `pipeline.py` (after the existing chain imports):

```python
from chains.reviewer import build_reviewer_chain
from prompts import ReviewerOutput
```

Add `_review_and_retry` as a new method on `Pipeline`, after `_extract_skills_async` and before `_run_parallel_steps`:

```python
async def _review_and_retry(
    self,
    writer_chain,
    reviewer_chain,
    inputs: dict,
    extract_content,
    section_type: str,
    max_retries: int = 2,
):
    """
    Run writer → reviewer → retry loop.

    Args:
        writer_chain: Async-invokable LangChain chain producing resume content.
        reviewer_chain: Async-invokable reviewer chain returning ReviewerOutput.
        inputs: Initial input dict for the writer chain.
        extract_content: Callable that extracts the reviewable text from the writer result.
        section_type: "highlight" or "summary" — passed to the reviewer.
        max_retries: Maximum number of retry attempts after the first failure (default 2).

    Returns:
        The last writer result, regardless of final review status.
    """
    current_inputs = dict(inputs)
    previous_feedback = "None"

    for attempt in range(max_retries + 1):
        result = await writer_chain.ainvoke(current_inputs)
        content = extract_content(result)

        review: ReviewerOutput = await reviewer_chain.ainvoke({
            "section_type": section_type,
            "content": content,
            "previous_feedback": previous_feedback,
        })

        if review.passed:
            return result

        if attempt == max_retries:
            logger.warning(
                "Reviewer still failing after %d retries for section_type='%s'. "
                "Using last result. Issues: %s",
                max_retries,
                section_type,
                review.issues,
            )
            return result

        # Prepare retry: append revision instruction to inputs
        previous_feedback = "; ".join(review.issues)
        current_inputs = dict(inputs)
        current_inputs["revision_instruction"] = review.revision_instruction

    return result  # unreachable but satisfies type checkers
```

- [ ] **Step 4: Run the retry tests to verify they pass**

```bash
cd BE-AI_Resume_Builder && source .venv/bin/activate && pytest tests/test_reviewer.py -v
```

Expected: all 7 tests in `test_reviewer.py` PASS.

- [ ] **Step 5: Commit**

```bash
cd BE-AI_Resume_Builder && git add pipeline.py tests/test_reviewer.py && git commit -m "feat: add _review_and_retry helper to pipeline"
```

---

### Task 5: Wire `_review_and_retry` into experience, project, and summary methods

**Files:**
- Modify: `pipeline.py`
- Modify: `tests/test_reviewer.py`

**Interfaces:**
- Consumes: `_review_and_retry(self, writer_chain, reviewer_chain, inputs, extract_content, section_type, max_retries=2)` (Task 4)
- Consumes: `build_reviewer_chain(llm)` (Task 2)
- Consumes: `build_section_highlighter_chain(llm)` — unchanged signature
- Consumes: `build_summary_writer_chain(llm)` — unchanged signature

---

- [ ] **Step 1: Write the failing integration tests**

Add to `tests/test_reviewer.py`:

```python
def test_rewrite_experience_uses_review_and_retry():
    """_rewrite_experience_async must call _review_and_retry, not writer directly."""
    from pipeline import Pipeline

    p = Pipeline.__new__(Pipeline)
    p.ai_config = {}
    p.parsed_job = {
        "duties": ["Build APIs"],
        "qualifications": ["5 years Python"],
        "technical_skills": ["Python"],
        "non_technical_skills": ["Communication"],
    }

    exp_raw = {"name": "Acme", "unedited": True, "summary": "Led API development team."}

    expected_result = MagicMock()
    expected_result.final_answer = [MagicMock(highlight="Led API dev.", relevance=5)]

    review_and_retry_mock = AsyncMock(return_value=expected_result)

    with patch.object(p, '_review_and_retry', review_and_retry_mock), \
         patch.object(p, '_get_llm', return_value=MagicMock()):
        result = asyncio.run(p._rewrite_experience_async(exp_raw))

    review_and_retry_mock.assert_called_once()
    call_kwargs = review_and_retry_mock.call_args
    assert call_kwargs.kwargs.get("section_type") == "highlight" or \
           (len(call_kwargs.args) >= 5 and call_kwargs.args[4] == "highlight")


def test_update_summary_uses_review_and_retry():
    """update_summary must call _review_and_retry for the summary section."""
    from pipeline import Pipeline

    p = Pipeline.__new__(Pipeline)
    p.ai_config = {}
    p.parsed_job = {
        "company": "Acme Corp",
        "job_summary": "Build software",
        "technical_skills": ["Python"],
        "non_technical_skills": ["Communication"],
    }
    p.resume_builder = {
        "summary": "",
        "summary_raw": "Experienced engineer.",
        "experiences": [],
        "projects": [],
        "skills": [],
        "education": [],
    }

    expected_result = MagicMock()
    expected_result.final_answer = "Experienced software engineer with 5 years building scalable APIs."

    review_and_retry_mock = AsyncMock(return_value=expected_result)

    with patch.object(p, '_review_and_retry', review_and_retry_mock), \
         patch.object(p, '_get_llm', return_value=MagicMock()), \
         patch.object(p, '_get_degrees', return_value=[]), \
         patch.object(p, '_format_projects_for_prompt', return_value=[]), \
         patch.object(p, '_format_experiences_for_prompt', return_value=[]), \
         patch.object(p, '_format_skills_for_prompt', return_value=[]):
        p.update_summary()

    review_and_retry_mock.assert_called_once()
    call_kwargs = review_and_retry_mock.call_args
    assert call_kwargs.kwargs.get("section_type") == "summary" or \
           (len(call_kwargs.args) >= 5 and call_kwargs.args[4] == "summary")
    assert p.resume_builder["summary"] == expected_result.final_answer
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd BE-AI_Resume_Builder && source .venv/bin/activate && pytest tests/test_reviewer.py::test_rewrite_experience_uses_review_and_retry tests/test_reviewer.py::test_update_summary_uses_review_and_retry -v
```

Expected: FAIL — `_rewrite_experience_async` and `update_summary` do not call `_review_and_retry` yet.

- [ ] **Step 3: Modify `_rewrite_experience_async` in `pipeline.py`**

Replace the body of `_rewrite_experience_async` (currently ~lines 228–243):

```python
async def _rewrite_experience_async(self, exp_raw: dict) -> dict:
    exp = dict(exp_raw)
    experience_unedited = exp.get("summary") if exp.get("unedited", False) else ""
    if experience_unedited:
        writer_chain = build_section_highlighter_chain(self._get_llm())
        reviewer_chain = build_reviewer_chain(self._get_llm())
        inputs = {
            **format_prompt_inputs_as_strings(
                prompt_inputs=["duties", "qualifications", "technical_skills", "non_technical_skills"],
                **self.parsed_job,
            ),
            "section": experience_unedited,
        }
        result = await self._review_and_retry(
            writer_chain=writer_chain,
            reviewer_chain=reviewer_chain,
            inputs=inputs,
            extract_content=lambda r: r.final_answer[0].highlight if r.final_answer else "",
            section_type="highlight",
        )
        highlights = sorted(result.final_answer, key=lambda d: d.relevance * -1)
        exp["highlights"] = [h.highlight for h in highlights]
    return exp
```

- [ ] **Step 4: Modify `_rewrite_project_async` in `pipeline.py`**

Replace the body of `_rewrite_project_async` (currently ~lines 245–261):

```python
async def _rewrite_project_async(self, proj_raw: dict) -> dict:
    proj = dict(proj_raw) if isinstance(proj_raw, dict) else proj_raw
    proj_unedited = proj.get("summary") if proj.get("unedited", False) else ""
    if proj_unedited:
        desc_combined = proj_unedited + " using " + proj.get("skills", "")
        writer_chain = build_section_highlighter_chain(self._get_llm())
        reviewer_chain = build_reviewer_chain(self._get_llm())
        inputs = {
            **format_prompt_inputs_as_strings(
                prompt_inputs=["duties", "qualifications", "technical_skills", "non_technical_skills"],
                **self.parsed_job,
            ),
            "section": desc_combined,
        }
        result = await self._review_and_retry(
            writer_chain=writer_chain,
            reviewer_chain=reviewer_chain,
            inputs=inputs,
            extract_content=lambda r: r.final_answer[0].highlight if r.final_answer else "",
            section_type="highlight",
        )
        highlights = sorted(result.final_answer, key=lambda d: d.relevance * -1)
        proj["highlights"] = [h.highlight for h in highlights]
    return proj
```

- [ ] **Step 5: Modify `update_summary` in `pipeline.py`**

Replace the body of `update_summary` (currently ~lines 343–361):

```python
def update_summary(self):
    logger.info("=========== Start updating summary ===========")
    if not self.resume_builder:
        self.read_resume()
    if "summary" not in self._active_sections():
        logger.info("Summary section skipped (not in ai_config.sections)")
        self.resume_builder["summary"] = self.resume_builder.get("summary_raw", "")
        return
    writer_chain = build_summary_writer_chain(self._get_llm())
    reviewer_chain = build_reviewer_chain(self._get_llm())
    inputs = format_prompt_inputs_as_strings(
        prompt_inputs=["company", "job_summary", "degrees", "projects", "experiences", "skills"],
        **self.parsed_job,
        degrees=self._get_degrees(),
        projects=self._format_projects_for_prompt(self.resume_builder["projects"]),
        experiences=self._format_experiences_for_prompt(self.resume_builder["experiences"]),
        skills=self._format_skills_for_prompt(self.resume_builder["skills"]),
    )
    result = asyncio.run(self._review_and_retry(
        writer_chain=writer_chain,
        reviewer_chain=reviewer_chain,
        inputs=inputs,
        extract_content=lambda r: r.final_answer,
        section_type="summary",
    ))
    self.resume_builder["summary"] = result.final_answer
```

- [ ] **Step 6: Run all reviewer tests to verify they pass**

```bash
cd BE-AI_Resume_Builder && source .venv/bin/activate && pytest tests/test_reviewer.py -v
```

Expected: all tests in `test_reviewer.py` PASS.

- [ ] **Step 7: Run full test suite to confirm no regressions**

```bash
cd BE-AI_Resume_Builder && source .venv/bin/activate && pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
cd BE-AI_Resume_Builder && git add pipeline.py tests/test_reviewer.py && git commit -m "feat: wire reviewer retry loop into experience, project, and summary generation"
```

---

### Task 6: Update `seed_prompts.py` to include reviewer

**Files:**
- Modify: `llm/seed_prompts.py`
- Modify: `tests/test_seed_prompts.py`

**Interfaces:**
- No interface changes — `seed_prompt_templates()` signature is unchanged.

---

- [ ] **Step 1: Write the failing test**

Read `tests/test_seed_prompts.py` first to understand its pattern, then add:

```python
def test_seed_includes_reviewer_with_is_show_false(tmp_path, monkeypatch):
    """Seeded reviewer document must have is_show=False."""
    import mongomock
    from llm.seed_prompts import seed_prompt_templates

    client = mongomock.MongoClient()
    monkeypatch.setattr("llm.seed_prompts.MongoClient", lambda uri, **kw: client)

    uri = "mongodb://localhost:27017/testdb"
    count = seed_prompt_templates(mongo_uri=uri)

    collection = client["testdb"]["prompt_templates"]
    docs = {d["name"]: d for d in collection.find()}

    assert "reviewer" in docs, "reviewer must be seeded"
    assert docs["reviewer"]["is_show"] is False, "reviewer must have is_show=False"
    assert docs["section_highlighter"]["is_show"] is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd BE-AI_Resume_Builder && source .venv/bin/activate && pytest tests/test_seed_prompts.py::test_seed_includes_reviewer_with_is_show_false -v
```

Expected: FAIL — reviewer not in seeded docs, or test not found.

- [ ] **Step 3: Update `llm/seed_prompts.py`**

Add `"reviewer"` to `_YAML_NAMES` and its description to `_DESCRIPTIONS`, and track which prompts need `is_show: False`:

```python
_DESCRIPTIONS = {
    "section_highlighter": "Highlights resume sections matching the job posting",
    "skills_matcher": "Extracts skills from resume matching job requirements",
    "summary_writer": "Writes a professional summary tailored to the job",
    "improver": "Critiques the resume and suggests improvements",
    "reviewer": "Internal quality reviewer — not user-editable",
}

_YAML_NAMES = ["section_highlighter", "skills_matcher", "summary_writer", "improver", "reviewer"]

# Prompts that should not be shown in the frontend prompt editor
_HIDDEN_PROMPTS = {"reviewer"}
```

Then in the `seed_prompt_templates` function, update the doc construction to use `_HIDDEN_PROMPTS`:

```python
docs.append({
    "name": name,
    "description": _DESCRIPTIONS.get(name, ""),
    "version": 1,
    "messages": data["messages"],
    "create_time": now,
    "update_time": now,
    "delete_time": None,
    "is_delete": False,
    "is_show": name not in _HIDDEN_PROMPTS,
})
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd BE-AI_Resume_Builder && source .venv/bin/activate && pytest tests/test_seed_prompts.py -v
```

Expected: all seed tests PASS including the new one.

- [ ] **Step 5: Run full test suite one final time**

```bash
cd BE-AI_Resume_Builder && source .venv/bin/activate && pytest tests/ -v
```

Expected: all tests PASS with no warnings.

- [ ] **Step 6: Commit**

```bash
cd BE-AI_Resume_Builder && git add llm/seed_prompts.py tests/test_seed_prompts.py && git commit -m "feat: seed reviewer prompt with is_show=False"
```

---

## Self-Review

**Spec coverage:**
- ✅ `ReviewerOutput(passed, issues, revision_instruction)` — Task 1
- ✅ `prompts/reviewer.yaml` with hard-coded standards — Task 2
- ✅ `build_reviewer_chain(llm)` — Task 2
- ✅ Retry loop max 2, fallback with warning — Task 4
- ✅ `revision_instruction` appended as new input key on retry — Task 4
- ✅ `_rewrite_experience_async` wired — Task 5
- ✅ `_rewrite_project_async` wired — Task 5
- ✅ `update_summary` wired — Task 5
- ✅ `section_highlighter.yaml` criteria updated — Task 3
- ✅ `summary_writer.yaml` criteria updated — Task 3
- ✅ `seed_prompts.py` reviewer added with `is_show: False` — Task 6
- ✅ `previous_feedback` defaults to string `"None"` — Task 4 implementation

**Type consistency:**
- `ReviewerOutput` defined in Task 1, imported in Tasks 2 and 4 — consistent
- `build_reviewer_chain` defined in Task 2, imported and used in Tasks 5 — consistent
- `_review_and_retry` defined in Task 4, called in Task 5 with matching kwargs

**Placeholder scan:** No TBD/TODO in any task. All code blocks are complete.

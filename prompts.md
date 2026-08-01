# Prompt Log — The Closer (cold-email-sender)

This file records every prompt/instruction given to me (the coding assistant) for this
project, along with what was done in response. It exists so the process is fully
traceable. New prompts should be appended at the bottom.

Format per entry:

```text
## [<ID>] <date> — <short title>
**Prompt (verbatim or faithful summary):**
<the user's instruction>

**Work done:**
<what I implemented/changed>

**Status:** <done / in progress / blocked>
```

---

## Session context (before this log was created)

The project is "The Closer" — a cold-email writer + send bot (job-seeker outreach).
State carried in from earlier sessions (fixes already verified against the live Groq
key, full test suite green):

- Fixed 9 original bugs + 2 discovered hardenings in:
  - `src/closer/generation/generator.py` — provider-scoped API keys, JD-inference
    not overriding explicit values, `re.DOTALL` body parsing, provider quality guard
    (no unresolved placeholders, company/role must appear in body, word-limit),
    `candidate_name` in the prompt, deterministic resume/JD summary fallback.
  - `src/closer/input/loader.py`, `src/closer/config/settings.py`,
    `src/closer/ui/app.py`, `src/closer/outreach/workflow.py`, guardrails.
- Live-testing loop: verify real output against real JDs with the live Groq key.
- Latest live test (Office Manager JD) exposed inference garbage like
  `"Unknown (cannot be inferred from the given job description)"` leaking into the
  email; fixed with `_is_helpful_inference` / `_is_plausible_company` / `_is_plausible_role`
  guards, role-like-word rejection in `_extract_company`, JD label stripping in
  `_first_sentence`, and placeholder-aware `_provider_output_is_usable`.

---

## [1] 2026-08-01 — Session context recap
**Prompt:**
> What did we do so far?

**Work done:**
Provided a recap of the project objective, completed bug fixes, and the active/blocked
work (Office Manager JD live test). Then continued the debugging: fixed the garbage
company-inference leak (two refusal variants), `_extract_company` picking up
"Office Management" as a company, `_first_sentence` including "Job Title:" labels,
and `_parse_provider_output` not unescaping literal `\n`. Added regression tests
(36 -> 39 passing). Verified live: Office Manager JD now infers
`Unknown Company / Office Manager` and Groq produces an accepted, honest email.

**Status:** done

---

## [2] 2026-08-01 — Product vision: JD-first flow + Google Sheets tracking
**Prompt (faithful, condensed from the full message):**
> The Streamlit app only shows 5 mock emails; I want a realistic flow. I provide the
> Job Description and Job ID/link, attach my resume (or use a markdown resume), link a
> Gemini API key, and the AI generates a personalized professional short subject+body.
> Then I attach the resume/docs and click Send / Draft / Skip — the decision is mine.
> Core idea: stop manually copying/pasting into ChatGPT and sending — save time.
> Also: every sent email must be stored in Google Sheets with
> Date & Time | recipient email | Subject Line | Job link | Status
> (received reply / not yet received reply).
> Tell me if this plan aligns with the project; refer to the .md docs.

**Work done:**
Reviewed `docs/problemStatement.md`, `docs/implementation-plan.md`, and the current
code. Verdict: fully aligned — the docs specify exactly this flow; the project is
~90% built. Identified 3 real gaps:
1. Mock contacts are the UI entry point and their company/role override JD inference
   (no "start from scratch" path).
2. No resume file upload (only the static `resume_background.md`).
3. Google Sheets rows are append-only; no reply-status updates (awaiting reply/replied).

**Status:** done (assessment delivered)

---

## [3] 2026-08-01 — Implement all three gaps + create prompts.md
**Prompt (answer to the "which gaps" question):**
> All three gaps. Make sure you do it all in a proper manner. Create a file
> `prompts.md` that stores the prompts given to me (the user) and track the process
> properly.

**Work done:**
1. Created this `prompts.md` log.
2. JD-first flow: added "New outreach (start from scratch)" to the UI picker; the
   form now starts blank and auto-infers company/role from the pasted job description
   (editable, not clobbering manual edits); signature defaults to the resume name.
3. Resume upload: added PDF/Markdown/TXT upload in the UI that feeds the AI prompt
   per application (falls back to `resume_background.md` when nothing is uploaded).
   Added `pypdf` to `requirements.txt` for PDF text extraction.
4. Reply-status tracking: added `update_outreach_status()` in
   `src/closer/tracking/sheets.py` (awaits `awaiting reply / replied / no reply`) and
   a "Track replies" panel in the UI.
5. Regression tests added and full suite run: **48 tests pass**. Live validation
   (`scripts/validate_mvp.py`) passes. Streamlit app verified with `AppTest`
   (renders with 0 exceptions; JD-first flow auto-infers role, signature defaults to
   "Rajendhar Are", resume upload updates the personalization summary, reply panel
   shows all statuses). Installed `pypdf` and `gspread` (now in `requirements.txt` /
   optional import).

**Status:** done

---

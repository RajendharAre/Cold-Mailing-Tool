# Phase Evaluation Rubric: The Closer

Use this document to **evaluate each implementation phase** when an AI (or human) builds the project. Pair with [implementation-plan.md](./implementation-plan.md), [architecture.md](./architecture.md), and [edge-case.md](./edge-case.md).

**How to use**

1. Complete the phase per the implementation plan.  
2. Run the **automated / manual checks** for that phase.  
3. Mark each criterion: **Pass** | **Fail** | **N/A**.  
4. Phase is **approved** only if all **Block** criteria pass and no **Critical anti-pattern** is present.  
5. Before starting the next phase, run **Regression gates** (bottom of doc).

**Scoring (optional)**

| Score | Meaning |
|-------|---------|
| 2 | Pass — meets criterion fully |
| 1 | Partial — works but missing polish documented as Warn |
| 0 | Fail — missing or incorrect |

Phase pass threshold: **≥90%** of applicable Block criteria at score 2, and **zero** Critical anti-patterns.

---

## Global Rules (All Phases)

### Critical anti-patterns (instant fail)

| ID | Anti-pattern |
|----|----------------|
| AP-01 | Real SMTP/API credentials committed to git |
| AP-02 | Email sent without user confirmation (FR3 bypass) |
| AP-03 | `DRY_RUN=false` as default in committed `.env.example` |
| AP-04 | Hardcoded passwords or API keys in source |
| AP-05 | Silent failure (no user message, no log row) on send/skip |
| AP-06 | Generator fabricates jobs, referrals, or meetings not in input |

### Global quality bar

- [ ] Python 3.10+ compatible syntax  
- [ ] Runnable from repo root: `python main.py` (or documented entry)  
- [ ] No unnecessary dependencies  
- [ ] Modules match architecture boundaries (no god-file >400 lines in MVP)  
- [ ] Errors are actionable in the terminal  

---

## Phase 0: Project Bootstrap

**Scope:** Repo layout, tooling, stubs, secrets hygiene.

### Block criteria

| ID | Criterion | Verify |
|----|-----------|--------|
| P0-01 | `requirements.txt` exists with `python-dotenv` | File present |
| P0-02 | `.gitignore` excludes `.env`, `__pycache__/`, venv | Inspect file |
| P0-03 | `.env.example` has all vars from problem statement §13 | Compare to spec |
| P0-04 | Phase packages exist under `src/closer/`: `cli`, `config`, `domain`, `input`, `generation`, `preview`, `delivery`, `audit` | Glob check |
| P0-05 | `python main.py` exits 0 | Run command |
| P0-06 | No real secrets in tracked files | `git grep` for password patterns |

### Warn criteria

| ID | Criterion |
|----|-----------|
| P0-W1 | `README.md` has install + run placeholder |
| P0-W2 | `docs/` links to architecture + implementation plan |

### Manual check

```bash
cd /path/to/the-closer
python main.py
echo $?   # expect 0
```

### Phase 0 verdict

| Pass | Fail |
|------|------|
| All P0 Block + no AP | Any Block fail or AP-01/04 |

---

## Phase 1: Domain Models & Configuration

**Scope:** `models.py`, `config.py`, env loading.

### Block criteria

| ID | Criterion | Verify |
|----|-----------|--------|
| P1-01 | `Contact` dataclass with all problem statement §5 fields | Code review |
| P1-02 | `EmailDraft`: `subject`, `body`, `word_count` | Code review |
| P1-03 | `LogEntry` + `DeliveryResult` defined | Code review |
| P1-04 | `load_config()` reads `.env`; `DRY_RUN` defaults true | Test with no `.env` |
| P1-05 | `AppConfig` includes SMTP, `SEND_MODE`, `MAX_OUTREACH_PER_RUN`, `INPUT_PATH` | Code review |
| P1-06 | Word-count helper available for generator | Import test |

### Edge-case coverage

| Edge ID | Expected |
|---------|----------|
| C-01 | Runs without `.env` |
| C-04 | Truthy parsing for `DRY_RUN` |

### Manual check

```bash
python -c "from config import load_config; c=load_config(); print(c.dry_run, c.max_outreach_per_run)"
```

### Phase 1 verdict

| Pass | Fail |
|------|------|
| P1 Block + imports clean | Missing types or wrong defaults |

---

## Phase 2: Input Loader (FR1)

**Scope:** `input_loader.py`, `contacts.json`, validation.

### Block criteria

| ID | Criterion | Verify |
|----|-----------|--------|
| P2-01 | `load_targets()` returns `list[Contact]` | Unit/manual test |
| P2-02 | `contacts.json` has ≥3 valid records | File review |
| P2-03 | Required fields validated (I-10–I-14) | Fixture with missing field |
| P2-04 | Invalid email skipped or rejected (I-30) | Fixture |
| P2-05 | Missing `recipient_name` → default (I-20) | Fixture |
| P2-06 | At least one record with and without `personalization_note` | File review |
| P2-07 | Missing file → clear error (I-01) | Rename file test |

### Warn criteria

| ID | Criterion |
|----|-----------|
| P2-W1 | Whitespace stripped on required strings (I-13) |
| P2-W2 | `INPUT_PATH` from config honored |

### Manual check

```bash
python -c "from input_loader import load_targets; cs=load_targets('contacts.json'); print(len(cs), cs[0].company)"
# Test missing file:
python -c "from input_loader import load_targets; load_targets('missing.json')" 2>&1
```

### Phase 2 verdict

| Pass | Fail |
|------|------|
| ≥3 contacts load; invalid row handled visibly | Crashes on bad JSON or silent drop |

---

## Phase 3: Email Generator (FR2)

**Scope:** `email_generator.py`, template, constraints.

### Block criteria

| ID | Criterion | Verify |
|----|-----------|--------|
| P3-01 | `generate_email(contact, config) -> EmailDraft` | Signature |
| P3-02 | Output includes subject + body | Print sample |
| P3-03 | Six-part anatomy present (problem §7) | Rubric review of 1 email |
| P3-04 | Uses `personalization_note` when set (G-02) | Two fixtures |
| P3-05 | Fallback hook when note missing (I-21) | Fixture |
| P3-06 | `word_count` computed; warn if >150 (G-03) | Long background test |
| P3-07 | No invented facts (G-10, AP-06) | Code review — template vars only |
| P3-08 | Three companies → three distinguishable bodies (I-53) | Run on `contacts.json` |
| P3-09 | `python email_generator.py` or equivalent demo entry | Run command |

### Edge-case coverage

| Edge ID | Expected |
|---------|----------|
| G-06 | Natural greeting for default name |
| G-07 | Apostrophe in company safe |
| I-43 | Long background → warn, no crash |

### Manual check

```bash
python email_generator.py
# Or:
python -c "
from input_loader import load_targets
from email_generator import generate_email
from config import load_config
for c in load_targets('contacts.json'):
    d = generate_email(c, load_config())
    print(c.company, d.word_count, d.subject[:50])
"
```

### Phase 3 verdict

| Pass | Fail |
|------|------|
| All P3 Block; word count honest | Generic identical bodies or AP-06 |

---

## Phase 4: Preview & Confirmation (FR3)

**Scope:** `preview.py` or `main.py` preview helpers.

### Block criteria

| ID | Criterion | Verify |
|----|-----------|--------|
| P4-01 | Full preview: company, role, recipient, subject, body, word count | Visual run |
| P4-02 | Prompt accepts `send`, `draft`, `skip` (P-01–P-03) | Interactive test |
| P4-03 | `skip` does not call sender | Code review + run |
| P4-04 | No SMTP/network in this phase | Grep `smtplib` / send not wired |
| P4-05 | Invalid input handled (P-04, P-05) | Type garbage at prompt |
| P4-06 | Comment or structure documents FR3 gate | Code review |

### Edge-case coverage

| Edge ID | Expected |
|---------|----------|
| P-02 | `send` + dry-run → no network (when wired in P5) |

### Manual check

Run preview for one contact; choose `skip` — program must continue or exit without send.

### Phase 4 verdict

| Pass | Fail |
|------|------|
| FR3 visible in UX | Send path without prompt (AP-02) |

---

## Phase 5: Orchestrator & Dry-Run Pipeline

**Scope:** `main.py` loop, `DryRunEmailSender`, volume cap.

### Block criteria

| ID | Criterion | Verify |
|----|-----------|--------|
| P5-01 | `run_outreach_pipeline()` wires load → generate → preview → deliver | Code review |
| P5-02 | `DRY_RUN=true` performs no real network I/O | Run with network monitor or grep |
| P5-03 | Dry-run returns success `DeliveryResult` or equivalent | Run + inspect |
| P5-04 | `MAX_OUTREACH_PER_RUN` enforced (I-50) | 10 contacts, cap 5 |
| P5-05 | Batch summary printed (O-05) | End of run output |
| P5-06 | `skip` continues to next contact (O-04) | Interactive run |
| P5-07 | State order: generate before prompt before deliver | Code review |

### Edge-case coverage

| Edge ID | Expected |
|---------|----------|
| O-01 | Zero contacts → no preview loop |
| C-05 | No send without confirm even if DRY_RUN false later |

### Manual check

```bash
DRY_RUN=true python main.py
# Step through: send once, skip once
```

### Phase 5 verdict

| Pass | Fail |
|------|------|
| Full loop works offline | Crashes mid-batch or AP-02 |

---

## Phase 6: Logging (FR5)

**Scope:** `logger.py`, CSV append, integration in `main.py`.

### Block criteria

| ID | Criterion | Verify |
|----|-----------|--------|
| P6-01 | `outreach_log.csv` created with header (L-01) | Delete file, rerun |
| P6-02 | Columns: timestamp, recipient_email, company, role, subject, status, error_message | Header row |
| P6-03 | Status values include: generated, skipped, failed (and sent/drafted when applicable) | After test run |
| P6-04 | One row per contact processed in a run | Count rows vs contacts |
| P6-05 | Append on re-run, not overwrite (L-06) | Two runs → more rows |
| P6-06 | Skip logs `skipped` (P-01) | Interactive test |
| P6-07 | CSV escapes commas/quotes in subject (L-04, L-05) | Subject with comma test |

### Edge-case coverage

| Edge ID | Expected |
|---------|----------|
| P-07 | Failed send → `failed` + error_message |

### Manual check

```bash
DRY_RUN=true python main.py
head -5 outreach_log.csv
wc -l outreach_log.csv
```

### Phase 6 verdict

| Pass | Fail |
|------|------|
| Auditable log for every outcome | AP-05 silent skip |

---

## Phase 7: Real Email Delivery (FR4)

**Scope:** SMTP or Gmail adapter, live send, error mapping.

### Block criteria

| ID | Criterion | Verify |
|----|-----------|--------|
| P7-01 | `deliver_email()` implements real provider when `DRY_RUN=false` | Config + run |
| P7-02 | STARTTLS / secure transport documented (architecture §15) | README or code |
| P7-03 | From address uses `SMTP_USER` / config | Sent email headers |
| P7-04 | Self-test: one email to own address in Sent/Drafts | Screenshot proof |
| P7-05 | Auth failure → `failed` + helpful message (S-01) | Wrong password test |
| P7-06 | FR3 still required before deliver (AP-02) | Code review |
| P7-07 | Empty subject/body not sent (S-06) | Code guard |
| P7-08 | Log row `sent` or `drafted` on success | CSV check |

### Warn criteria

| ID | Criterion |
|----|-----------|
| P7-W1 | `SEND_MODE=draft` works if Gmail API chosen |
| P7-W2 | README documents App Password setup |

### Edge-case coverage

| Edge ID | Expected |
|---------|----------|
| S-02 | Timeout does not hang |
| P-07 | SMTP fail → log failed, continue batch |

### Manual check

```bash
# .env: DRY_RUN=false, SMTP_* valid, first contact = your email
python main.py
```

### Phase 7 verdict

| Pass | Fail |
|------|------|
| One real proof email + log | AP-02, AP-01, or no error on auth fail |

---

## Phase 8: MVP Hardening & Submission

**Scope:** 5 contacts, guardrails, README, acceptance §17–18.

### Block criteria

| ID | Criterion | Verify |
|----|-----------|--------|
| P8-01 | ≥5 contacts in input | Count in JSON |
| P8-02 | ≥5 personalized emails generated | Log / screenshots |
| P8-03 | Company/role visible in each body | Sample review |
| P8-04 | All emails ≤150 words OR warning shown | word_count column or preview |
| P8-05 | Ethics: cap ≤5 per run default (E-06) | Config |
| P8-06 | README: setup, run, sending method, safety | README review |
| P8-07 | `outreach_log.csv` submitted artifact | File in repo or instructions |
| P8-08 | Acceptance §17 checklist complete | Table below |
| P8-09 | No AP-01–AP-06 in final codebase | Audit |

### MVP acceptance matrix (problem statement §17)

| # | Requirement | Pass? |
|---|-------------|-------|
| A1 | ≥5 personalized cold emails | |
| A2 | Subject + body each | |
| A3 | Company/role personalization | |
| A4 | Preview before send | |
| A5 | Send or draft successfully | |
| A6 | Each attempt logged | |
| A7 | Proof screenshots (Sent/Drafts) | |

### Submission package (§18)

| # | Artifact | Present? |
|---|----------|----------|
| S1 | GitHub repo / zip | |
| S2 | Screenshot of 5 emails | |
| S3 | `outreach_log.csv` | |
| S4 | How it works (README) | |
| S5 | Sending method noted | |

### Regression suite (run before sign-off)

Execute scenarios from [edge-case.md §9](./edge-case.md#9-cross-module-regression-scenarios).

### Phase 8 verdict

| Pass | Fail |
|------|------|
| All P8 Block + acceptance matrix | Any §17 item missing |

---

## Stretch Phase Evaluations (Optional)

### Stretch A: Gmail drafts + CSV

| ID | Criterion |
|----|-----------|
| SA-01 | Draft appears in Gmail Drafts without send |
| SA-02 | `jobs.csv` loads with column mapping |
| SA-03 | Invalid CSV row handled like JSON (skip/warn) |

### Stretch B: Streamlit UI

| ID | Criterion |
|----|-----------|
| SB-01 | UI calls shared `generate_email`, not duplicate template |
| SB-02 | Confirm button before send; respects `DRY_RUN` |
| SB-03 | Log still appended from UI actions |

### Stretch C: LLM + quality

| ID | Criterion |
|----|-----------|
| SC-01 | Validator enforces ≤150 words |
| SC-02 | Validator blocks fabricated referrals (AP-06) |
| SC-03 | Human confirm still required (AP-02) |

### Stretch D: Dedup + follow-ups

| ID | Criterion |
|----|-----------|
| SD-01 | Second run skips email already in log |
| SD-02 | `do_not_contact.csv` honored |
| SD-03 | Follow-up links to `parent_id` in log |

---

## Regression Gates Between Phases

Run after completing the phase listed.

| After phase | Minimum regression |
|-------------|-------------------|
| 1 | Import all models + config |
| 2 | Load contacts; invalid fixture |
| 3 | Generate for all loaded contacts |
| 4 | Preview + skip one contact |
| 5 | Full `DRY_RUN=true` loop |
| 6 | Log row count matches interactions |
| 7 | One live email + log `sent`/`drafted` |
| 8 | Full §9 edge-case table + acceptance matrix |

---

## AI Build Review Template

Copy for each phase completion PR or chat summary.

```markdown
## Phase N Evaluation

**Builder:** AI / Human  
**Date:** YYYY-MM-DD  
**Commit / branch:** 

### Block criteria
| ID | Pass/Fail | Notes |
|----|-----------|-------|
| PN-01 | | |

### Anti-patterns
| AP-01..06 | Clear / Violation |

### Edge cases exercised
- [ ] List IDs from edge-case.md (e.g. I-30, G-03)

### Commands run
```

### Verdict: APPROVED / NEEDS REVISION

**Blockers:**

```

---

## Evaluator Quick Reference

| Phase | Primary FR | Key path(s) under `src/closer/` | One-liner smoke test |
|-------|------------|----------------------------------|----------------------|
| 0 | — | `cli/main.py`, phase package stubs | `python main.py` → 0 |
| 1 | NFR | `domain/`, `config/` | import `load_config` |
| 2 | FR1 | `input/`, `data/contacts.json` | load 3+ contacts |
| 3 | FR2 | `generation/` | 3 distinct bodies |
| 4 | FR3 | `preview/` | skip → no send |
| 5 | FR4 dry | `cli/main.py` | full loop DRY_RUN |
| 6 | FR5 | `audit/`, `logs/` | CSV rows append |
| 7 | FR4 live | `delivery/` | 1 real email proof |
| 8 | All | README, `data/`, `logs/` | §17 + §18 complete |

---

## Related Documents

- [edge-case.md](./edge-case.md) — input/output failure catalog  
- [implementation-plan.md](./implementation-plan.md) — tasks per phase  
- [architecture.md](./architecture.md) — module contracts  
- [problemStatement.md](./problemStatement.md) — requirements source

# Edge Cases: The Closer

Reference for implementers and reviewers. Covers **basic edge cases** expected in MVP and common failure modes during live builds. For architecture and phases, see [architecture.md](./architecture.md) and [implementation-plan.md](./implementation-plan.md).

**Legend**

| Severity | Meaning |
|----------|---------|
| **Block** | Must handle; incorrect behavior is a bug |
| **Warn** | Should surface a warning; continue if safe |
| **Defer** | Document or handle in stretch / Phase 8 |

---

## 1. Input & Contact Data (FR1)

### 1.1 File & format

| # | Case | Expected behavior | Severity |
|---|------|-------------------|----------|
| I-01 | `contacts.json` missing | Clear error: file not found; exit non-zero or empty run with message | Block |
| I-02 | `contacts.json` empty array `[]` | Message: no targets loaded; exit gracefully | Block |
| I-03 | Invalid JSON (trailing comma, syntax error) | Parse error with file path; no partial load | Block |
| I-04 | JSON root is object, not array | Error: expected list of contacts | Block |
| I-05 | `INPUT_PATH` points to non-existent file | Same as I-01 | Block |
| I-06 | `INPUT_PATH` is directory | Error: not a file | Block |
| I-07 | File encoding not UTF-8 | Error or explicit UTF-8 read with clear failure | Warn |
| I-08 | Duplicate keys in one JSON object | Last value wins (stdlib); document behavior | Defer |

### 1.2 Required fields

| # | Case | Expected behavior | Severity |
|---|------|-------------------|----------|
| I-10 | Missing `recipient_email` | Skip record + warning, OR abort batch (document choice) | Block |
| I-11 | Missing `company`, `role`, `candidate_name`, or `candidate_background` | Skip record + warning with index/id | Block |
| I-12 | Required field present but empty string `""` | Treat as missing | Block |
| I-13 | Required field whitespace only `"   "` | Treat as missing after `.strip()` | Block |
| I-14 | `null` for required field in JSON | Treat as missing | Block |

### 1.3 Optional fields

| # | Case | Expected behavior | Severity |
|---|------|-------------------|----------|
| I-20 | Missing `recipient_name` | Default greeting: `"there"` / `"Hi there"` | Block |
| I-21 | Missing `personalization_note` | Generator uses `company` + `role` fallback hook | Block |
| I-22 | Missing `portfolio_url` | Sign-off without link; no placeholder URL | Block |
| I-23 | Missing `job_url`, `linkedin_url`, `resume_link` | Omit from body; no invented links | Block |
| I-24 | Extra unknown JSON fields | Ignore silently | Defer |

### 1.4 Email & URL validation

| # | Case | Expected behavior | Severity |
|---|------|-------------------|----------|
| I-30 | Invalid email: `not-an-email`, `@missing.com`, `user@` | Skip record or reject with reason | Block |
| I-31 | Email with display name `"Name <user@x.com>"` | Parse address or reject (document) | Warn |
| I-32 | Uppercase / mixed-case email | Normalize to lowercase for log; send as provided or normalized | Warn |
| I-33 | Plus-alias `user+tag@gmail.com` | Accept as valid | Block |
| I-34 | Internationalized domain (IDN) | Accept if library validates; else warn | Defer |
| I-35 | `portfolio_url` invalid (no scheme, `not a url`) | Warn; omit link from body | Warn |
| I-36 | Very long URL (2000+ chars) | Include or truncate; do not crash | Warn |

### 1.5 Content in fields (injection & display)

| # | Case | Expected behavior | Severity |
|---|------|-------------------|----------|
| I-40 | Newlines in `company` or `role` | Strip or single-line; no broken template | Warn |
| I-41 | HTML/script in `personalization_note` | Treat as plain text; do not execute | Block |
| I-42 | Emoji or non-ASCII in names | Preserve in output if UTF-8 | Warn |
| I-43 | Extremely long `candidate_background` (500+ words) | Generate email; word_count may exceed 150 → warn | Warn |
| I-44 | Special chars in subject-related fields: `"`, `\n`, `%` | No crash; safe string formatting | Block |

### 1.6 Batch size & duplicates

| # | Case | Expected behavior | Severity |
|---|------|-------------------|----------|
| I-50 | More contacts than `MAX_OUTREACH_PER_RUN` | Process only first N; message that cap applied | Block |
| I-51 | `MAX_OUTREACH_PER_RUN=0` or negative | Error at config load or treat as 0 with message | Block |
| I-52 | Duplicate `recipient_email` in same file | Process both unless dedup stretch; warn optional | Warn |
| I-53 | Same company/role, different recipients | Distinct emails per contact | Block |

---

## 2. Configuration & Environment

| # | Case | Expected behavior | Severity |
|---|------|-------------------|----------|
| C-01 | No `.env` file | Use defaults; `DRY_RUN=true` | Block |
| C-02 | `.env` missing `SMTP_PASSWORD` with `DRY_RUN=true` | Run succeeds without SMTP | Block |
| C-03 | `.env` missing SMTP vars with `DRY_RUN=false` | Fail before send with actionable message | Block |
| C-04 | `DRY_RUN=true` (string) vs `True` vs `1` | Parse truthy consistently | Block |
| C-05 | `DRY_RUN=false` but user never confirmed send | No SMTP call (FR3) | Block |
| C-06 | Invalid `SMTP_PORT` (e.g. `abc`) | Config error at startup | Block |
| C-07 | `SEND_MODE` not `draft` or `send` | Default or error | Warn |
| C-08 | Wrong type for `MAX_OUTREACH_PER_RUN` in env | Error or safe default | Block |
| C-09 | Secrets committed in repo | Prevent via `.gitignore`; not runtime fix | Block |

---

## 3. Email Generation (FR2)

| # | Case | Expected behavior | Severity |
|---|------|-------------------|----------|
| G-01 | All optional fields missing | Valid email with company/role hook only | Block |
| G-02 | `personalization_note` empty string | Use fallback hook, not empty sentence | Block |
| G-03 | Word count > 150 | Warning in preview; optional flag on `EmailDraft` | Block |
| G-04 | Word count exactly 150 | No warning | Block |
| G-05 | Very short background (`"AI"`) | Still produce coherent email; may feel thin | Warn |
| G-06 | `recipient_name` is `"there"` | Greeting reads naturally (`Hi there,`) | Block |
| G-07 | Company name with apostrophe: `O'Reilly Media` | Correct escaping in template | Block |
| G-08 | Role with special chars: `SWE (New Grad)` | Subject/body include role intact | Block |
| G-09 | Multiple asks in template | Template must enforce **one** CTA only | Block |
| G-10 | Template invents experience not in `candidate_background` | Must not add employers, referrals, or meetings | Block |
| G-11 | `portfolio_url` present | Appears in sign-off only once | Block |
| G-12 | Identical contacts except email | Bodies differ only by recipient if template uses name | Warn |

---

## 4. Preview & Confirmation (FR3)

| # | Case | Expected behavior | Severity |
|---|------|-------------------|----------|
| P-01 | User enters `skip` | No `deliver_email`; log `skipped` | Block |
| P-02 | User enters `send` with `DRY_RUN=true` | No network; log `generated` / `dry_run` | Block |
| P-03 | User enters `draft` with `DRY_RUN=true` | Same as P-02 | Block |
| P-04 | Empty input at prompt | Re-prompt or default to `skip` (document) | Block |
| P-05 | Invalid input: `yes`, `y`, `n`, `maybe` | Re-prompt or map `yes`→send only if documented | Warn |
| P-06 | Ctrl+C / EOF during prompt | Graceful exit; log in-progress contact if applicable | Warn |
| P-07 | User confirms send then SMTP fails | Log `failed` with error; continue to next contact | Block |
| P-08 | Preview shows wrong contact metadata | Display `company`, `role`, `recipient_email` for current index | Block |
| P-09 | Body contains leading/trailing whitespace | Show as stored; readable formatting | Warn |

---

## 5. Email Delivery (FR4)

| # | Case | Expected behavior | Severity |
|---|------|-------------------|----------|
| S-01 | SMTP auth failure (wrong password) | `failed` + message mentioning App Password | Block |
| S-02 | SMTP connection timeout | `failed`; no hang forever | Block |
| S-03 | Invalid recipient at SMTP layer | `failed` with provider error | Block |
| S-04 | `SEND_MODE=draft` but SMTP only supports send | Document limitation; use Gmail API or send to self | Warn |
| S-05 | Send to self (test) | Success; appears in Sent/Drafts | Block |
| S-06 | Empty subject or body passed to sender | Reject before SMTP; do not send blank email | Block |
| S-07 | Subject line newline | Strip newlines from subject | Block |
| S-08 | Non-ASCII in subject/body | UTF-8 encoding in MIME | Warn |
| S-09 | `DRY_RUN` toggled mid-run | Only read config at startup per run | Defer |
| S-10 | Rate limit / temporary 4xx from provider | `failed`; suggest retry | Warn |

---

## 6. Logging (FR5)

| # | Case | Expected behavior | Severity |
|---|------|-------------------|----------|
| L-01 | `outreach_log.csv` does not exist | Create with header row | Block |
| L-02 | Log file exists, no header | Append only if format matches; else error | Warn |
| L-03 | Log file locked / permission denied | Clear error; do not claim success | Block |
| L-04 | Subject contains comma or quote | CSV-escape fields properly | Block |
| L-05 | Subject/body contains newline | CSV-escape; one row per event | Block |
| L-06 | Same contact run twice | Two append rows (audit trail) | Block |
| L-07 | Skip without generation attempted | Still log if preview was shown | Warn |
| L-08 | Clock skew / timezone | Consistent timestamp format (ISO-8601) | Warn |
| L-09 | Disk full on append | Error surfaced; send may have succeeded | Warn |

---

## 7. Orchestrator & Pipeline

| # | Case | Expected behavior | Severity |
|---|------|-------------------|----------|
| O-01 | Zero contacts after validation | Exit before loop; no empty preview | Block |
| O-02 | Exception in `generate_email` | Log `failed` or skip; do not crash whole batch silently | Block |
| O-03 | Exception in `deliver_email` | Log `failed`; continue batch | Block |
| O-04 | User skips all contacts | Summary: 0 sent, N skipped; log reflects skips | Block |
| O-05 | Mixed outcomes in one run | Summary counts: sent, drafted, skipped, failed | Block |
| O-06 | Re-run `main.py` immediately | Idempotent load; new log rows appended | Block |
| O-07 | Import cycle between modules | Clean imports: models ← services ← main | Block |

---

## 8. Safety & Ethics

| # | Case | Expected behavior | Severity |
|---|------|-------------------|----------|
| E-01 | Bulk send without confirmation per email | **Must not happen** — FR3 gate every time | Block |
| E-02 | `DRY_RUN=false` on first ever run | README warns; self-email test first | Block |
| E-03 | Generic email (no company/role in body) | Warn or reject before send | Warn |
| E-04 | `candidate_name` ≠ `SENDER_NAME` / SMTP identity mismatch | Warn in docs; no impersonation | Warn |
| E-05 | Contact on opt-out list (stretch) | Skip with message | Defer |
| E-06 | >5 sends in one run with cap disabled | Cap enforced by `MAX_OUTREACH_PER_RUN` | Block |

---

## 9. Cross-Module Regression Scenarios

Run after Phases 5–8 to catch integration gaps.

| Scenario | Steps | Pass if |
|----------|--------|---------|
| Happy path dry-run | 3 valid contacts, confirm `send` on one, `skip` on two | 1 generated/dry_run, 2 skipped in log |
| Bad email row | 1 invalid email among 3 | 2 processed, 1 skipped with warning |
| Long background | 1 contact with 400-word background | Warning if >150 words; no crash |
| SMTP failure | Wrong password, user confirms send | `failed` row; next contact still runs |
| Empty input file | `[]` | Clean message, exit 0 or 1 (document) |

---

## 10. Stretch-Goal Edge Cases (Reference)

| # | Case | Notes |
|---|------|-------|
| X-01 | LLM returns >150 words | Validator rejects or truncates with warn |
| X-02 | LLM invents referral | Validator blocks send |
| X-03 | CSV wrong column headers | Mapping error with expected columns |
| X-04 | Streamlit double-click Send | Debounce or idempotent log |
| X-05 | Dedup: email in prior log | Skip with reason |
| X-06 | Gmail OAuth token expired | Refresh or clear re-auth instructions |

---

## 11. Test Data Snippets

Use in `contacts.json` fixtures or manual QA.

```json
{
  "recipient_name": "",
  "recipient_email": "invalid-email",
  "company": "   ",
  "role": "Intern",
  "candidate_name": "Alex Kim",
  "candidate_background": "Python"
}
```

```json
{
  "recipient_name": "O'Brien",
  "recipient_email": "test+alias@example.com",
  "company": "Acme \"AI\" Labs",
  "role": "Backend\nEngineer",
  "candidate_name": "Alex Kim",
  "candidate_background": "Short.",
  "personalization_note": "<script>alert(1)</script>"
}
```

---

## 12. Out of Scope (Not Edge Cases for MVP)

- Scraping job boards or finding emails automatically  
- Multi-user accounts or shared inboxes  
- Scheduling sends for later  
- Tracking opens/clicks  
- CAN-SPAM legal compliance automation (human responsibility remains)  

---

## Related Documents

- [eval.md](./eval.md) — phase-by-phase pass/fail rubric for AI builds  
- [implementation-plan.md](./implementation-plan.md) — build order  
- [problemStatement.md](./problemStatement.md) — functional requirements

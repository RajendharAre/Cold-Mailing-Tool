# Deployment Plan: The Closer

This document describes how to deploy **The Closer** for demos, personal use, or submission review. It covers the **Streamlit UI** (recommended for hosted deployment) and the **CLI** (recommended for local real sends).

---

## 1. Can we use Streamlit to deploy this project?

**Yes — for the web UI path.** The repo already ships a Streamlit app that reuses the same core pipeline as the CLI:

| Entry point | Command |
|-------------|---------|
| Root launcher | `streamlit run streamlit_app.py` |
| Package module | `PYTHONPATH=src streamlit run src/closer/ui/app.py` |

Streamlit is a good fit because:

- The UI (`src/closer/ui/app.py`) calls the same modules: `load_config`, `load_targets`, `generate_email`, `handle_contact_action`, `append_log`.
- Dependencies are minimal (`python-dotenv`, `streamlit`).
- No database or background workers are required for MVP.
- Human-in-the-loop review maps naturally to buttons (Send / Draft / Skip).

**Streamlit is not a fit for unattended CLI batch runs.** If you only need `python main.py` in a terminal, you do not need Streamlit — run locally or on a VM with SSH.

**Important constraints when deploying Streamlit publicly:**

| Constraint | Why it matters |
|------------|----------------|
| Ephemeral disk | On Streamlit Community Cloud, `logs/outreach_log.csv` and edits to `data/contacts.json` may not persist across restarts or redeploys. |
| Secrets on a URL | A public app with `DRY_RUN=false` and real SMTP credentials is a security risk. Prefer `DRY_RUN=true` for demos, or add auth + private hosting. |
| Gmail SMTP from cloud | Google may block or rate-limit SMTP from some cloud IPs. Test before relying on live sends from a hosted app. |
| Single-user design | Architecture targets one job seeker, not multi-tenant SaaS. Do not expose as an open bulk-send service. |

**Recommendation by goal:**

| Goal | Best deployment |
|------|-----------------|
| Demo / submission / teaching | **Streamlit Community Cloud** with `DRY_RUN=true` |
| Personal real outreach | **Local CLI** or **private Streamlit** on your machine |
| Shared team tool (small) | **Private VPS + Docker + Streamlit** with secrets in env |
| Production SaaS | Out of MVP scope — would need auth, persistent storage, and a proper email API |

---

## 2. Deployment architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                     Deployment options                           │
├─────────────────┬───────────────────────┬───────────────────────┤
│ Streamlit Cloud │ Self-hosted Streamlit │ Local only (CLI)      │
│ (public demo)   │ (VPS / Docker)        │ (real Gmail sends)    │
└────────┬────────┴───────────┬───────────┴───────────┬───────────┘
         │                    │                       │
         ▼                    ▼                       ▼
   streamlit_app.py      streamlit + .env         python main.py
         │                    │                       │
         └────────────────────┴───────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │  src/closer/* (shared core)   │
              │  config → input → generate    │
              │  → preview/workflow → delivery│
              │  → audit log                  │
              └───────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
  data/contacts.json   logs/outreach_log.csv   Gmail SMTP
  (read / optional)    (append-only)           (if DRY_RUN=false)
```

---

## 3. Pre-deployment checklist

Complete these before any hosted deploy:

- [ ] **Tests pass locally:** `python scripts/validate_mvp.py` and optionally `python -m pytest tests/ -q`
- [ ] **UI works locally:** `streamlit run streamlit_app.py` — generate, preview, skip/draft/send with `DRY_RUN=true`
- [ ] **No secrets in git:** `.env` is gitignored; only `.env.example` is committed
- [ ] **Sample data committed:** `data/contacts.json` has valid demo contacts (no real PII you do not want public)
- [ ] **Default safety:** `DRY_RUN=true` for any public URL
- [ ] **Python version:** 3.9+ (3.10+ recommended); match locally and on host
- [ ] **Entry point:** `streamlit_app.py` at repo root (already present)

Optional hardening for hosted demos:

- [ ] Add `.streamlit/config.toml` (theme, server headless settings)
- [ ] Add `packages.txt` only if you need apt packages on Streamlit Cloud (not required for current deps)
- [ ] Document that reviewers should use **Skip** / **Draft** in dry-run, not live send

---

## 4. Option A — Streamlit Community Cloud (recommended for demos)

Best for: submission links, portfolio demos, teaching, reviewers who cannot clone the repo.

### 4.1 Prerequisites

- GitHub repo pushed (public or private with Streamlit access)
- [Streamlit Community Cloud](https://streamlit.io/cloud) account linked to GitHub
- Branch with working `streamlit_app.py` and `requirements.txt`

### 4.2 Deploy steps

1. Push the repo to GitHub (if not already).
2. Open [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Select:
   - **Repository:** `your-org/cold-email-parser`
   - **Branch:** `main` (or your feature branch)
   - **Main file path:** `streamlit_app.py`
4. Click **Advanced settings** → add secrets (see §6). For demos, only:

   ```toml
   DRY_RUN = "true"
   SEND_MODE = "draft"
   MAX_OUTREACH_PER_RUN = "5"
   INPUT_PATH = "data/contacts.json"
   LOG_PATH = "logs/outreach_log.csv"
   ```

5. Deploy. First build installs `requirements.txt` and starts the app.

### 4.3 Post-deploy verification

- [ ] Sidebar shows `DRY_RUN: true`
- [ ] Contacts load from `data/contacts.json`
- [ ] **Generate email** produces subject + body
- [ ] **Skip** / **Draft** / **Send** update session and append to log (within session; log may reset on redeploy)
- [ ] No SMTP errors when `DRY_RUN=true` (no credentials required)

### 4.4 Limitations on Community Cloud

| Item | Behavior |
|------|----------|
| `logs/outreach_log.csv` | Written under repo mount; may not survive cold starts — treat as demo-only audit |
| Uploading new contacts | Not in MVP UI — use committed `data/contacts.json` or add file uploader later |
| Live Gmail send | Possible but discouraged on public apps; test SMTP from cloud IP first |
| CLI `main.py` | Not used; only Streamlit process runs |

---

## 5. Option B — Self-hosted Streamlit (VPS / Docker / Railway / Render)

Best for: private access, persistent disk, real SMTP from a stable IP you control.

### 5.1 Runtime command

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit with real values
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
```

### 5.2 Environment variables

Set the same variables as `.env.example` on the host (platform dashboard or systemd `EnvironmentFile`):

| Variable | Required when | Notes |
|----------|---------------|-------|
| `DRY_RUN` | Always | `true` until you intentionally enable sends |
| `SMTP_USER` | `DRY_RUN=false` | Gmail address |
| `SMTP_PASSWORD` | `DRY_RUN=false` | Gmail App Password |
| `INPUT_PATH` | Optional | Default `data/contacts.json` |
| `LOG_PATH` | Optional | Default `logs/outreach_log.csv` |

### 5.3 Docker sketch (optional)

Not in repo today; add when you need reproducible deploys:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Mount volumes for persistence:

```bash
docker run -p 8501:8501 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  --env-file .env \
  your-image:tag
```

### 5.4 Reverse proxy + HTTPS

For production-like hosting:

- Put **nginx** or **Caddy** in front of port 8501
- Enable TLS (Let's Encrypt)
- Add **HTTP basic auth** or OAuth if the app can send real email

---

## 6. Secrets management

| Environment | Where to put secrets |
|-------------|----------------------|
| Local dev | `.env` (never commit) |
| Streamlit Cloud | App → **Settings** → **Secrets** (TOML format) |
| Docker / VPS | `--env-file .env` or platform secret store |
| CI | GitHub Actions secrets (if you add deploy workflow later) |

**Streamlit secrets example** (demo-safe):

```toml
DRY_RUN = "true"
SEND_MODE = "draft"
MAX_OUTREACH_PER_RUN = "5"
SENDER_NAME = "Your Name"
# Omit SMTP_USER / SMTP_PASSWORD when DRY_RUN=true
```

**Live send example** (private host only):

```toml
DRY_RUN = "false"
SMTP_USER = "you@gmail.com"
SMTP_PASSWORD = "xxxx xxxx xxxx xxxx"
SENDER_NAME = "Your Name"
```

`load_config()` reads `os.environ` after `python-dotenv`; Streamlit Cloud injects secrets as environment variables, so no code changes are required.

---

## 7. Option C — Local CLI (no “deploy”, best for real sends)

Best for: your own job search workflow with Gmail proof (Sent folder + `outreach_log.csv`).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: DRY_RUN=false, SMTP_USER, SMTP_PASSWORD
python main.py
```

This path satisfies submission acceptance (preview, send, log) without exposing credentials to the internet.

---

## 8. Security and compliance

| Risk | Mitigation |
|------|------------|
| Leaked Gmail App Password | Use Streamlit secrets / host env; rotate password if exposed |
| Public bulk sending | Keep `MAX_OUTREACH_PER_RUN` ≤ 5; human confirm per email (built in) |
| PII in logs | Do not commit `logs/outreach_log.csv` with real recipients; use sample log for submission |
| Abuse of public URL | Default `DRY_RUN=true`; add auth before enabling real SMTP on any public URL |
| Gmail ToS | Low-volume, personalized outreach with human review — align with project ethics guardrails |

---

## 9. Suggested rollout phases

### Phase 1 — Local validation (day 0)

1. Run `streamlit run streamlit_app.py` locally with `DRY_RUN=true`
2. Run `python main.py` for one self-test send with `DRY_RUN=false`
3. Confirm `logs/outreach_log.csv` rows

### Phase 2 — Public demo (day 1)

1. Deploy to Streamlit Community Cloud with `DRY_RUN=true` only
2. Add deployment URL to `README.md` and submission notes
3. Capture screenshots from the hosted UI for `submission/screenshots/`

### Phase 3 — Private production (optional)

1. VPS or Docker with volume mounts for `data/` and `logs/`
2. TLS + authentication
3. `DRY_RUN=false` only after SMTP smoke test from that host

---

## 10. Files to add later (optional improvements)

| File | Purpose |
|------|---------|
| `.streamlit/config.toml` | Headless server, theme, `enableCORS`, `enableXsrfProtection` |
| `Dockerfile` | Reproducible self-hosted deploy |
| `.github/workflows/deploy.yml` | CI test + optional Streamlit redeploy |
| `src/closer/ui/app.py` — file uploader | Let operators upload `contacts.json` without redeploying |
| External storage adapter | S3/GCS for log + contacts if Community Cloud persistence is insufficient |

None of these are required for a first Streamlit Cloud demo.

---

## 11. Quick reference

| Question | Answer |
|----------|--------|
| Can we deploy with Streamlit? | **Yes** — use `streamlit_app.py` |
| Best platform for a demo link? | **Streamlit Community Cloud** |
| Best way to send real email? | **Local CLI** with `.env` |
| Default for any public deploy? | **`DRY_RUN=true`** |
| Main file path on Streamlit Cloud? | `streamlit_app.py` |
| Dependencies file? | `requirements.txt` |

---

## 12. Submission note

For course/project submission, a typical deliverable set is:

1. **GitHub repo** (this project)
2. **Hosted demo URL** (Streamlit Cloud, dry-run only)
3. **Local proof** — `logs/outreach_log.csv` or `logs/outreach_log.sample.csv` + Gmail screenshot from local CLI run

See [SUBMISSION.md](./SUBMISSION.md) for the full checklist.

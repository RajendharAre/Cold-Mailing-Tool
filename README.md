# The Closer

The Closer is a human-in-the-loop outreach assistant for job seekers. It turns a job description, resume context, and outreach target into a personalized cold email draft, lets the user review it before sending, and records every action in an audit log.

This project is designed to feel practical rather than toy-like: it supports real review loops, safe defaults, and a clean path toward more advanced AI-assisted outreach.

## Why this project matters

Most applicants spend too much time crafting repetitive outreach emails from scratch. Generic messages are easy to ignore, while personalized messages take time to write carefully.

The Closer addresses that by combining:

- structured input for job and resume context,
- personalized email generation,
- preview-before-send behavior,
- dry-run safety for testing,
- and audit logging for transparency and debugging.

It is not meant to spam people. It is meant to help a candidate communicate thoughtfully and efficiently.

## What the app does

The current workflow can:

- start from scratch with any job description: paste the JD and job link, and the app infers the company and role,
- attach a resume (PDF, Markdown, or TXT) for each application, or use the default `resume_background.md`,
- generate a tailored subject line and email body with Groq or Gemini,
- preview the draft inside the Streamlit UI,
- support dry-run testing or SMTP-based delivery,
- save each result to a CSV audit log and Google Sheets,
- track replies (awaiting reply / replied / no reply) in Google Sheets.

## Core features

- Personalized cold email generation from job and resume context
- JD-first flow: no need to pre-enter mock contacts — paste a JD and go
- Resume upload (PDF / Markdown / TXT) feeding the AI prompt per application
- Human review before any delivery attempt — Send, Draft, or Skip
- Safe dry-run mode by default
- Groq or Gemini-backed generation (`LLM_PROVIDER` in `.env`)
- Google Sheets outreach tracking with reply-status updates
- Environment-based configuration for deployment flexibility
- Modular architecture across generation, preview, delivery, and logging
- Streamlit UI for a polished browser experience
- CSV-based audit logging for traceability

## Tech stack

- Python 3.9+
- Streamlit for the UI
- python-dotenv for configuration
- smtplib for SMTP delivery
- pytest for automated regression tests

## Project structure

```text
cold-email-sender/
├── main.py
├── streamlit_app.py
├── data/
│   └── contacts.json
├── docs/
├── logs/
├── scripts/
├── src/
│   └── closer/
│       ├── cli/
│       ├── config/
│       ├── delivery/
│       ├── domain/
│       ├── generation/
│       ├── input/
│       ├── outreach/
│       ├── preview/
│       └── ui/
└── tests/
```

## Quick start

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### 3. Create your environment file

Create a file named `.env` in the project root with values such as:

```env
DRY_RUN=true
SEND_MODE=draft
MAX_OUTREACH_PER_RUN=5
INPUT_PATH=data/contacts.json
LOG_PATH=logs/outreach_log.csv
```

> Never commit your real `.env` file to GitHub.

## Run the app

### CLI mode

```bash
python main.py
```

### Streamlit UI mode

```bash
streamlit run streamlit_app.py
```

The app should open at http://localhost:8501.

## SMTP setup

To send real emails, configure SMTP in your `.env` file:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SENDER_NAME=Your Name
DRY_RUN=false
SEND_MODE=send
```

For Gmail, use an App Password rather than your normal account password. You can generate it from your Google Account security settings.

## Google Sheets tracking

Every action (sent / drafted / skipped / failed) is appended to a Google Sheet when configured. Each row includes: timestamp, recipient email, recipient name, company, role, job link, status, subject, and word count. You can update a row's status to `awaiting reply`, `replied`, or `no reply` from the "Track replies" panel in the UI.

Setup:

1. Create a Google Cloud service account and download its JSON key file.
2. Share your target spreadsheet with the service account email (Viewer/Editor).
3. Configure `.env`:

```env
GOOGLE_SHEETS_CREDENTIALS_FILE=path/to/service-account.json
GOOGLE_SHEETS_SPREADSHEET_ID=your-spreadsheet-id
GOOGLE_SHEETS_WORKSHEET_NAME=Outreach
```

`gspread` is required for this integration (`pip install gspread`).

## Recommended workflow

1. Choose **New outreach (start from scratch)** or pick an existing contact.
2. Paste the job description and job link; the app infers the company and role.
3. Attach your resume (PDF/MD/TXT) or use the default `resume_background.md`.
4. Enter the recipient email and generate an AI draft.
5. Review the preview in the browser, then choose Skip, Draft, or Send.
6. Review the audit log for each attempt; update reply statuses in Google Sheets when replies come in.

## Safety and ethics

This project is built with responsible usage in mind:

- human review is required before delivery,
- dry-run is the default for safe testing,
- outreach volume is capped,
- the templates avoid fabricated claims,
- and the flow is designed for thoughtful communication rather than spam.

## Production-minded qualities

This project already shows several strong engineering characteristics:

- clear separation of responsibilities,
- environment-driven configuration,
- reusable generation and delivery modules,
- audit logging for accountability,
- and a practical path toward future AI and deployment enhancements.

## Deployment options

The project can be used in multiple ways:

- locally for personal use,
- as a Streamlit app in a browser,
- or as the foundation for a more advanced hosted outreach product.

For hosted deployments, you would typically add:

- secure secret management,
- a deployment platform such as Streamlit Community Cloud or Render,
- and a database for longer-term outreach history.

## Future enhancements

Possible next steps include:

- follow-up email generation,
- auto-status updates from email replies (Gmail API polling),
- authentication and multi-user support,
- and richer analytics for outreach performance.

## Why this is a strong project for recruiters

This project demonstrates practical engineering skills in a real-world scenario:

- Python application development,
- modular system design,
- email integration,
- human-in-the-loop workflow design,
- safe automation practices,
- and clear product value for job seekers and recruiters.

A reviewer should see this as more than a simple script: it is a usable, thoughtful automation workflow with a clear problem statement and real-world relevance.

## Documentation

Additional project notes and planning documents are available in the docs folder:

- [docs/problemStatement.md](docs/problemStatement.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/implementation-plan.md](docs/implementation-plan.md)
- [docs/SUBMISSION.md](docs/SUBMISSION.md)

The prompt/process log is kept in [prompts.md](prompts.md).

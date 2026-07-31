# The Closer

The Closer is a practical, human-in-the-loop outreach assistant for job seekers. It helps users create personalized cold emails, review them before delivery, and track every outreach attempt with a structured audit trail.

This project is designed to demonstrate how software, email automation, and thoughtful personalization can work together in a safe and useful way.

## Why this project matters

Job seekers often spend too much time writing repetitive outreach emails from scratch. Generic messages tend to perform poorly, while personalized emails take time to craft manually.

The Closer solves this by combining:

- structured email generation,
- company/role personalization,
- preview-before-send behavior,
- safe defaults for testing,
- and audit logging for proof and debugging.

It is not built as a spam tool. It is built as a thoughtful outreach workflow that keeps the user in control.

## What the project does

The app can:

- load outreach targets from a JSON input file,
- generate a personalized subject line and email body,
- preview the message before sending,
- support dry-run testing and SMTP-based sending,
- save every result to a log file for traceability.

## Core features

- Personalized cold email generation using a reusable template system
- Human review before delivery
- Safe dry-run mode by default
- Config-driven behavior through environment variables
- Modular architecture with separate concerns for generation, preview, delivery, and logging
- Optional Streamlit-based UI for a more polished experience
- CSV-based audit logging for proof and debugging

## Tech stack

- Python 3.9+
- Streamlit for the web UI
- python-dotenv for environment configuration
- smtplib for SMTP delivery
- pytest for automated testing

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

### 1. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

```bash
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### 3. Create your environment file

Create a file named `.env` in the project root and add values such as:

```env
DRY_RUN=true
SEND_MODE=draft
MAX_OUTREACH_PER_RUN=5
INPUT_PATH=data/contacts.json
LOG_PATH=logs/outreach_log.csv
```

> Never commit your real `.env` file to GitHub.

## Run the application

### CLI mode

```bash
python main.py
```

### Streamlit UI mode

```bash
streamlit run streamlit_app.py
```

## SMTP configuration

If you want to send real emails, configure SMTP in your `.env` file:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SENDER_NAME=Your Name
DRY_RUN=false
SEND_MODE=send
```

For Gmail, use an App Password rather than your normal account password.

## How the workflow works

1. Load contact or job details from the input file.
2. Generate a personalized subject and body.
3. Preview the email for human review.
4. Choose one of the actions: send, draft, or skip.
5. Record the outcome in the log file.

## Safety and ethics

This project is built with responsible usage in mind:

- human review is required before delivery,
- default behavior is dry-run for safe testing,
- outreach volume is capped,
- templates avoid fabricated claims,
- and the flow is designed for thoughtful communication rather than spam.

## Production-minded qualities

This project is stronger than a basic demo because it already shows several production-style habits:

- a clean separation of responsibilities,
- configuration through environment variables,
- reusable modules for generation and delivery,
- log-based auditing,
- and a path toward deployment and expansion.

## Deployment options

The project can be used in several ways:

- locally for personal use,
- as a Streamlit app in the browser,
- or as a foundation for a more advanced hosted outreach product.

For hosted use, you would typically add:

- a web deployment platform,
- secure secret management,
- and possibly a database for persistent history.

## Future enhancements

Possible next steps include:

- Gmail draft support,
- AI-powered email rewriting,
- follow-up email generation,
- a database-backed history view,
- authentication and multi-user support,
- and richer analytics for outreach performance.

## Why this is a strong project for recruiters

This project demonstrates practical software engineering skills in a real-world scenario:

- Python application development
- modular system design
- API/email integration
- human-in-the-loop workflow design
- safe automation practices
- and a clear business value for job seekers and recruiters alike

A recruiter or reviewer should see this as more than a simple script: it is a usable, thoughtful automation workflow with a clear problem statement and practical impact.

## Documentation

Additional project notes and planning documents are available in the docs folder:

- [docs/problemStatement.md](docs/problemStatement.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/implementation-plan.md](docs/implementation-plan.md)
- [docs/SUBMISSION.md](docs/SUBMISSION.md)

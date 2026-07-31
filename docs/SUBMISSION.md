# Final Submission Checklist (Phase 8)

## Deliverables

| # | Item | Location |
|---|------|----------|
| 1 | GitHub repository | This repo |
| 2 | Screenshots of 5 personalized emails | `submission/screenshots/` |
| 3 | Outreach log CSV | `logs/outreach_log.csv` (your run) or `logs/outreach_log.sample.csv` (example) |
| 4 | How the system works | `README.md` |
| 5 | Sending method | README → **Sending method: Gmail SMTP** |

## MVP acceptance (problem statement §17)

- [ ] ≥5 personalized emails generated from `data/contacts.json`
- [ ] Each email has subject + body
- [ ] Company/role personalization in each body
- [ ] Preview shown before any send (`python main.py`)
- [ ] At least one successful send or dry-run logged
- [ ] Every attempt in `logs/outreach_log.csv`
- [ ] Screenshots of Sent folder or terminal previews

## Commands

```bash
# Validate generation (non-interactive)
python scripts/validate_mvp.py

# Optional unit tests
python -m pytest tests/ -q

# Create sample log artifact (dry_run status, no SMTP)
python scripts/seed_sample_log.py

# Interactive full pipeline
python main.py
```

## Badge (optional)

Post a public screenshot of **3 sent** personalized emails from your own Gmail address.

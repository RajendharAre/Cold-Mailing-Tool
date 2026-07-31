"""Orchestrator entrypoint and outreach pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from closer.config import AppConfig, load_config
from closer.generation import generate_email
from closer.input import load_targets
from closer.cli.guardrails import run_preflight_checks
from closer.outreach.workflow import apply_guardrails, handle_contact_action
from closer.preview import preview_email, prompt_action


@dataclass
class BatchSummary:
    processed: int = 0
    skipped: int = 0
    dry_run_sent: int = 0
    dry_run_drafted: int = 0
    sent: int = 0
    drafted: int = 0
    failed: int = 0
    logged: int = 0


def run_outreach_pipeline(config: AppConfig | None = None) -> BatchSummary:
    """
    Run the full outreach loop: load → generate → preview → confirm → deliver → log.

    Never calls deliver_email unless prompt_action returns send or draft.
    """
    cfg = config or load_config()
    contacts = load_targets(cfg.input_path)
    batch = apply_guardrails(contacts, cfg)
    summary = BatchSummary()

    if not batch:
        print("No contacts to process.")
        return summary

    total_loaded = len(contacts)
    if total_loaded > len(batch):
        print(
            f"Loaded {total_loaded} contact(s); capped to {len(batch)} "
            f"(MAX_OUTREACH_PER_RUN={cfg.max_outreach_per_run})."
        )
    else:
        print(f"Loaded {total_loaded} contact(s); processing {len(batch)}.")

    run_preflight_checks(batch, cfg)
    print(f"Log file: {cfg.log_path}")
    if not cfg.dry_run:
        print(
            "WARNING: DRY_RUN=false — real emails will be sent when you choose 'send'. "
            "Test with your own address first."
        )

    for index, contact in enumerate(batch, start=1):
        summary.processed += 1
        print(f"\n--- Contact {index}/{len(batch)} ---")

        draft = generate_email(contact, cfg)
        preview_email(draft, contact)
        action = prompt_action()

        outcome = handle_contact_action(contact, draft, cfg, action)
        print(outcome.message)

        if action == "skip":
            summary.skipped += 1
        elif outcome.log_status == "failed":
            summary.failed += 1
        elif cfg.dry_run:
            if outcome.delivery_result and outcome.delivery_result.status == "sent":
                summary.dry_run_sent += 1
            elif outcome.delivery_result and outcome.delivery_result.status == "drafted":
                summary.dry_run_drafted += 1
        elif outcome.log_status == "sent":
            summary.sent += 1
        elif outcome.log_status == "drafted":
            summary.drafted += 1

        summary.logged += 1

    _print_batch_summary(summary, dry_run=cfg.dry_run, log_path=cfg.log_path)
    return summary


def _print_batch_summary(
    summary: BatchSummary,
    dry_run: bool,
    log_path,
) -> None:
    print("\n" + "=" * 40)
    print("Batch summary")
    print(f"  processed:       {summary.processed}")
    print(f"  skipped:         {summary.skipped}")
    if dry_run:
        print(f"  dry_run sent:    {summary.dry_run_sent}")
        print(f"  dry_run drafted: {summary.dry_run_drafted}")
    else:
        print(f"  sent:            {summary.sent}")
        print(f"  drafted:         {summary.drafted}")
    print(f"  failed:          {summary.failed}")
    print(f"  log rows written: {summary.logged}")
    print(f"  log file:        {log_path}")
    print("=" * 40)


def main() -> None:
    config = load_config()
    print("The Closer — MVP ready (Phase 8)")
    print(f"  dry_run={config.dry_run}  send_mode={config.send_mode}")
    print(f"  input_path={config.input_path}")
    print()
    run_outreach_pipeline(config)


if __name__ == "__main__":
    main()

"""
Streamlit UI for The Closer.

Run from repo root:
  PYTHONPATH=src streamlit run src/closer/ui/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Ensure package imports when Streamlit sets cwd to this file's directory.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from closer.config import load_config  # noqa: E402
from closer.domain import Contact, EmailDraft  # noqa: E402
from closer.generation import generate_email  # noqa: E402
from closer.input import load_targets  # noqa: E402
from closer.outreach.workflow import apply_guardrails, handle_contact_action  # noqa: E402


def _contact_label(contact: Contact, index: int) -> str:
    return f"{index}. {contact.company} — {contact.role} ({contact.recipient_email})"


def _init_session() -> None:
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.config = load_config()
        st.session_state.drafts: dict[int, EmailDraft] = {}
        st.session_state.outcomes: dict[int, str] = {}
        _reload_contacts()


def _reload_contacts() -> None:
    config = st.session_state.config
    loaded = load_targets(config.input_path)
    st.session_state.all_contacts = loaded
    st.session_state.contacts = apply_guardrails(loaded, config)
    st.session_state.drafts = {}
    st.session_state.outcomes = {}
    st.session_state.selected_index = 0


def _render_sidebar() -> None:
    config = st.session_state.config
    st.sidebar.title("The Closer")
    st.sidebar.caption("Cold email writer + send bot")

    st.sidebar.markdown("### Settings")
    st.sidebar.write(f"**DRY_RUN:** `{config.dry_run}`")
    st.sidebar.write(f"**Send mode:** `{config.send_mode}`")
    st.sidebar.write(f"**Max per run:** `{config.max_outreach_per_run}`")
    st.sidebar.write(f"**Input:** `{config.input_path}`")
    st.sidebar.write(f"**Log:** `{config.log_path}`")

    if not config.dry_run:
        st.sidebar.error(
            "DRY_RUN is false — choosing Send will deliver real emails via SMTP."
        )
    else:
        st.sidebar.success("DRY_RUN is true — Send/Draft are simulated only.")

    if st.sidebar.button("Reload contacts"):
        st.session_state.config = load_config()
        _reload_contacts()
        st.rerun()

    total = len(st.session_state.get("all_contacts", []))
    batch = len(st.session_state.get("contacts", []))
    st.sidebar.markdown("### Batch")
    st.sidebar.write(f"Loaded: **{total}** | Processing: **{batch}**")

    log_path = Path(config.log_path)
    if log_path.is_file():
        with st.sidebar.expander("Recent log rows"):
            lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            st.code("\n".join(lines[-6:]), language="text")


def _render_contact_picker() -> tuple[Contact, int]:
    contacts: list[Contact] = st.session_state.contacts
    if not contacts:
        st.warning("No valid contacts loaded. Check data/contacts.json.")
        st.stop()

    labels = [_contact_label(c, i) for i, c in enumerate(contacts, start=1)]
    index = st.selectbox(
        "Select outreach target",
        range(len(contacts)),
        format_func=lambda i: labels[i],
        index=min(st.session_state.get("selected_index", 0), len(contacts) - 1),
    )
    st.session_state.selected_index = index
    return contacts[index], index


def _render_preview(contact: Contact, draft: EmailDraft) -> None:
    st.subheader("Preview")
    col1, col2 = st.columns(2)
    col1.metric("Company", contact.company)
    col2.metric("Role", contact.role)
    st.write(f"**To:** {contact.recipient_email}")
    st.write(f"**Recipient name:** {contact.recipient_name or 'there'}")
    st.write(f"**Subject:** {draft.subject}")
    st.metric("Word count", draft.word_count)
    st.text_area("Body", value=draft.body, height=320, disabled=True)


def main() -> None:
    st.set_page_config(page_title="The Closer", page_icon="✉️", layout="wide")
    _init_session()
    _render_sidebar()

    st.title("The Closer")
    st.markdown(
        "Generate personalized cold emails, review them here, then **Send**, "
        "**Draft**, or **Skip**. All actions are logged to your outreach CSV."
    )

    config = st.session_state.config
    contact, index = _render_contact_picker()

    if st.button("Generate email", type="primary"):
        draft = generate_email(contact, config)
        st.session_state.drafts[index] = draft
        st.session_state.outcomes.pop(index, None)
        st.success("Email generated.")

    draft = st.session_state.drafts.get(index)
    if draft is None:
        st.info("Click **Generate email** to create a draft for this contact.")
        return

    _render_preview(contact, draft)

    if index in st.session_state.outcomes:
        st.info(f"Last action: {st.session_state.outcomes[index]}")

    st.markdown("### Confirm action")
    st.caption("Human review required before any delivery (same as CLI).")

    col_skip, col_draft, col_send = st.columns(3)
    with col_skip:
        skip = st.button("Skip", use_container_width=True)
    with col_draft:
        draft_btn = st.button("Draft", use_container_width=True)
    with col_send:
        send_btn = st.button("Send", use_container_width=True, type="primary")

    if skip:
        outcome = handle_contact_action(contact, draft, config, "skip")
        st.session_state.outcomes[index] = outcome.message
        st.warning(outcome.message)

    if draft_btn:
        outcome = handle_contact_action(contact, draft, config, "draft")
        st.session_state.outcomes[index] = outcome.message
        if outcome.log_status == "failed":
            st.error(outcome.message)
        else:
            st.success(outcome.message)

    if send_btn:
        outcome = handle_contact_action(contact, draft, config, "send")
        st.session_state.outcomes[index] = outcome.message
        if outcome.log_status == "failed":
            st.error(outcome.message)
        else:
            st.success(outcome.message)

    with st.expander("Guardrail notes"):
        if not contact.personalization_note:
            st.warning(
                f"No personalization_note for {contact.company} — "
                "using company/role fallback in the template."
            )
        if config.max_outreach_per_run > 5:
            st.warning(
                f"MAX_OUTREACH_PER_RUN={config.max_outreach_per_run} exceeds "
                "recommended demo cap of 5."
            )
        if not config.dry_run and config.smtp_user:
            smtp_local = config.smtp_user.split("@")[0].lower()
            cand = contact.candidate_name.lower()
            first = cand.split()[0] if cand.split() else ""
            if first not in smtp_local and smtp_local not in cand.replace(" ", ""):
                st.warning(
                    f"SMTP_USER ({config.smtp_user}) may not match "
                    f"candidate_name ({contact.candidate_name})."
                )


if __name__ == "__main__":
    main()

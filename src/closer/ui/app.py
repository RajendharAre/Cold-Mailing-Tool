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
from closer.domain import Contact, EmailDraft, count_words  # noqa: E402
from closer.generation import generate_email  # noqa: E402
from closer.generation.generator import (  # noqa: E402
    _resume_candidate_name,
    _summarize_resume,
    enrich_contact_from_job_description,
    load_resume_background_text,
)
from closer.input import extract_resume_text, load_targets  # noqa: E402
from closer.outreach.workflow import apply_guardrails, handle_contact_action  # noqa: E402
from closer.tracking import update_outreach_status  # noqa: E402


def _contact_label(contact: Contact, index: int) -> str:
    return f"{index}. {contact.company} — {contact.role} ({contact.recipient_email})"


def _clear_editable_widget_keys(index: int | None = None) -> None:
    """Drop Streamlit widget keys so regenerated drafts render fresh values."""
    for key in list(st.session_state.keys()):
        if key.startswith("editable_"):
            if index is None or key.endswith(f"_{index}"):
                del st.session_state[key]


def _init_session() -> None:
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.config = load_config()
        st.session_state.drafts: dict[int, EmailDraft] = {}
        st.session_state.outcomes: dict[int, str] = {}
        st.session_state.current_contact: Contact | None = None
        _reload_contacts()


def _reload_contacts() -> None:
    config = st.session_state.config
    loaded = load_targets(config.input_path)
    st.session_state.all_contacts = loaded
    st.session_state.contacts = apply_guardrails(loaded, config)
    st.session_state.drafts = {}
    st.session_state.outcomes = {}
    st.session_state.selected_index = 0
    _clear_editable_widget_keys()


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


def _blank_contact() -> Contact:
    """A fresh, empty outreach target for the JD-first flow."""
    resume_text = load_resume_background_text()
    return Contact(
        recipient_email="",
        company="",
        role="",
        candidate_name=_resume_candidate_name(resume_text) or "Your Name",
        candidate_background="",
    )


def _form_signature(contact: Contact) -> str:
    return "|".join(
        [
            contact.recipient_email or "",
            contact.company or "",
            contact.role or "",
            contact.candidate_name or "",
            contact.job_url or "",
        ]
    )


def _seed_form_from_contact(contact: Contact) -> None:
    """Seed the input widgets once when the selected outreach target changes."""
    signature = _form_signature(contact)
    if st.session_state.get("input_signature") == signature:
        return
    st.session_state.input_signature = signature
    st.session_state.input_recipient_email = contact.recipient_email
    st.session_state.input_recipient_name = contact.recipient_name or ""
    st.session_state.input_job_link = contact.job_url or ""
    st.session_state.input_company = contact.company or ""
    st.session_state.input_role = contact.role or ""
    st.session_state.input_job_description = contact.job_description or ""
    st.session_state.input_personalization_note = contact.personalization_note or ""
    st.session_state.input_candidate_name = contact.candidate_name
    st.session_state.input_last_inferred_jd = ""
    st.session_state.input_company_inferred = False
    st.session_state.input_role_inferred = False
    st.session_state.input_resume_text = None
    if "input_resume_upload" in st.session_state:
        del st.session_state["input_resume_upload"]


def _infer_company_role_from_jd(config) -> None:
    """Auto-fill company/role from a pasted job description without clobbering edits."""
    jd = st.session_state.get("input_job_description", "")
    last_inferred = st.session_state.get("input_last_inferred_jd")
    if not jd or jd == last_inferred:
        return

    probe = Contact(
        recipient_email=st.session_state.get("input_recipient_email", ""),
        company="",
        role="",
        candidate_name=st.session_state.get("input_candidate_name", ""),
        candidate_background="",
        job_description=jd,
    )
    enriched = enrich_contact_from_job_description(probe, config)

    candidates = [
        ("input_company", enriched.company, "input_company_inferred"),
        ("input_role", enriched.role, "input_role_inferred"),
    ]
    for key, value, flag in candidates:
        current = st.session_state.get(key, "")
        was_inferred = st.session_state.get(flag, False)
        if (
            value
            and value not in ("Unknown Company", "Unknown Role")
            and (not current or was_inferred)
        ):
            st.session_state[key] = value
            st.session_state[flag] = True
        else:
            st.session_state[flag] = False

    st.session_state.input_last_inferred_jd = jd


def _render_contact_picker() -> tuple[Contact, int]:
    contacts: list[Contact] = st.session_state.contacts
    if not contacts:
        st.warning("No valid contacts loaded. Check data/contacts.json.")
        st.stop()

    labels = ["➕ New outreach (start from scratch)"] + [
        _contact_label(c, i) for i, c in enumerate(contacts, start=1)
    ]
    index = st.selectbox(
        "Outreach target",
        range(len(contacts) + 1),
        format_func=lambda i: labels[i],
        index=0,
    )
    if index == 0:
        return _blank_contact(), -1
    return contacts[index - 1], index


def _render_input_form(contact: Contact, config) -> Contact:
    _seed_form_from_contact(contact)
    _infer_company_role_from_jd(config)

    st.subheader("Core outreach details")
    st.caption(
        "Paste the job description and job link. Company and role are inferred from "
        "the JD and can be edited here."
    )

    recipient_email = st.text_input("Recipient email *", key="input_recipient_email")
    recipient_name = st.text_input("Recipient name", key="input_recipient_name")
    job_link = st.text_input("Job link / Job ID", key="input_job_link")
    company = st.text_input("Company", key="input_company")
    role = st.text_input("Role", key="input_role")
    job_description = st.text_area(
        "Job description",
        key="input_job_description",
        height=140,
    )
    personalization_note = st.text_area(
        "Personalization note (optional)",
        key="input_personalization_note",
        height=80,
    )
    candidate_name = st.text_input("Your name (signature)", key="input_candidate_name")

    st.markdown("### Resume")
    st.caption(
        "Attach a resume (PDF, Markdown, or TXT) for this application, or use the "
        "default resume_background.md."
    )
    uploaded = st.file_uploader(
        "Attach resume",
        type=["pdf", "md", "markdown", "txt"],
        key="input_resume_upload",
    )
    if uploaded is not None:
        try:
            resume_text = extract_resume_text(uploaded.name, uploaded.getvalue())
        except RuntimeError as exc:
            st.error(str(exc))
            resume_text = ""
        if resume_text:
            st.session_state["input_resume_text"] = resume_text
            st.success(
                f"Loaded resume from {uploaded.name} "
                f"({len(resume_text.split())} words)."
            )
        else:
            st.warning("Could not read the uploaded file; keeping the default resume.")

    if st.button("Use default resume (resume_background.md)"):
        st.session_state["input_resume_text"] = None
        if "input_resume_upload" in st.session_state:
            del st.session_state["input_resume_upload"]
        st.rerun()

    resume_uploaded = st.session_state.get("input_resume_text") is not None
    resume_text = st.session_state.get("input_resume_text") or load_resume_background_text()
    resume_summary = _summarize_resume(resume_text)
    if resume_summary:
        st.caption(f"Resume summary used for personalization: “{resume_summary}”")

    return Contact(
        recipient_email=recipient_email.strip(),
        company=company.strip() or "Unknown Company",
        role=role.strip() or "Unknown Role",
        candidate_name=candidate_name.strip() or contact.candidate_name,
        candidate_background=(
            resume_summary if resume_uploaded else (contact.candidate_background or resume_summary)
        ),
        recipient_name=recipient_name.strip() or None,
        job_url=job_link.strip() or None,
        portfolio_url=contact.portfolio_url,
        personalization_note=personalization_note.strip() or None,
        linkedin_url=contact.linkedin_url,
        resume_link=contact.resume_link,
        job_description=job_description.strip() or None,
        resume_context=resume_summary or None,
    )


def _render_preview(contact: Contact, draft: EmailDraft, index: int) -> EmailDraft:
    st.subheader("Preview")
    col1, col2 = st.columns(2)
    col1.metric("Company", contact.company)
    col2.metric("Role", contact.role)
    st.write(f"**To:** {contact.recipient_email}")

    subject_key = f"editable_subject_{index}"
    body_key = f"editable_body_{index}"
    recipient_key = f"editable_recipient_name_{index}"

    subject_value = st.text_input("Subject", value=draft.subject, key=subject_key)
    recipient_name_value = st.text_input(
        "Recipient name", value=contact.recipient_name or "there", key=recipient_key
    )
    body_value = st.text_area("Body", value=draft.body, height=320, key=body_key)

    edited_draft = EmailDraft(
        subject=subject_value,
        body=body_value,
        word_count=count_words(body_value),
    )
    return edited_draft


def _render_reply_tracking(config) -> None:
    st.markdown("### Track replies")
    st.caption(
        "Update a recipient's status in Google Sheets "
        "(sent → awaiting reply / replied / no reply)."
    )
    with st.form("track_reply_form"):
        email = st.text_input("Recipient email", key="track_email")
        status = st.selectbox(
            "Status",
            ["awaiting reply", "replied", "no reply"],
            key="track_status",
        )
        submitted = st.form_submit_button("Update status in Sheets")

    if submitted:
        if not email.strip():
            st.warning("Enter a recipient email.")
            return
        result = update_outreach_status(email.strip(), status, config)
        if result.get("enabled") and result.get("status") != "no_match":
            st.success(result["message"])
        else:
            st.error(result["message"])


def main() -> None:
    st.set_page_config(page_title="The Closer", page_icon="✉️", layout="wide")
    _init_session()
    _render_sidebar()

    st.title("The Closer")
    st.markdown(
        "Paste a **job description** and **job link**, attach your resume, and the "
        "AI drafts a short personalized email. Review it here, then **Send**, "
        "**Draft**, or **Skip** — all actions are logged to your outreach CSV and "
        "Google Sheets."
    )

    config = st.session_state.config
    contact, index = _render_contact_picker()
    contact = _render_input_form(contact, config)
    st.session_state.current_contact = contact

    missing_email = not contact.recipient_email.strip()
    if missing_email:
        st.warning("Enter the recipient email before generating.")

    if st.button("Generate email", type="primary", disabled=missing_email):
        _clear_editable_widget_keys(index)
        draft = generate_email(contact, config)
        st.session_state.drafts[index] = draft
        st.session_state.outcomes.pop(index, None)
        st.success("Email generated.")

    st.divider()
    _render_reply_tracking(config)

    draft = st.session_state.drafts.get(index)
    if draft is None:
        st.info("Click **Generate email** to create a draft for this contact.")
        return

    draft = _render_preview(contact, draft, index)
    st.session_state.drafts[index] = draft

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
            smtp_local = config.smtp_user.split("@")[0].lower().replace(".", "")
            cand = contact.candidate_name.lower()
            first = cand.split()[0] if cand.split() else ""
            if first not in smtp_local and smtp_local not in cand.replace(" ", ""):
                st.warning(
                    f"SMTP_USER ({config.smtp_user}) may not match "
                    f"candidate_name ({contact.candidate_name})."
                )


if __name__ == "__main__":
    main()

"""Cold-email generator with deterministic fallback and optional LLM provider support."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Callable

import requests

from closer.config import AppConfig, load_config
from closer.domain import Contact, EmailDraft, count_words
from closer.input import load_targets

_WORD_LIMIT = 150


def generate_email(contact: Contact, config: AppConfig) -> EmailDraft:
    """Generate subject and body using an LLM provider when available."""
    contact = enrich_contact_from_job_description(contact, config)
    provider_output = _maybe_generate_with_provider(contact, config)
    if provider_output is not None:
        subject, body = provider_output
        word_count = count_words(body)
        if _provider_output_is_usable(body, word_count, contact):
            return EmailDraft(subject=subject, body=body, word_count=word_count)
        print(
            "[email_generator] provider output failed quality checks; "
            "using deterministic fallback",
            file=sys.stderr,
        )

    print(
        "[email_generator] provider output unavailable; using deterministic fallback",
        file=sys.stderr,
    )

    subject = _build_subject(contact)
    body = _build_body(contact)
    word_count = count_words(body)

    if word_count > _WORD_LIMIT:
        print(
            f"[email_generator] warning: generated {word_count} words "
            f"(limit {_WORD_LIMIT}) for {contact.recipient_email}",
            file=sys.stderr,
        )

    return EmailDraft(subject=subject, body=body, word_count=word_count)


def _provider_output_is_usable(body: str, word_count: int, contact: Contact) -> bool:
    """Mirror the project's quality bar so provider output never ships raw templates."""
    if word_count > _WORD_LIMIT:
        return False
    if not body or _has_unresolved_placeholders(body):
        return False
    if (
        contact.company
        and contact.company not in _PLACEHOLDER_COMPANY
        and not _company_appears_in_body(contact.company, body)
    ):
        return False
    if (
        contact.role
        and contact.role not in _PLACEHOLDER_ROLE
        and not _role_appears_in_body(contact.role, body)
    ):
        return False
    return True


_PLACEHOLDER_COMPANY = ("Unknown Company",)
_PLACEHOLDER_ROLE = ("Unknown Role",)


def _has_unresolved_placeholders(text: str) -> bool:
    return bool(
        re.search(r"\{[a-zA-Z_]+\}|\[your name\]", text, flags=re.IGNORECASE)
    )


_GENERIC_ROLE_WORDS = {
    "intern",
    "internship",
    "engineer",
    "engineering",
    "developer",
    "analyst",
    "manager",
    "role",
}


def _company_appears_in_body(company: str, body: str) -> bool:
    company_norm = re.sub(r"[^a-z0-9]+", " ", company.lower()).strip()
    body_norm = re.sub(r"[^a-z0-9]+", " ", body.lower())
    if not company_norm:
        return True
    if company_norm in body_norm:
        return True
    first_word = company_norm.split()[0]
    return len(first_word) > 2 and first_word in body_norm.split()


def _role_appears_in_body(role: str, body: str) -> bool:
    body_norm = re.sub(r"[^a-z0-9]+", " ", body.lower())
    role_norm = re.sub(r"[^a-z0-9]+", " ", role.lower()).strip()
    if not role_norm:
        return True
    if role_norm in body_norm:
        return True
    role_words = {
        word
        for word in role_norm.split()
        if word not in _GENERIC_ROLE_WORDS
    }
    if not role_words:
        role_words = set(role_norm.split())
    body_words = set(body_norm.split())
    matches = role_words & body_words
    return len(matches) >= max(1, min(2, len(role_words)))


def enrich_contact_from_job_description(contact: Contact, config: AppConfig) -> Contact:
    """Infer company and role from the job description when missing."""
    if not contact.job_description:
        return contact

    text = contact.job_description.strip()
    company, role = contact.company, contact.role
    if not company or not role:
        inferred_company, inferred_role = _infer_company_and_role_with_provider(
            contact, config
        )
        if inferred_company and not _is_plausible_company(inferred_company):
            inferred_company = None
        if inferred_role and not _is_plausible_role(inferred_role):
            inferred_role = None
        company = company or inferred_company or _extract_company(text)
        role = role or inferred_role or _extract_role(text)

    resume_summary = _summarize_resume(load_resume_background_text())
    candidate_background = contact.candidate_background or resume_summary

    return Contact(
        recipient_email=contact.recipient_email,
        company=company or "Unknown Company",
        role=role or "Unknown Role",
        candidate_name=contact.candidate_name,
        candidate_background=candidate_background,
        recipient_name=contact.recipient_name,
        job_url=contact.job_url,
        portfolio_url=contact.portfolio_url,
        personalization_note=contact.personalization_note,
        linkedin_url=contact.linkedin_url,
        resume_link=contact.resume_link,
        job_description=contact.job_description,
        resume_context=contact.resume_context,
    )


def load_resume_background_text() -> str:
    """Load resume background text from a markdown file if present."""
    repo_root = Path(__file__).resolve().parents[3]
    candidates = [repo_root / "resume_background.md", repo_root / "Resume_Background.md"]
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    return ""


def _summarize_resume(text: str) -> str:
    """Return a one-sentence summary from the resume background file."""
    if not text:
        return ""
    summary_match = re.search(
        r"^##\s+Summary\s*\n(.+?)(?=\n##|\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    summary = summary_match.group(1).strip() if summary_match else text.strip()
    return _first_sentence(summary)


def _resume_candidate_name(text: str) -> str | None:
    """Return the candidate name from a resume markdown file, if present."""
    match = re.search(
        r"(?im)^\s*\**\s*name\s*:\s*\**\s*([A-Za-z][A-Za-z .'-]*)",
        text,
    )
    return match.group(1).strip() if match else None


def _first_sentence(text: str) -> str:
    """Return the first sentence or line of a text, skipping raw markdown and labels."""
    match = re.search(r"[^.!?\n]*[.!?]?", text.strip())
    sentence = match.group(0).strip() if match else text.strip()
    return re.sub(
        r"^\s*(?:job title|role|position|title|company|about the role|role overview|"
        r"job description|job summary|description|jd)\s*:\s*",
        "",
        sentence,
        flags=re.IGNORECASE,
    ).strip()


def _resolve_api_key(config: AppConfig) -> str | None:
    """Return the API key for the active provider only, never another provider's key."""
    if config.llm_provider == "gemini":
        return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if config.llm_provider == "groq":
        return config.groq_api_key or os.getenv("GROQ_API_KEY")
    return None


def _infer_company_and_role_with_provider(
    contact: Contact, config: AppConfig
) -> tuple[str | None, str | None]:
    """Use the active provider to infer company and role from the JD when possible."""
    if config.llm_provider not in {"groq", "gemini"}:
        return None, None

    api_key = _resolve_api_key(config)
    if not api_key:
        return None, None

    prompt = (
        "Infer the company name and job role from the following job description. "
        "Return JSON with keys company and role. "
        f"Job description: {contact.job_description or ''}"
    )

    if config.llm_provider == "groq":
        payload = {
            "messages": [
                {"role": "system", "content": "You infer company and role from job descriptions."},
                {"role": "user", "content": prompt},
            ],
            "model": "llama-3.1-8b-instant",
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=20,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except Exception:
            return None, None
    else:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
            f"?key={api_key}"
        )
        try:
            response = requests.post(url, json=payload, timeout=20)
            response.raise_for_status()
            content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return None, None

    cleaned = content.strip()
    if not cleaned:
        return None, None

    try:
        data = json.loads(cleaned)
    except Exception:
        data = None

    if isinstance(data, dict):
        company = data.get("company") or data.get("Company") or ""
        role = data.get("role") or data.get("Role") or ""
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        company = data[0].get("company") or data[0].get("Company") or ""
        role = data[0].get("role") or data[0].get("Role") or ""
    else:
        company = re.search(r'"company"\s*:\s*"([^"]+)"', cleaned)
        role = re.search(r'"role"\s*:\s*"([^"]+)"', cleaned)
        company = company.group(1).strip() if company else ""
        role = role.group(1).strip() if role else ""

    company = re.sub(r"\s+", " ", str(company).strip()) if company else ""
    role = re.sub(r"\s+", " ", str(role).strip()) if role else ""
    role = role.replace(",", " ").strip()

    if company and not _is_plausible_company(company):
        company = ""
    if role and not _is_plausible_role(role):
        role = ""

    return (company or None, role or None)


def _is_helpful_inference(value: str) -> bool:
    """Reject model responses like 'Unknown (cannot be inferred from the JD)'."""
    if re.search(
        r"\b(?:unknown|cannot|can't|unable|not provided|not found|not specified|"
        r"not stated|not given|not mentioned|n/a|na|none|could not|couldn't|"
        r"generic|placeholder|inferred|sample|example|standard)\b",
        value.lower(),
    ):
        return False
    if "(" in value or ")" in value:
        return False
    return True


def _is_plausible_company(value: str) -> bool:
    return _is_helpful_inference(value) and len(value.split()) <= 5


def _is_plausible_role(value: str) -> bool:
    return _is_helpful_inference(value) and len(value.split()) <= 8


def _extract_company(text: str) -> str | None:
    explicit = re.search(r"\babout\s+([^\n]+)", text, flags=re.IGNORECASE)
    if explicit:
        candidate = explicit.group(1).strip()
        candidate = re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9]+$", "", candidate)
        return candidate.rstrip(".")

    patterns = [
        r"\bat\s+([A-Z][A-Za-z0-9&.\-]*(?:\s+[A-Z][A-Za-z0-9&.\-]*)*)",
        r"\bfor\s+([A-Z][A-Za-z0-9&.\-]*(?:\s+[A-Z][A-Za-z0-9&.\-]*)*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            candidate = re.sub(
                r"\s+(to|for|and|with|build|develop|working|join|hiring)\b.*$",
                "",
                candidate,
                flags=re.IGNORECASE,
            )
            candidate = candidate.strip()
            if _looks_like_company(candidate):
                return candidate
    return None


_COMPANY_UNLIKE_WORDS = {
    "manager",
    "management",
    "developer",
    "engineer",
    "intern",
    "internship",
    "analyst",
    "position",
    "role",
    "job",
    "experience",
    "office",
    "team",
    "candidate",
    "applicant",
    "skills",
    "qualifications",
    "responsibilities",
}


def _looks_like_company(candidate: str) -> bool:
    words = {
        word.lower()
        for word in re.findall(r"[a-zA-Z]+", candidate)
    }
    if not words:
        return False
    return not bool(words & _COMPANY_UNLIKE_WORDS)


def _extract_role(text: str) -> str | None:
    title_match = re.search(
        r"^\s*(Software Engineer(?:,\s*Intern)?|Backend Intern|Frontend Intern|Data Scientist|Machine Learning Intern|Product Manager|Research Intern|Operations Intern|Developer Intern|Intern|Engineer|Analyst)\b",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if title_match:
        title = title_match.group(1).strip()
        title = re.sub(r"\s+at\s+.*$", "", title, flags=re.IGNORECASE)
        title = title.replace(",", " ")
        title = re.sub(r"[^A-Za-z0-9]+", " ", title).strip()
        title = re.sub(r"\s+", " ", title)
        return re.sub(r"\s+for\s+.*$", "", title, flags=re.IGNORECASE).strip()

    patterns = [
        r"(Software Engineer|Backend Intern|Frontend Intern|Data Scientist|Machine Learning Intern|Product Manager|Research Intern|Operations Intern|Developer Intern|Intern|Engineer|Analyst)[^\.\n]*",
        r"hiring\s+(?:a|an)\s+([^\.\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            role = match.group(1).strip()
            return re.sub(r"\s+for\s+.*$", "", role, flags=re.IGNORECASE).strip()
    return None


def _maybe_generate_with_provider(
    contact: Contact, config: AppConfig
) -> tuple[str, str] | None:
    """Return provider-generated subject/body when a configured provider is available."""
    if config.llm_provider not in {"groq", "gemini"}:
        return None

    api_key = _resolve_api_key(config)
    if not api_key:
        return None

    if config.llm_provider == "groq":
        return _call_groq_api(contact, api_key)
    return _call_gemini_api(contact, api_key)


def _call_groq_api(contact: Contact, api_key: str) -> tuple[str, str] | None:
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "You write concise personalized cold emails.",
            },
            {
                "role": "user",
                "content": _build_provider_prompt(contact),
            },
        ],
        "model": "llama-3.1-8b-instant",
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
    except Exception:
        return None

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except Exception:
        return None
    return _parse_provider_output(content)


def _call_gemini_api(contact: Contact, api_key: str) -> tuple[str, str] | None:
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": _build_provider_prompt(contact)},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.3},
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        f"?key={api_key}"
    )
    try:
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
    except Exception:
        return None

    try:
        content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None
    return _parse_provider_output(content)


def _build_provider_prompt(contact: Contact) -> str:
    return (
        "Write a concise personalized cold email draft for a job application. "
        f"Recipient email: {contact.recipient_email}. "
        f"Recipient name: {contact.recipient_name or 'there'}. "
        f"Company: {contact.company}. "
        f"Role: {contact.role}. "
        f"Job description: {contact.job_description or ''}. "
        f"Resume background: {contact.candidate_background}. "
        f"Personalization note: {contact.personalization_note or ''}. "
        f"Candidate name (sign the email with this): {contact.candidate_name}. "
        "Keep the body under 150 words. "
        "Reply with ONLY valid JSON with keys subject and body. "
        "Never use placeholders like {company}, {role}, or [Your Name]."
    )


def _parse_provider_output(content: str) -> tuple[str, str] | None:
    cleaned = content.strip()
    if not cleaned:
        return None

    try:
        data = json.loads(cleaned)
    except Exception:
        data = None

    subject = ""
    body = ""

    if isinstance(data, dict):
        subject = data.get("subject") or data.get("Subject") or ""
        body = data.get("body") or data.get("Body") or ""
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        subject = data[0].get("subject") or data[0].get("Subject") or ""
        body = data[0].get("body") or data[0].get("Body") or ""

    if not (subject and body):
        flat = _unescape_provider_escapes(cleaned)
        subject_match = re.search(
            r"subject\s*[:=]\s*(.+)", flat, flags=re.IGNORECASE
        )
        body_match = re.search(
            r"body\s*[:=]\s*(.+)", flat, flags=re.DOTALL | re.IGNORECASE
        )
        if subject_match and body_match:
            subject = _clean_provider_fragment(subject_match.group(1))
            body = _clean_provider_fragment(body_match.group(1))

    if not (subject and body) and (
        "subject" in cleaned.lower() and "body" in cleaned.lower()
    ):
        subject_match = re.search(r'"subject"\s*:\s*"([^"]+)"', cleaned)
        body_match = re.search(r'"body"\s*:\s*"([^"]+)"', cleaned)
        if subject_match and body_match:
            subject = subject_match.group(1).strip()
            body = body_match.group(1).strip()

    if not (subject and body):
        return None

    return (
        _unescape_provider_escapes(str(subject).strip()),
        _unescape_provider_escapes(str(body).strip()),
    )


def _unescape_provider_escapes(text: str) -> str:
    """Turn literal '\\n' / '\\t' emitted by the model into real characters."""
    return text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", " ")


def _clean_provider_fragment(text: str) -> str:
    """Strip leading markers and surrounding quotes, leaving body text untouched."""
    text = re.sub(r"^[\-\s*]+", "", text).strip()
    quote_match = re.match(
        r"^f?([\"'])(.*)\1[,;:\s]*$", text, flags=re.DOTALL | re.IGNORECASE
    )
    if quote_match:
        text = quote_match.group(2)
    return text.strip()


def _build_subject(contact: Contact) -> str:
    # Optional variant: mention company when no explicit personalization note exists.
    if contact.personalization_note:
        return f"Quick note on the {contact.role} role"
    return f"Interest in {contact.role} at {contact.company}"


def _build_body(contact: Contact) -> str:
    recipient_name = contact.recipient_name or "there"
    hook = _build_personalization_hook(contact)
    sign_off_lines = [contact.candidate_name]
    if contact.portfolio_url:
        sign_off_lines.append(contact.portfolio_url)

    lines = [
        f"Hi {recipient_name},",
        "",
        hook,
        "",
        (
            f"I'm {contact.candidate_name}, and I've been building projects around "
            f"{contact.candidate_background}."
        ),
    ]

    if contact.job_description:
        lines.append(
            f"The role stood out because it focuses on {_first_sentence(contact.job_description)}."
        )

    if contact.resume_context:
        lines.append(
            f"My recent experience with {contact.resume_context} aligns well with that work."
        )

    lines.extend(
        [
            "",
            (
                "Would you be open to a quick look at my profile or pointing me to "
                "the right person to connect with?"
            ),
            "",
            "Best,",
            *sign_off_lines,
        ]
    )
    return "\n".join(lines)


def _build_personalization_hook(contact: Contact) -> str:
    if contact.personalization_note:
        return (
            f"I noticed {contact.company} is hiring for {contact.role}. "
            f"{contact.personalization_note}"
        )
    return (
        f"I noticed {contact.company} is hiring for {contact.role}, and that "
        "combination of domain and role is exactly what I have been preparing for."
    )


if __name__ == "__main__":
    cfg = load_config()
    contacts = load_targets(cfg.input_path)
    if not contacts:
        print("No contacts available to generate email.")
        raise SystemExit(0)

    draft = generate_email(contacts[0], cfg)
    print(f"Recipient: {contacts[0].recipient_email}")
    print(f"Subject: {draft.subject}")
    print(f"Word count: {draft.word_count}")
    print()
    print(draft.body)

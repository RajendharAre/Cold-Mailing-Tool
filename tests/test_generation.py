"""Tests for cold email generation (Phase 8)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from closer.config import AppConfig, load_config  # noqa: E402
from closer.domain import Contact  # noqa: E402
from closer.generation import generate_email  # noqa: E402
import closer.generation.generator as generator_module  # noqa: E402


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user=None,
        smtp_password=None,
        sender_name="Alex Kim",
        dry_run=True,
        send_mode="draft",
        max_outreach_per_run=5,
        input_path=ROOT / "data" / "contacts.json",
        log_path=ROOT / "logs" / "outreach_log.csv",
        groq_api_key=None,
        llm_provider="groq",
        llm_model=None,
    )


@pytest.fixture
def contact() -> Contact:
    return Contact(
        recipient_email="test@example.com",
        company="Acme AI",
        role="Backend Intern",
        candidate_name="Alex Kim",
        candidate_background="Python and automation",
        personalization_note="Recently launched a new API platform.",
        recipient_name="Jamie",
    )


def test_generate_email_has_subject_and_body(config: AppConfig, contact: Contact) -> None:
    draft = generate_email(contact, config)
    assert draft.subject.strip()
    assert draft.body.strip()
    assert "Acme AI" in draft.body
    assert "Backend Intern" in draft.body


def test_generate_email_word_count_within_limit(
    config: AppConfig, contact: Contact
) -> None:
    draft = generate_email(contact, config)
    assert draft.word_count <= 150
    assert draft.word_count > 0


def test_fallback_hook_without_personalization_note(config: AppConfig) -> None:
    contact = Contact(
        recipient_email="test@example.com",
        company="Nimbus Health",
        role="SWE Intern",
        candidate_name="Alex Kim",
        candidate_background="data workflows",
    )
    draft = generate_email(contact, config)
    assert "Nimbus Health" in draft.body
    assert "SWE Intern" in draft.body


def test_generate_email_uses_job_description_and_resume_context(
    config: AppConfig,
) -> None:
    contact = Contact(
        recipient_email="test@example.com",
        company="OpenAI",
        role="Applied AI Intern",
        candidate_name="Alex Kim",
        candidate_background="Python automation and LLM workflows",
        job_description="Build internal tools for prompt evaluation and data labeling.",
        resume_context="Built a Python pipeline that scored candidate outreach emails.",
    )
    draft = generate_email(contact, config)
    assert "Build internal tools" in draft.body
    assert "Python pipeline" in draft.body


def test_generate_email_uses_provider_output_when_available(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    config.llm_provider = "gemini"
    config.groq_api_key = "test-key"

    monkeypatch.setattr(
        generator_module,
        "_maybe_generate_with_provider",
        lambda contact, cfg: ("Gemini subject", "Gemini body for the ML Intern role at Acme"),
    )

    draft = generate_email(
        Contact(
            recipient_email="test@example.com",
            company="Acme",
            role="ML Intern",
            candidate_name="Alex Kim",
            candidate_background="ML pipelines",
        ),
        config,
    )

    assert draft.subject == "Gemini subject"
    assert draft.body == "Gemini body for the ML Intern role at Acme"


def test_load_config_auto_selects_gemini_when_key_is_available(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("DRY_RUN=true\nSEND_MODE=draft\n", encoding="utf-8")

    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")

    config = load_config(env_file=env_path)

    assert config.llm_provider == "gemini"


def test_groq_provider_uses_groq_key_when_configured(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    config.llm_provider = "groq"
    config.groq_api_key = "groq-test-key"
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")

    called = {}

    def fake_call(contact, api_key):
        called["api_key"] = api_key
        return ("Groq subject", "Groq body for the ML Intern role at Acme")

    monkeypatch.setattr(generator_module, "_call_groq_api", fake_call)

    draft = generate_email(
        Contact(
            recipient_email="test@example.com",
            company="Acme",
            role="ML Intern",
            candidate_name="Alex Kim",
            candidate_background="ML pipelines",
        ),
        config,
    )

    assert draft.subject == "Groq subject"
    assert draft.body == "Groq body for the ML Intern role at Acme"
    assert called["api_key"] == "groq-test-key"


def test_groq_provider_does_not_leak_gemini_key(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    config.llm_provider = "groq"
    config.groq_api_key = None
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    called = {"invoked": False}

    def fake_call(contact, api_key):
        called["invoked"] = True
        return ("Groq subject", "Groq body")

    monkeypatch.setattr(generator_module, "_call_groq_api", fake_call)

    draft = generate_email(
        Contact(
            recipient_email="test@example.com",
            company="Acme",
            role="ML Intern",
            candidate_name="Alex Kim",
            candidate_background="ML pipelines",
        ),
        config,
    )

    assert called["invoked"] is False
    assert draft.body.strip()


def test_gemini_provider_does_not_leak_groq_key(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    config.llm_provider = "gemini"
    config.groq_api_key = "groq-test-key"
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    called = {"invoked": False}

    def fake_call(contact, api_key):
        called["invoked"] = True
        return ("Gemini subject", "Gemini body")

    monkeypatch.setattr(generator_module, "_call_gemini_api", fake_call)

    generate_email(
        Contact(
            recipient_email="test@example.com",
            company="Acme",
            role="ML Intern",
            candidate_name="Alex Kim",
            candidate_background="ML pipelines",
        ),
        config,
    )

    assert called["invoked"] is False


def test_enrich_contact_from_job_description_fills_company_and_role(
    config: AppConfig,
) -> None:
    contact = Contact(
        recipient_email="test@example.com",
        company="",
        role="",
        candidate_name="Alex Kim",
        candidate_background="",
        job_description=(
            "We are hiring a Backend Intern at Acme Labs to build internal APIs."
        ),
    )

    resolved = generator_module.enrich_contact_from_job_description(contact, config)

    assert resolved.company == "Acme Labs"
    assert resolved.role == "Backend Intern"


def test_extract_company_and_role_from_stripe_internship_jd() -> None:
    jd = """Software Engineer, Intern

Who we are
About Stripe
Stripe is a financial infrastructure platform for businesses.

What you'll do
Every internship at Stripe centers around a real project.
"""

    assert generator_module._extract_company(jd) == "Stripe"
    assert generator_module._extract_role(jd) == "Software Engineer Intern"


def test_enrich_contact_prefers_provider_inference_over_regex_fallback(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    contact = Contact(
        recipient_email="test@example.com",
        company="",
        role="",
        candidate_name="Alex Kim",
        candidate_background="",
        job_description="We are hiring a Backend Intern at Acme Labs to build internal APIs.",
    )

    monkeypatch.setattr(
        generator_module,
        "_infer_company_and_role_with_provider",
        lambda _contact, _cfg: ("Acme Labs", "Backend Intern"),
    )
    monkeypatch.setattr(generator_module, "_extract_company", lambda _text: "Wrong")
    monkeypatch.setattr(generator_module, "_extract_role", lambda _text: "Wrong")

    resolved = generator_module.enrich_contact_from_job_description(contact, config)

    assert resolved.company == "Acme Labs"
    assert resolved.role == "Backend Intern"


def test_enrich_contact_preserves_existing_company_and_role(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    contact = Contact(
        recipient_email="test@example.com",
        company="Acme AI",
        role="Backend Intern",
        candidate_name="Alex Kim",
        candidate_background="Python automation",
        job_description="We are hiring a Software Engineer at Google to build internal APIs.",
    )

    monkeypatch.setattr(
        generator_module,
        "_infer_company_and_role_with_provider",
        lambda _contact, _cfg: ("Google", "Software Engineer"),
    )

    resolved = generator_module.enrich_contact_from_job_description(contact, config)

    assert resolved.company == "Acme AI"
    assert resolved.role == "Backend Intern"


def test_resume_background_file_is_loaded_when_available(config: AppConfig) -> None:
    text = generator_module.load_resume_background_text()

    assert text.strip()
    assert "skill" in text.lower() or "experience" in text.lower()


def test_resume_background_is_structured_for_ai_use(config: AppConfig) -> None:
    text = generator_module.load_resume_background_text()

    assert "profile" in text.lower() or "summary" in text.lower()
    assert "python" in text.lower()
    assert "algoview" in text.lower() or "sentxstock" in text.lower()


def test_parse_provider_output_preserves_multiline_body() -> None:
    result = generator_module._parse_provider_output(
        "subject: Quick note\nbody: Hi there,\n\nBest,\nAlex"
    )

    assert result == ("Quick note", "Hi there,\n\nBest,\nAlex")


def test_parse_provider_output_unescapes_literal_newlines() -> None:
    result = generator_module._parse_provider_output(
        "subject: Quick note\\nbody: Hi Priya,\\n\\nI am writing about the role.\\n\\nBest,\\nAlex"
    )

    assert result == ("Quick note", "Hi Priya,\n\nI am writing about the role.\n\nBest,\nAlex")


def test_extract_role_does_not_mangle_for_substring() -> None:
    assert (
        generator_module._extract_role("hiring a UX Researcher for the design team")
        == "UX Researcher"
    )


def test_provider_output_with_unresolved_placeholders_falls_back(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        generator_module,
        "_maybe_generate_with_provider",
        lambda _contact, _cfg: ("subject", "body with {company} placeholder"),
    )

    draft = generate_email(
        Contact(
            recipient_email="test@example.com",
            company="Acme AI",
            role="Backend Intern",
            candidate_name="Alex Kim",
            candidate_background="Python",
        ),
        config,
    )

    assert "Acme AI" in draft.body
    assert "{" not in draft.body


def test_provider_output_with_template_signoff_falls_back(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        generator_module,
        "_maybe_generate_with_provider",
        lambda _contact, _cfg: ("subject", "body for the Backend Intern role at Acme AI\n\n[Your Name]"),
    )

    draft = generate_email(
        Contact(
            recipient_email="test@example.com",
            company="Acme AI",
            role="Backend Intern",
            candidate_name="Alex Kim",
            candidate_background="Python",
        ),
        config,
    )

    assert "[Your Name]" not in draft.body


def test_provider_output_over_word_limit_falls_back(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        generator_module,
        "_maybe_generate_with_provider",
        lambda _contact, _cfg: ("subject", "word " * 200),
    )

    draft = generate_email(
        Contact(
            recipient_email="test@example.com",
            company="Acme",
            role="ML Intern",
            candidate_name="Alex Kim",
            candidate_background="ML",
        ),
        config,
    )

    assert draft.word_count <= 150


def test_clean_provider_fragment_handles_quotes_and_fstrings() -> None:
    assert generator_module._clean_provider_fragment('f"Hello world"') == "Hello world"
    assert generator_module._clean_provider_fragment('"Hello world",') == "Hello world"
    assert generator_module._clean_provider_fragment("- Hello world") == "Hello world"


def test_provider_prompt_includes_candidate_name(config: AppConfig) -> None:
    contact = Contact(
        recipient_email="test@example.com",
        company="Acme",
        role="ML Intern",
        candidate_name="Alex Kim",
        candidate_background="ML pipelines",
    )
    prompt = generator_module._build_provider_prompt(contact)
    assert "Alex Kim" in prompt


def test_role_appears_in_body_accepts_paraphrased_role() -> None:
    assert generator_module._role_appears_in_body(
        "Backend Engineering Intern", "I would love to join your Backend Engineering team"
    )
    assert generator_module._role_appears_in_body(
        "Software Engineer Intern", "applying for a software engineering internship"
    )
    assert not generator_module._role_appears_in_body(
        "Data Engineering Intern", "I enjoy backend systems and APIs"
    )


def test_company_appears_in_body_accepts_shortened_company() -> None:
    assert generator_module._company_appears_in_body("Acme AI", "Acme AI builds tools")
    assert generator_module._company_appears_in_body("Acme AI", "I admire Acme's work")
    assert not generator_module._company_appears_in_body("Nimbus Health", "I like health apps")


def test_provider_output_with_paraphrased_role_is_accepted(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        generator_module,
        "_maybe_generate_with_provider",
        lambda _contact, _cfg: (
            "Backend Engineering Intern Application at Acme AI",
            "Hi Priya,\nI am excited about joining your Backend Engineering team at Acme AI. "
            "My Python background fits the work. Best regards, Alex Kim",
        ),
    )

    draft = generate_email(
        Contact(
            recipient_email="test@example.com",
            company="Acme AI",
            role="Backend Engineering Intern",
            candidate_name="Alex Kim",
            candidate_background="Python automation",
        ),
        config,
    )

    assert draft.subject == "Backend Engineering Intern Application at Acme AI"
    assert "Alex Kim" in draft.body


def test_summarize_resume_extracts_summary_sentence() -> None:
    text = (
        "# Resume Background\n\n"
        "## Summary\n"
        "A strong Python-first developer. Second sentence here.\n\n"
        "## Core Strengths\n- Python\n"
    )
    assert generator_module._summarize_resume(text) == "A strong Python-first developer."


def test_deterministic_body_does_not_dump_full_resume(config: AppConfig) -> None:
    contact = Contact(
        recipient_email="test@example.com",
        company="Acme AI",
        role="Backend Engineering Intern",
        candidate_name="Alex Kim",
        candidate_background="Python automation",
        job_description="Backend Engineering Intern\n\nAbout Acme AI\nAcme AI builds workflow tools.",
    )
    draft = generate_email(contact, config)
    assert draft.word_count <= 150
    assert "## " not in draft.body


def test_resume_candidate_name_parses_from_markdown() -> None:
    assert generator_module._resume_candidate_name(
        "# Resume Background\n\n**Name:** Rajendhar Are\n"
    ) == "Rajendhar Are"
    assert generator_module._resume_candidate_name(
        "Name: Priya Sharma\n## Summary"
    ) == "Priya Sharma"
    assert generator_module._resume_candidate_name("# No name here") is None


def test_is_helpful_inference_rejects_refusal_style_values() -> None:
    assert not generator_module._is_helpful_inference(
        "Unknown (cannot be inferred from the given job description)"
    )
    assert not generator_module._is_helpful_inference(
        "Generic Company Name (inferred based on a standard job description)"
    )
    assert not generator_module._is_helpful_inference("Not specified")
    assert not generator_module._is_helpful_inference("none")
    assert generator_module._is_helpful_inference("Stripe")
    assert generator_module._is_helpful_inference("Office Manager")


def test_is_plausible_company_rejects_sentence_like_values() -> None:
    assert not generator_module._is_plausible_company(
        "Unknown (cannot be inferred from the given job description)"
    )
    assert not generator_module._is_plausible_company(
        "Generic Company Name (inferred based on a standard job description)"
    )
    assert generator_module._is_plausible_company("Acme AI")
    assert generator_module._is_plausible_company("Nimbus Health")


def test_enrich_contact_drops_unhelpful_provider_company_inference(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    contact = Contact(
        recipient_email="test@example.com",
        company="",
        role="",
        candidate_name="Alex Kim",
        candidate_background="",
        job_description=(
            "Job Title: Office Manager\n\n"
            "We are looking for an experienced office manager with 5+ years of experience "
            "in administrative support for a small team."
        ),
    )

    monkeypatch.setattr(
        generator_module,
        "_infer_company_and_role_with_provider",
        lambda _contact, _cfg: (
            "Unknown (cannot be inferred from the given job description)",
            "Office Manager",
        ),
    )

    resolved = generator_module.enrich_contact_from_job_description(contact, config)

    assert resolved.company == "Unknown Company"
    assert resolved.role == "Office Manager"


def test_enrich_contact_drops_generic_company_placeholder(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    contact = Contact(
        recipient_email="test@example.com",
        company="",
        role="",
        candidate_name="Alex Kim",
        candidate_background="",
        job_description="Job Title: Office Manager\n\nWe are seeking an efficient Office Manager.",
    )

    monkeypatch.setattr(
        generator_module,
        "_infer_company_and_role_with_provider",
        lambda _contact, _cfg: (
            "Generic Company Name (inferred based on a standard job description)",
            "Office Manager",
        ),
    )

    resolved = generator_module.enrich_contact_from_job_description(contact, config)

    assert resolved.company == "Unknown Company"
    assert resolved.role == "Office Manager"


def test_extract_company_rejects_role_like_candidates() -> None:
    assert generator_module._extract_company(
        "We are looking for an office manager with 5+ years of office management experience."
    ) is None
    assert generator_module._extract_company(
        "We are hiring a Backend Intern at Acme Labs to build internal APIs."
    ) == "Acme Labs"


def test_first_sentence_strips_job_title_label() -> None:
    assert generator_module._first_sentence("Job Title: Office Manager\n\nWe are hiring.") == (
        "Office Manager"
    )
    assert generator_module._first_sentence("Role: Backend Intern at Acme AI.") == (
        "Backend Intern at Acme AI."
    )
    assert generator_module._first_sentence("Stripe builds financial infrastructure.") == (
        "Stripe builds financial infrastructure."
    )


def test_provider_output_usable_when_company_is_unknown_placeholder() -> None:
    contact = Contact(
        recipient_email="test@example.com",
        company="Unknown Company",
        role="Office Manager",
        candidate_name="Alex Kim",
        candidate_background="Python automation",
    )
    body = (
        "Hi Jamie,\n\nI am excited about the Office Manager opportunity and would love to "
        "bring my organizational skills to your team. Best regards, Alex Kim"
    )
    assert generator_module._provider_output_is_usable(body, len(body.split()), contact)

"""Phase 2 — Load outreach targets (JSON / CSV) and resume intake."""

from closer.input.loader import load_targets
from closer.input.resume import extract_resume_text

__all__ = ["load_targets", "extract_resume_text"]

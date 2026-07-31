"""Text helpers for email generation and validation."""


def count_words(text: str) -> int:
    """Count words in plain text (whitespace-separated tokens)."""
    if not text or not text.strip():
        return 0
    return len(text.split())

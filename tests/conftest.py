"""Test-session setup: keep tests hermetic from any local .streamlit/secrets.toml."""

from __future__ import annotations

import pytest
import streamlit as st


@pytest.fixture(autouse=True)
def _isolate_streamlit_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(st, "secrets", {})

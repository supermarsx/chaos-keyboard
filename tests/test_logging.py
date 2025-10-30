"""Tests for the telemetry logging helpers."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from chaos_keyboard.logging import REDACTED_PLACEHOLDER, TelemetryLogger


def _read_json(path: Path) -> list[dict[str, object]]:
    content = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in content if line]


def test_log_event_writes_jsonl_and_pretty_output(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "telemetry.jsonl"
    pretty_stream = io.StringIO()
    logger = TelemetryLogger(jsonl_path=jsonl_path, pretty_stream=pretty_stream)

    record = logger.log("effect_started", payload={"effect": "matrix_rain"})

    assert record.event == "effect_started"
    assert "matrix_rain" in pretty_stream.getvalue()

    payloads = _read_json(jsonl_path)
    assert len(payloads) == 1
    entry = payloads[0]
    assert entry["event"] == "effect_started"
    assert entry["payload"]["effect"] == "matrix_rain"
    assert "ts" in entry


def test_log_event_redacts_sensitive_fields(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "telemetry.jsonl"
    pretty_stream = io.StringIO()
    logger = TelemetryLogger(jsonl_path=jsonl_path, pretty_stream=pretty_stream)

    payload = {"text": "secret", "typed_text": "same", "other": "value"}
    logger.log("key_press", payload=payload)

    # The original payload must not be mutated.
    assert payload["text"] == "secret"

    entry = _read_json(jsonl_path)[0]
    assert entry["payload"]["text"] == REDACTED_PLACEHOLDER
    assert entry["payload"]["typed_text"] == REDACTED_PLACEHOLDER
    assert entry["payload"]["other"] == "value"

    output = pretty_stream.getvalue()
    assert REDACTED_PLACEHOLDER in output
    assert "secret" not in output


@pytest.mark.parametrize("extra_field", ["url", "typed_input"])
def test_redaction_extends_defaults(tmp_path: Path, extra_field: str) -> None:
    jsonl_path = tmp_path / "telemetry.jsonl"
    pretty_stream = io.StringIO()
    logger = TelemetryLogger(jsonl_path=jsonl_path, pretty_stream=pretty_stream)

    payload = {extra_field: "retro://home", "page": "home"}
    logger.log("demo_browser_navigate", payload=payload, redact_fields={extra_field})

    entry = _read_json(jsonl_path)[0]
    assert entry["payload"][extra_field] == REDACTED_PLACEHOLDER
    assert entry["payload"]["page"] == "home"

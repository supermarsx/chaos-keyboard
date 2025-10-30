"""Telemetry logging utilities for Chaos Keyboard."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Iterable, Mapping, MutableMapping, TextIO

__all__ = ["TelemetryLogger", "TelemetryRecord", "REDACTED_PLACEHOLDER"]

REDACTED_PLACEHOLDER = "[REDACTED]"
DEFAULT_REDACT_KEYS = frozenset({"text", "typed_text", "input"})


@dataclass(slots=True)
class TelemetryRecord:
    """Container representing a structured telemetry entry."""

    timestamp: datetime
    event: str
    payload: Mapping[str, Any]

    def to_json(self) -> str:
        """Return the record encoded as a JSON string."""

        serialisable = {
            "ts": self.timestamp.isoformat(timespec="milliseconds"),
            "event": self.event,
            "payload": self.payload,
        }
        return json.dumps(serialisable, ensure_ascii=False, sort_keys=True)


class TelemetryLogger:
    """Emit telemetry events to JSONL storage and a human readable stream."""

    def __init__(
        self,
        *,
        jsonl_path: Path | None = None,
        pretty_stream: TextIO | None = None,
        redact_keys: Iterable[str] = DEFAULT_REDACT_KEYS,
    ) -> None:
        self._jsonl_path = jsonl_path
        self._pretty_stream = pretty_stream
        self._redact_keys = frozenset(key.strip().lower() for key in redact_keys)
        self._lock = Lock()

    def log(
        self,
        event: str,
        *,
        payload: Mapping[str, Any] | None = None,
        redact_fields: Iterable[str] | None = None,
    ) -> TelemetryRecord:
        """Record a telemetry event.

        Parameters
        ----------
        event:
            The machine readable name of the event.
        payload:
            Optional mapping with additional structured data. The mapping is
            shallow-copied to avoid mutating user state.
        redact_fields:
            Optional iterable of field names that must be redacted for this
            event. When omitted the logger falls back to
            :data:`DEFAULT_REDACT_KEYS` configured during initialisation.
        """

        timestamp = datetime.now(timezone.utc)
        payload_copy: MutableMapping[str, Any] = dict(payload or {})
        active_redact = self._redact_keys
        if redact_fields is not None:
            active_redact = self._redact_keys.union({field.strip().lower() for field in redact_fields})

        for key in list(payload_copy):
            if self._should_redact(key, active_redact):
                payload_copy[key] = REDACTED_PLACEHOLDER

        record = TelemetryRecord(timestamp=timestamp, event=event, payload=dict(payload_copy))
        self._write_record(record)
        return record

    def format_pretty(self, record: TelemetryRecord) -> str:
        """Return a human friendly representation of ``record``."""

        timestamp = record.timestamp.astimezone(timezone.utc).strftime("%H:%M:%S")
        parts = [f"[{timestamp}]", record.event]
        if record.payload:
            kv_pairs = ", ".join(f"{key}={value}" for key, value in record.payload.items())
            parts.append(kv_pairs)
        return " ".join(parts)

    def _write_record(self, record: TelemetryRecord) -> None:
        json_line = record.to_json()
        pretty_line = self.format_pretty(record)

        with self._lock:
            if self._jsonl_path is not None:
                self._jsonl_path.parent.mkdir(parents=True, exist_ok=True)
                with self._jsonl_path.open("a", encoding="utf-8") as handle:
                    handle.write(json_line + "\n")
            if self._pretty_stream is not None:
                self._pretty_stream.write(pretty_line + "\n")
                self._pretty_stream.flush()

    @staticmethod
    def _should_redact(key: str, redactions: Iterable[str]) -> bool:
        lookup = key.strip().lower()
        return lookup in redactions

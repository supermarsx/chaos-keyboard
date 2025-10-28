"""Unit tests covering the Chaos Keyboard safety policies."""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from threading import Thread
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from chaos_keyboard.safety import (  # noqa: E402  - local import for tests
    CapabilityNotAllowed,
    SafetyContext,
    SafetyError,
    SafetyInterlocks,
    SafetyWatchdog,
    normalize_mode,
    RuntimeMode,
)


def test_sim_only_denies_dangerous_capabilities() -> None:
    ctx = SafetyContext(mode="sim only")

    assert ctx.mode is RuntimeMode.SIM_ONLY
    assert ctx.allows("overlay")
    assert not ctx.allows("system")

    with pytest.raises(CapabilityNotAllowed):
        ctx.require_capabilities(["overlay", "system"])


def test_lab_mode_requires_authorisation() -> None:
    with pytest.raises(SafetyError):
        SafetyContext(mode="LAB")

    interlocks = SafetyInterlocks()
    interlocks.arm_lab_mode(token="demo-operator")
    ctx = SafetyContext(mode="LAB", interlocks=interlocks)

    assert ctx.mode is RuntimeMode.LAB
    assert ctx.interlocks is interlocks


def test_normalize_mode_handles_aliases() -> None:
    assert normalize_mode("sim") is RuntimeMode.SIM_ONLY
    assert normalize_mode("stream safe") is RuntimeMode.STREAM_SAFE
    assert normalize_mode("unknown") is RuntimeMode.SIM_ONLY


def test_panic_stop_completes_within_200ms() -> None:
    watchdog = SafetyWatchdog(max_stop_duration=0.2)
    callbacks: list[str] = []

    watchdog.register(lambda: callbacks.append("fired"))

    def trigger_panic() -> None:
        time.sleep(0.05)
        watchdog.panic()

    thread = Thread(target=trigger_panic)
    thread.start()

    start = perf_counter()
    assert watchdog.wait_for_panic(timeout=0.2)
    elapsed = perf_counter() - start

    thread.join()

    assert callbacks == ["fired"]
    assert elapsed <= 0.2


def test_panic_runs_all_callbacks_even_when_some_raise(caplog: pytest.LogCaptureFixture) -> None:
    watchdog = SafetyWatchdog()
    callbacks: list[str] = []

    watchdog.register(lambda: callbacks.append("first"))

    def faulty_callback() -> None:
        callbacks.append("faulty")
        raise RuntimeError("boom")

    watchdog.register(faulty_callback)
    watchdog.register(lambda: callbacks.append("second"))

    with caplog.at_level(logging.ERROR):
        watchdog.panic()

    assert callbacks == ["first", "faulty", "second"]
    assert any("panic callback" in message for message in caplog.messages)


def test_wait_for_panic_accounts_for_callback_runtime() -> None:
    watchdog = SafetyWatchdog(max_stop_duration=0.05)

    def slow_callback() -> None:
        time.sleep(0.1)

    watchdog.register(slow_callback)

    thread = Thread(target=watchdog.panic)
    thread.start()

    start = perf_counter()
    assert not watchdog.wait_for_panic(timeout=0.2)
    elapsed = perf_counter() - start

    thread.join()

    # The watchdog should report that the panic exceeded its configured duration.
    assert elapsed >= 0.05

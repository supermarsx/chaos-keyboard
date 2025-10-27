# Agent Instructions

## Required reading before coding
- Study `spec.md` to keep features aligned with the safety, mode, and UX expectations of Chaos Keyboard.
- Review any affected modules to mirror existing patterns (typed Qt widgets, safety interlocks, and simulation-first defaults).

## Coding standards
- Preserve the project's typed style: keep `from __future__ import annotations`, annotate all public APIs, and favor explicit return types.
- Follow PEP 8 formatting and descriptive docstrings for new modules, classes, and functions.
- Keep UI code declarative and state updates centralized (e.g., prefer `ModeStatusBar.update_mode` over inline label mutation).
- Use pathlib and dataclasses where appropriate for new filesystem or configuration helpers.

## Testing & validation
- Run available unit or integration tests (`pytest` when present) and manual smoke tests via `python -m chaos_keyboard --mode "SIM ONLY"` for UI work.
- Update documentation (`readme.md`, module docstrings) when behavior changes or new effects are added.
- Ensure new features remain simulation-only by default; gate any lab-only behavior behind explicit safeguards as described in the spec.

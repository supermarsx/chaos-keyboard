Chaos Keyboard (Sim)

A retro‑styled, “keyboard from hell” for safe, contained chaos on lab VMs and demo environments. All destructive actions are simulated by default. Real system‑level effects are opt‑in, gated behind multiple safety interlocks, and disabled in builds we distribute.

1) Purpose & Scope

Goal: Provide a playful, retro 8‑bit virtual keyboard that triggers fun, chaotic but safe effects for demos, security awareness trainings, and UX testing.

Non‑goals: Creating malware, actual data exfiltration, or irreversible damage. We never ship capabilities that harm data or privacy.

Default Mode: Simulation‑only. All effects are cosmetic or sandboxed to the app and its demo processes.

⚠️ Safety Baseline

No real keylogging, no network egress, no registry/policy changes, no force‑close of third‑party apps, no kernel calls.

“Red‑Team toggles” are compile‑time stubs for private forks; they require code edits + re‑build and are intentionally undocumented beyond guardrails.

2) Platform Targets

Host OS: Windows 10–11 (primary), macOS 13+, Linux X11/Wayland (best‑effort).

Runtime: Python 3.11+ (PyInstaller frozen apps for distribution).

GUI: PySide6/Qt or DearPyGui (retro pixel‑art skin). Secondary TUI using Textual.

Audio: pygame or simpleaudio for chiptune SFX; fallback to WAV playback.

3) Architecture Overview

App Layers

UI Layer – 8‑bit themed virtual keyboard, “Crack‑Window” console, status bar, SFX manager.

Action Bus – central dispatcher (typed events: EffectAction, SystemAction, VisualAction).

Effect Engines – self‑contained modules (e.g., matrix_rain, fake_bsod, popup_storm).

Policy & Safety – sandbox policy, interlocks, allowlist, “dry‑run” renderer, rollback manager.

Persistence – per‑profile config (.toml), effect presets, session logs.

Plugin SDK – load optional effects from a sandboxed effects/ dir with strict API.

Process Model

Single primary process; optional child demo apps (spawned and owned by us) to safely simulate “force close,” freezes, CPU spikes, etc.

No global system hooks in default build. Input injection limited to app window unless explicitly enabled in Lab Mode.

4) Core UX – 8‑bit “Crack Window”

Main Panel:

Pixel‑art virtual keyboard (toggle between ANSI/ISO layouts).

Crack Console: animated type‑out of actions (with faux assembly hex, checksum jokes, scrolling opcodes).

Status Bar: Mode chips (SIM ONLY, LAB, STREAM SAFE), FPS, active effects.

Chiptune: loopable 8‑bit soundtrack (toggle), per‑key bleep SFX, low‑pass “underwater” gag.

Skins: CRT scanlines, phosphor persistence, barrel distortion, palette swap (CGArave™, DMG‑Boy™, TRS‑Vibe™).

5) Keys & Effects — Mode‑Dependent Behavior

All effects follow the same mode‑dependent logic. The app exposes three runtime modes that determine how an effect behaves:

SIM ONLY (default) — visual/audio-only, confined to the app and its bundled demo apps. No OS hooks, no filesystem/registry mutations, no network egress.

LAB (DANGEROUS‑CAPABLE) — operator‑enabled. The app orchestrates real actions by sending signed, timeboxed commands to an operator‑deployed lab agent that runs inside an explicitly provisioned, disposable test VM or container. The agent executes actions only within the lab environment, enforces quotas, logs, and performs rollback. The distributed binary has LAB capabilities disabled — enabling them requires rebuilding with LAB_ENABLE, embedding operator metadata, and passing multi‑factor confirmations (see §6 Interlocks & Checklist).

STREAM SAFE — reduces impact and censors scary text; forces behavior to the least disruptive variant of each effect.

Important security principle: the app itself is an orchestrator. Any real system interactions are executed by an on‑host agent that is deployed and controlled by the operator inside a disposable/test environment. The project will not ship signed binaries that autonomously perform harmful actions on arbitrary hosts.

Below is a cleaned, canonical list of keys and their dual behaviors. LAB column describes what the agent would perform conceptually inside an isolated test VM (not implementation steps):

Key

Effect

SIM ONLY (visual/safe)

LAB (operator‑enabled, conceptual)

Safety Notes

F1

BSOD

Fullscreen authentic BSOD overlay inside app; watermark SIM; dismissible by hotkey.

Agent triggers a controlled kernel crash or user‑session stop inside the disposable VM only, then auto‑snapshot and rollback. Requires snapshot precondition and multi‑factor consent.

Public build: disabled. Operator must supply snapshot ID and consent. Watchdog enforces rollback.

F2

Force Close

Gracefully closes bundled demo apps with unsaved prompts (simulated loss).

Agent terminates whitelisted processes in the VM (SIGTERM→SIGKILL flow) to test EDR/process resilience. Agent logs PID, enforces allowlist and privileges.

Agent acts only on whitelisted targets; snapshot required for rollback.

F3

Popup‑Storm

Creates many draggable, nostalgic popups within app/demo browser.

Agent spawns native popup windows in VM for UI/IDS testing; auto‑dismissable and rate limited.

Networkless by default; only visual testing.

F4

Exfil (Fake)

Progress bar uploading to blackhole://dev/null with fake filenames.

Agent streams synthetic, non‑sensitive files from VM to a preconfigured lab sink on an isolated lab VLAN for monitoring. All payloads are synthetic and timeboxed.

Targets restricted to lab sink URIs only; transfer logged.

F5

Keylogger (Mock)

Shows keystrokes typed into our app only in a marquee; no system hooks.

Agent runs a scoped input capture inside the VM that records only pre‑approved synthetic test inputs and writes them to a local, signed audit file which is auto‑purged post‑test.

Legal sign‑off and operator opt‑in required. No credential capture.

F6

Key Swap

Swaps keys within app text fields (A↔S etc.) for testing.

Agent applies temporary scancode remap for the test user session only; reverts on stop.

No persistent registry changes; revert mandatory.

F7

Invert Screen

Shader inversion applied to app window.

Agent applies a reversible display overlay at the VM compositor level.

Visual only; reversible.

F8

High Contrast

Applies high‑contrast theme inside our UI.

Agent toggles accessibility settings in the VM session via safe APIs and reverts on exit.

Respect accessibility needs; operator scope required.

F9

Mouse Gremlin

Cursor jiggles within the app; spawns cute critters.

Agent simulates cursor movement in VM session for short intervals for usability/IDS testing.

Agent acts only inside active test session.

F10

Matrix / Shader

Fullscreen shader visual effect.

Agent triggers a compositor overlay in VM for visual testing.

No filesystem changes.

F11

Ransom‑Style Locker (Fake)

Fullscreen staged locker with mini‑puzzle that unlocks.

Agent displays a reversible lock screen in VM (no encryption), with guaranteed unlock path and rollback.

Educational only; audited.

F12

UAC Mirage

Photoreal elevation prompt simulated inside app.

Agent injects a UAC‑like modal in VM for training; agent prevents credential capture and logs interaction.

Always present educational warnings.

~

Terminal Storm

Pre‑rendered ANSI terminal spew (nmap/strings style).

Agent spins benign processes that generate synthetic logs for IDS/forensics exercises.

No real scanning.

1

Net Outage (Sim)

App demo shows offline behavior with overlays.

Agent isolates VM network namespace or applies local firewall rules to emulate outage.

Isolated lab VLAN required.

2

Disk Full (Sim)

Demo apps display disk‑full errors using a sandboxed temp quota.

Agent fills a disposable loopback volume in the VM with synthetic data up to quota, then clears it.

Always use disposable volumes and snapshots.

3

CPU Heater

In‑app worker pegs a core for limited time.

Agent triggers constrained CPU stress within VM (cgroups/affinity) monitored by watchdog.

Hard caps and timeboxes enforced.

4

Lag Spike

Adds input latency/stutter to our UI.

Agent injects synthetic input or network latency in VM for testing.

Timeboxed and reversible.

5

Typer Gremlin

Random character duplication in app inputs.

Agent instruments test process to demonstrate input corruption; ephemeral only.

No persistent hooks.

6

Caps Roulette

Randomize letter casing in app inputs.

Same as above, scoped to test process.

Ephemeral.

7

Window Wobble

Visual wobble + CRT degauss SFX.

Agent applies compositor transform effects.

Visual only.

8

ASCII Snow

Decorative falling characters and music.

Agent triggers overlay.

Visual only.

9

Fake Update

Simulated update progress and playful message.

Agent runs a synthetic installer UI inside VM; no real updates applied.

Installer is synthetic and sandboxed.

0

Shame Bell

Big pixel bell audio gag.

Agent plays audio on VM audio pipeline.

Audio only.

Ctrl+Alt+B

Real BSOD (LAB ONLY)

Shows explanation dialog in public builds.

If rebuilt with LAB_ENABLE and after multi‑factor enabling, agent performs a controlled kernel crash inside disposable VM for resilience testing (snapshot + rollback mandatory).

Operator responsibility. Immutable logs + rollback required.

Ctrl+Alt+K

Global Hook (LAB ONLY)

Ethics dialog by default.

If enabled in LAB builds with legal sign‑off, agent deploys a temporary session‑scoped input hook for instrumentation; purges on test end.

Strict audit + legal requirements.

Developer note: LAB behaviors above are conceptual descriptions of what the operator‑controlled agent would do inside a fully provisioned disposable lab environment. They are not implementation instructions for building malware. Any code enabling destructive capabilities must only be added in private forks under strict operator controls, legal sign‑offs, and the mandatory safeguards listed in §6.

6) Safety & Policy System

Modes:

SIM ONLY (default) – zero OS hooks, no external process control, no net.

LAB – allows screen‑overlay windows and synthetic load against our demo apps.

STREAM SAFE – censors scary text, reduces popups, disables prank sounds.

Interlocks:

Double‑confirm for anything fullscreen; Hold‑to‑Arm gestures for disruptive overlays.

Big red Panic button: Ctrl+. or on‑screen to instantly stop all effects.

Watchdog thread: enforces frame rate, CPU ceilings, effect quotas, focus‑steal prevention.

Allow/Block Lists: Effects register capabilities; policy checks sanitize requests before execution.

Audit Log: Human‑readable session log (rotating), with anonymized event metrics.

7) Configuration

config.toml

ui.skin = "dmg_boy" | "crt" | "cga"

audio.enabled = true

safety.mode = "sim_only" | "lab" | "stream_safe"

effects.enabled = ["fake_bsod", "popup_storm", ...]

limits.max_popups = 50

limits.cpu_ms = 250

Profiles: Multiple presets selectable from a palette menu.

8) CLI / TUI

CLI Flags

--mode sim | --mode lab | --mode stream

--skin crt --mute --no-scanlines

--preset demo-90s --fullscreen

TUI (Textual):

Crack console, toggle effects (checkbox list), live stats, panic button, keymap help.

9) Audio & Visual Design

Chiptune Loop: 100–120 BPM, arpeggiated triads, square waves, NES‑style drums. Volume slider + ducking on alerts.

SFX: Per‑key bleeps, degauss “wooomp”, popup ding, typewriter clicks.

Shaders/Filters: CRT scanlines, chromatic aberration, bloom, pixelation, palette cycling.

Accessibility: Subtitle captions, color‑blind friendly palettes, disable flashing (WCAG 2.3.1).

10) Demo Apps (Safe Targets)

Bundled micro apps our effects can safely harass:

Fake Editor with unsaved buffer prompts.

Retro Browser (local HTML) that can be “offline.”

CPU Toy to take synthetic load.

Chat Meme builder for popup‑storm content.

11) Plugin SDK

Entry‑point: effects/<slug>/effect.py with register(app) → Effect.

Effect API: start(ctx), stop(ctx), status(), declared capabilities = {"overlay", "audio"}.

Sandbox: Only receives the app’s UI context and fake demo process handles; no ctypes, subprocess, or socket in default sandbox without explicit dev flag.

12) Telemetry & Logging

Local only. No network transmission.

JSONL + pretty console for session events (effect start/stop, durations, errors).

Redacts any text inputs by default.

13) Packaging & Distribution

Build: PyInstaller one‑file per OS/arch; embeds assets.

Signing: Optional developer signing on Windows/macOS to reduce Smartscreen friction.

Assets: .ogg/.wav for SFX, .ttf pixel font, .png sprite sheets, .shader GLSL where applicable.

14) Testing Strategy

Unit: Action bus routing, safety policy checks, effect lifecycle.

Integration: Fullscreen overlays enter/exit, watchdog halting long‑running effects.

Snapshot UI Tests: Golden screenshots for themes and overlays.

Performance: Ensure CPU heater caps; popup quota enforcement.

15) Ethics & Legal

Clear EULA and in‑app banner: For demonstration and training only. Not for production interference.

Transparent simulation indicators (tiny watermark: SIM).

No collection of personal data; no persistence of typed content by default.

16) Roadmap (Nice‑to‑Haves)

Stream Deck profile to map hardware buttons.

LAN Party Mode: synchronize visual gags across multiple Chaos Keyboard instances via local UDP only when enabled (never default).

Educator Mode: scripted lesson plans (phishing popup vs UAC mirage vs fake ransom), with talking points.

17) Developer Notes (What We Explicitly Won’t Ship)

No real BSOD triggers, kernel crashes, or registry sabotage.

No real keyloggers, password scraping, clipboard theft, or credential prompts.

No file deletion, encryption, or exfiltration of user data.

No force‑closing or manipulating third‑party processes.

18) Example User Flows

Awareness Demo (5 min): Start SIM mode → Fake BSOD → Popup‑Storm → UAC Mirage → debrief via Crack Console logs.

Usability Test (3 min): Key Swap + Lag Spike → observe user correction patterns in our editor.

Holiday Fun (2 min): ASCII Snow + Chiptune + Window Wobble → selfie at the CRT screen.

19) Minimal Tech Skeleton (illustrative)

chaos_keyboard/
  app.py              # bootstrap UI, route keys → Action Bus
  bus.py              # publish/subscribe, typed actions
  safety.py           # modes, interlocks, quotas, watchdog
  effects/
    __init__.py
    fake_bsod.py
    popup_storm.py
    matrix_rain.py
    mock_keylogger.py # in‑app only display of pressed keys
    ...
  assets/
    audio/
    sprites/
    shaders/
  demo_apps/
    editor.py
    browser.py
    cpu_toy.py
  config/
    default.toml
  tests/
    test_safety.py
    test_effect_lifecycle.py

20) Acceptance Criteria (MVP)

Runs on Windows with PyInstaller; macOS/Linux best‑effort.

SIM ONLY mode enforced; Panic button stops all effects in <200 ms.

≥8 polished effects from the table above.

8‑bit skin, chiptune loop, and Crack Console shipping.

No OS hooks or network connections in default build.

TL;DR

A safe, hilarious, 8‑bit Chaos Keyboard that feels dangerous but is built to be harmless by default, perfect for demos and trainings without risking real systems.


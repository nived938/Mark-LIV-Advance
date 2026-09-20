# ChatGPT / AI Development Guide

This file is the fast context document for any AI assistant working on this repository.

## Project identity

Repository: `nived938/Mark-LIV-Advance`

Product: a native desktop J.A.R.V.I.S-style personal AI assistant.

Primary runtime: Python + PyQt6 + Gemini Live.

Main source:
- `main.py` — live conversation/session supervisor, audio, tool dispatch, reconnect, cancellation, shutdown.
- `ui.py` — PyQt6 UI, HUD, Arc Core, overlays, public `JarvisUI` wrapper.
- `core/` — cross-cutting engine logic.
- `actions/` — self-describing built-in tools.
- `plugins/` — drop-in optional tools.
- `memory/` — persistent local memory and configuration.
- `dashboard/` — local runtime/dashboard data.
- `scripts/` — developer checks.

Read `architecture.md` before making structural changes.

## Existing major capabilities

Do not propose or implement these as "new" unless the request explicitly asks for changes:

- Voice conversation through Gemini Live.
- Animated HUD / Arc Core reactor HUD.
- Facial animation and lip sync.
- Wake word.
- Push-to-talk.
- Audio device selection.
- Screen and webcam vision.
- Windows desktop/UI automation.
- Android/ADB control.
- Browser control.
- File search and file management.
- File/document processing.
- Terminal agent.
- Coding/testing agent.
- Mark 32 autonomous planning/execution.
- Mark 32 verification and cancellation.
- Long-term memory.
- Clipboard intelligence.
- Notifications and reminders.
- Calendar/email/communication integrations.
- WhatsApp incoming-call detection.
- Background monitoring.
- Remote dashboard.
- Plugin/action discovery.
- Live theming and assistant customization.
- Task terminal and task observability.

## Rules for changes

### 1. Preserve architecture boundaries

Put code in the smallest correct layer:

- conversation/session lifecycle -> `main.py`
- Qt widgets and UI presentation -> `ui.py`
- reusable engine/state logic -> `core/`
- built-in skill -> `actions/`
- optional extension -> `plugins/`
- persistent local data -> `memory/`

Do not move reusable actions into `main.py`.

### 2. JarvisUI is the public UI contract

`main.py` must communicate through `JarvisUI`.

When adding a UI capability used by `main.py`:
1. Add the implementation to `MainWindow`.
2. Add the public bridge/property/method to `JarvisUI`.
3. Run `python scripts\\check_ui_contract.py`.

Never make new `main.py` code depend on private `self.ui._win` internals.

### 3. Threading

Qt widgets live on the Qt main thread.

Slow or blocking work belongs in worker threads/executors.

Workers communicate with the UI through `JarvisUI` methods or Qt signals.

Never update a Qt widget directly from a worker thread.

### 4. Long-running tasks

A slow operation should:

- support cooperative cancellation
- show progress when useful
- never block the Qt event loop
- end with an explicit success/error/cancelled state

The Arc Core task terminal is specifically for active long-running tasks.

### 5. Truthfulness

J.A.R.V.I.S. must never claim an action succeeded unless the underlying tool actually succeeded.

Verification belongs in the execution path for autonomous tasks.

### 6. Destructive/external actions

Respect the existing permission and confirmation system.

Do not bypass confirmation for shutdown, deletion, external writes, purchases, message/email sends, installation, or similar irreversible/external operations.

### 7. Secrets

Never commit:
- `config/api_keys.json`
- credentials
- tokens
- private certificates
- user-specific runtime data

### 8. Keep the UI original

Do not replace the existing J.A.R.V.I.S. visual identity with generic dashboard components unless explicitly requested.

The current design language is dark, compact, technical, holographic, and Arc Core oriented.

## Validation

Run:

```bat
python scripts\check_ui_contract.py
python -m py_compile main.py ui.py core\mark32_engine.py actions\file_search_advance.py actions\mark32_advance.py actions\whatsapp_incoming_agent.py
```

Then test:
- startup
- voice
- text input
- long task
- interrupt
- cancellation
- closing during a task
- camera
- wake word
- plugin loading

## Best files to inspect for common work

| Task | Start here |
|---|---|
| Tool behavior | `actions/<tool>.py` |
| Autonomous Mark 32 behavior | `core/mark32_engine.py` |
| Prompt/routing | `core/prompt.txt` |
| UI layout | `ui.py` |
| Live conversation | `main.py` |
| Memory | `memory/memory_manager.py` |
| Settings | `memory/config_manager.py` |
| New plugin | `plugins/_template.py` |
| UI bridge errors | `ui.py` + `scripts/check_ui_contract.py` |
| Architecture | `architecture.md` |
| Future feature ideas | `roadmap.md` |

## AI workflow

Before editing:
1. Read `architecture.md`.
2. Read the target file and its callers.
3. Search for existing implementations before creating new ones.
4. Check whether the capability already exists.

After editing:
1. Run the UI contract check when UI bridges changed.
2. Run Python compilation.
3. Inspect the diff.
4. Report exactly which files and behaviors changed.

## Important current facts

- The task terminal is inside the Arc Core HUD, not the outer left application rail.
- The task terminal is hidden when idle and appears only during active long-running tasks.
- Qt font-database warning noise is intentionally filtered at the Qt logging category level.
- File search has cooperative cancellation.
- Application shutdown has explicit cancellation/reconnect cleanup.

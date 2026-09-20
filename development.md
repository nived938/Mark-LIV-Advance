# Development Guide

## Environment

Typical local project path used during development:

```text
E:\Jarvis-Mark-32
```

The repository is:

```text
nived938/Mark-LIV-Advance
```

## Start the application

```bat
cd /d E:\Jarvis-Mark-32
python main.py
```

## Compile check

```bat
python -m py_compile main.py ui.py core\mark32_engine.py actions\file_search_advance.py actions\mark32_advance.py actions\whatsapp_incoming_agent.py
```

## UI contract check

```bat
python scripts\check_ui_contract.py
```

This checks every public `self.ui.<name>` reference used by `main.py` against the `JarvisUI` wrapper.

## Safe change workflow

### Step 1 — Understand

Read:
- `architecture.md`
- `chatgpt.md`
- `project.md`

Then inspect the target implementation and its callers.

### Step 2 — Search

Before adding a function, search the repository for:
- the capability name
- the desired behavior
- existing action/plugin names
- relevant UI callbacks

Avoid duplicate implementations.

### Step 3 — Implement in the correct layer

- `actions/` for a reusable built-in tool
- `plugins/` for an optional integration
- `core/` for shared infrastructure
- `main.py` for live-session orchestration
- `ui.py` for Qt presentation

### Step 4 — Preserve safety

Use:
- existing permission checks
- confirmation UI
- cancellation tokens
- existing undo mechanisms where applicable

Never silently bypass a protection because a feature is inconvenient.

### Step 5 — Test

At minimum:

```bat
python scripts\check_ui_contract.py
python -m py_compile main.py ui.py core\mark32_engine.py
```

For changes in an action:

```bat
python -m py_compile actions\<changed_action>.py
```

### Step 6 — Runtime test

Test the smallest user-facing flow first.

Examples:
- new action -> invoke that action directly
- UI change -> open the relevant panel
- long task -> verify Arc Core terminal
- cancellation -> interrupt during work
- shutdown -> close while work is running

## Debugging common classes of failure

### Missing JarvisUI method

Symptom:

```text
AttributeError: 'JarvisUI' object has no attribute '...'
```

Fix:
1. Add the method/property to `JarvisUI`.
2. Keep the real implementation on `MainWindow` if it is Qt-specific.
3. Run:

```bat
python scripts\check_ui_contract.py
```

### Qt thread errors

Symptom:
- crashes while updating widgets from a worker
- inconsistent UI updates

Fix:
- emit a Qt signal
- or call a thread-safe `JarvisUI` bridge

Never manipulate `QWidget` instances from worker threads.

### Long task cannot stop

Inspect:
- `main.py` active tool task cancellation
- `actions/file_search_advance.py`
- `core/mark32_engine.py` `CancelToken`

The work must check cancellation inside loops, not only before starting.

### Shutdown traceback

Check:
- `request_shutdown()`
- active tool tasks
- executor creation
- reconnect loop
- background monitor threads

No new future/task should be scheduled after shutdown has started.

### Duplicate tool/action behavior

Search `actions/`, `plugins/`, and inline `TOOL_DECLARATIONS`.

Action names must not collide with inline tools.

## UI development rules

The visual identity is centered on the Arc Core:

- dark technical HUD
- cyan/teal primary system language
- restrained accent colors
- thin borders
- compact terminal-style typography
- overlays inside the central HUD where appropriate

The outer left rail is for system telemetry. Long-running task feedback belongs to the Arc Core task terminal.

## Git workflow

Recommended normal sync:

```bat
git fetch origin
git status --short
git pull --ff-only origin main
```

Before pulling when you have local work:

```bat
git stash push -u -m "local work before sync"
git pull --ff-only origin main
git stash pop
```

Do not use destructive reset commands to solve ordinary sync problems without first preserving local work.

## Release checklist

- Application starts.
- UI contract passes.
- Python compilation passes.
- Voice input/output works.
- Text input works.
- Tools execute real actions.
- Long tasks show progress.
- Interrupt works.
- Cancellation works.
- Closing during a task does not create reconnect/shutdown traceback loops.
- Secrets are not committed.

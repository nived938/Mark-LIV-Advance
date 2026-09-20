# Project Guide

## What is J.A.R.V.I.S.?

J.A.R.V.I.S. is a native desktop personal AI assistant designed to feel like a real computer companion rather than a chat window.

It can converse by voice, operate the local computer, work with files, control Android devices, use vision, run multi-step tasks, remember useful information, and expose optional capabilities through actions and plugins.

## New capability layer

The current build has seven new product areas in addition to Mark 32's earlier agents:

- Meeting & Call Copilot — captures Live input transcription into local meeting records and returns the transcript for summary.
- Knowledge Vault — indexes selected text/document sources into a persistent local search database with source paths/snippets.
- Workflow Recorder — records action/plugin calls and replays saved routines.
- Event Rules Engine — persistent WHEN/THEN rules for file and process events.
- Hardware Diagnostics Center — collects a diagnostic health report without automatically stress-testing hardware.
- Self-Updater — checks the GitHub origin and applies only safe fast-forward updates.
- Personal Workspace Modes — persistent Coding/Study/Work/Presentation/Travel contexts and custom profiles.

Operating modes are separate from workspaces:

- Normal = standard behavior.
- Gaming = Steam + conservative optional-background-app cleanup.
- Serious = autonomous Mark 32 permissions with OS/UAC still authoritative.

## Product goals

1. Natural voice-first interaction.
2. Real computer control instead of simulated answers.
3. Autonomous multi-step work with verification.
4. Strong cancellation and safe shutdown.
5. A highly visible Arc Core/HUD interface.
6. Extensible capabilities without making `main.py` a monolith.
7. Local-first storage for configuration and memory.

## Runtime model

```
                         J.A.R.V.I.S.
                              |
                  +-----------+-----------+
                  |                       |
             Gemini Live              Local UI
                  |                       |
             JarvisLive                JarvisUI
                  |                       |
          +-------+-------+         MainWindow
          |       |       |              |
       Actions  Plugins  Mark32       Arc Core
          |       |       |          / Task UI
          +-------+-------+              |
                  |                      |
              Local machine       user-visible state
```

## Directory map

```
/
├── main.py
├── ui.py
├── architecture.md
├── chatgpt.md
├── project.md
├── development.md
├── roadmap.md
├── setup.py
├── requirements.txt
├── requirements-advance.txt
│
├── actions/
│   └── built-in tools
│
├── core/
│   ├── mark32_engine.py
│   ├── action_loader.py
│   ├── plugin_loader.py
│   ├── prompt.txt
│   ├── avatar.py
│   ├── viseme.py
│   ├── echo.py
│   ├── confirm.py
│   ├── undo.py
│   ├── hotkey.py
│   ├── wake_word.py
│   └── audio_devices.py
│
├── plugins/
│   ├── _template.py
│   └── optional integrations
│
├── memory/
│   ├── memory_manager.py
│   ├── config_manager.py
│   └── local runtime state
│
├── dashboard/
│   └── local runtime dashboard data
│
└── scripts/
    └── developer validation checks
```

## Request lifecycle

### Normal conversation

```
user voice/text
     |
     v
JarvisLive
     |
     v
Gemini Live
     |
     +---- normal answer ----> speech/HUD
     |
     +---- tool call ---------> action/plugin/Mark32
                                  |
                                  v
                            real result
                                  |
                                  v
                           Gemini response
```

### Autonomous task

```
goal
 |
 v
Mark32Engine
 |
 +--> planner
 |
 +--> permission check
 |
 +--> deterministic tool
 |
 +--> verifier
 |
 +--> recovery/routing when applicable
 |
 +--> task store
 |
 +--> dashboard state
```

## State ownership

| State | Owner |
|---|---|
| Gemini session | `JarvisLive` |
| UI widgets | `MainWindow` |
| Public UI callbacks | `JarvisUI` |
| Mark 32 task state | `Mark32Engine` / `TaskStore` |
| Long-term memory | `memory/memory_manager.py` |
| Settings | `memory/config_manager.py` |
| Action registry | `core/action_loader.py` |
| Plugin registry | `core/plugin_loader.py` |
| Camera stream | `MainWindow` camera subsystem |
| Cancellation | `JarvisLive` + Mark 32 `CancelToken` |

## Where to add a new capability

### Use an action

Use `actions/` when the capability is a normal tool that can be described by a `TOOL` declaration and a handler.

Examples:
- a new device API
- a new operating-system utility
- a new data lookup
- a new local integration

### Use a plugin

Use `plugins/` when the capability is optional, third-party, domain-specific, or intended to be installed/removed independently.

### Use core

Use `core/` when the behavior is shared infrastructure rather than a single user-facing tool.

### Use main.py

Use `main.py` only when the behavior is inherently tied to the live conversation/session lifecycle.

### Use ui.py

Use `ui.py` for visual presentation, controls and Qt-specific interaction.

## Important architectural rule

The project has one public UI boundary:

`main.py -> JarvisUI -> MainWindow`

This is important because `MainWindow` contains Qt implementation details while `main.py` runs the assistant/session engine.

## Existing task observability

The Arc Core task terminal is a temporary overlay for active long-running work.

Idle:
- hidden

Active long task:
- visible

Completion/error/cancel:
- hidden

This keeps the Arc Core visually clean without losing task progress when work is actually happening.

## Local data

The assistant is local-first, but Gemini Live is still a network dependency for the conversational model.

Do not confuse local configuration/memory with model inference privacy.

## Documentation map

- `architecture.md` — technical architecture and runtime contracts.
- `chatgpt.md` — rules and context for AI coding assistants.
- `project.md` — project overview for humans and AI.
- `development.md` — coding, testing and debugging workflow.
- `roadmap.md` — proposed new capabilities that are not existing feature upgrades.

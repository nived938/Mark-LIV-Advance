# J.A.R.V.I.S. — Architecture

## 1. Purpose

Mark-LIV-Advance is a native desktop J.A.R.V.I.S. assistant. The main runtime combines:

- PyQt6 desktop UI and animated HUD.
- Gemini Live conversational audio.
- Self-discovering action modules in actions/.
- Optional plugins in plugins/.
- The Mark 32 autonomous task engine.
- Local long-term memory and configuration.
- Screen and webcam vision.
- Windows desktop/UI Automation.
- Android/ADB control.
- Browser, terminal and coding capabilities.
- Scheduling, notifications and communication helpers.

The design keeps the live conversation/session state in main.py while reusable capabilities live in actions/, core/, and memory/.

## 2. High-Level Runtime

    main.py
      JarvisLive supervisor
          |
          +-- Gemini Live session
          |     +-- audio input/output
          |     +-- conversation turns
          |     +-- tool calls
          |
          +-- inline tools
          |     +-- screen / vision
          |     +-- memory
          |     +-- monitoring
          |     +-- shutdown
          |
          +-- ActionRegistry
          |     +-- actions/*.py
          |
          +-- PluginRegistry
          |     +-- plugins/*
          |
          +-- Mark32Engine
          |     +-- planning
          |     +-- permissions
          |     +-- execution
          |     +-- verification
          |     +-- cancellation
          |     +-- scheduling
          |
          +-- JarvisUI
                +-- MainWindow
                +-- HUD
                +-- task terminal
                +-- activity log
                +-- controls

## 3. Startup Sequence

1. main.py starts and normalizes Windows console/subprocess behavior.
2. JarvisUI creates QApplication and MainWindow.
3. MainWindow builds the HUD, system monitor, task terminal, activity log, content panel, camera surface and controls.
4. JarvisLive loads configuration and initializes live-session state.
5. action_loader discovers valid action modules.
6. plugin_loader discovers valid plugins.
7. JarvisLive wires the UI callback interface.
8. Background integrations such as wake word, WhatsApp monitoring and Mark 32 scheduling become available.
9. The asynchronous supervisor starts the Gemini Live/reconnect loop.

The UI wrapper is a public contract. New UI capabilities used from main.py must be exposed by JarvisUI, even when the implementation is inside MainWindow.

## 4. UI Layer: ui.py

### MainWindow

MainWindow owns all Qt widgets and Qt-thread-only state:

- left system monitor
- task terminal inside the Arc Core/HUD, shown only while a long-running task is active
- central animated HUD
- camera feed
- content/quiz/review panels
- activity log
- command input
- interrupt control
- settings/customization overlays
- clipboard panel
- remote-control pairing panel

Thread-safe updates enter through Qt signals such as _log_sig, _state_sig, _content_sig, _camera_sig, _task_sig and related signals.

### JarvisUI

JarvisUI is the public wrapper consumed by main.py.

It exposes:

- lifecycle: on_close, ready
- conversation: on_text_command, on_interrupt, set_state, write_log
- task progress: write_task_log
- plugins: get_plugins, get_plugin_settings, request_say
- wake word: wake_is_ready, wake_get_state, on_wake_toggle, on_wake_manual, on_wake_install
- audio: set_audio_level, push_visemes, on_audio_device_change, ptt_hold, on_push_to_talk
- camera: show_camera_frame, start_camera_stream, stop_camera_stream
- confirmation/content: show_confirm, hide_confirm, show_content, show_quiz, show_review

Never rely on MainWindow-only methods from main.py.

## 5. Conversation Engine: main.py

JarvisLive is responsible for:

- Gemini Live connection and session lifecycle.
- Audio input/output.
- Tool-call dispatch.
- Session resumption.
- Reconnect and backoff.
- Voice and audio-device changes.
- Wake-word state.
- Push-to-talk.
- Cancellation and clean shutdown.
- Session summaries.
- Plugin speech requests.

Tool resolution is conceptually:

    inline tools
        |
        +-- discovered actions
        |
        +-- discovered plugins
        |
        +-- explicit Mark 32 routes

Long-running tool calls are represented as cancellable async tasks so the universal interrupt path can stop them.

## 6. Action System: core/action_loader.py

Actions are self-describing Python modules under actions/.

The loader:

- discovers action files
- validates TOOL declarations
- prevents collisions with inline tools
- creates a unified ActionRegistry

Reusable capabilities should normally be added as action modules rather than making main.py larger.

## 7. Plugin System: core/plugin_loader.py

Plugins are separate from the application core.

The registry:

- discovers plugins
- validates plugin metadata
- prevents tool-name collisions
- exposes plugin tools
- exposes settings schemas to the UI
- supports plugin speech through request_say

Plugins should not reach directly into Qt widgets or depend on the JARVIS color palette.

## 8. Mark 32: core/mark32_engine.py

Mark32Engine is the deterministic autonomous task layer.

Core components:

- CancelToken: cooperative cancellation.
- PermissionSystem: confirmation gates for destructive/external operations.
- TaskStore: SQLite-backed task state/history.
- LongTermMemory: Mark 32 memory adapter.
- TaskPlanner: converts goals into steps.
- Verifier: validates step results.
- ErrorRecovery: recovery policy abstraction.
- ToolRouter: identifies available capabilities for unsupported steps.
- VisionAgent: vision state and monitoring helpers.
- VisualComputerControl: computer interaction.
- AndroidAgent: Android operations.
- FileAgent: filesystem operations.
- TerminalAgent: terminal commands.
- CodingTestingAgent: coding and test operations.
- BrowserAgent: browser actions.
- ClipboardAgent: clipboard operations.
- CameraAgent: camera actions.
- NotificationAgent: notifications.
- SchedulerAgent: scheduled work.
- ContactAgent: contacts/intelligence.
- CommunicationAgent: communications.
- ParallelAgent: independent jobs.

Execution flow:

    user goal
       |
       v
    TaskPlanner.plan()
       |
       v
    step loop
       +-- cancellation check
       +-- deterministic handler
       +-- execute
       +-- Verifier.verify()
       +-- fail when verification fails
       |
       v
    TaskStore.update()
       |
       v
    dashboard state

Mark 32 should never claim an action succeeded without a real tool result and verification.

## 9. New Capability Systems

### Meeting & Call Copilot

- `core/meeting_manager.py` stores an active meeting and local transcript.
- `actions/meeting_copilot.py` starts/stops/status-checks the meeting.
- `main.py` feeds Live `input_transcription` into the active meeting.
- Stopping returns the saved transcript to Gemini for decisions/action-items/follow-up summarization.

### Knowledge Vault

- `core/knowledge_vault.py` maintains a persistent SQLite text index.
- `actions/knowledge_vault.py` indexes selected folders/files and searches source content.
- Supported sources include common source/text formats plus optional DOCX/PDF extraction when the corresponding reader is installed.
- Results include source paths and snippets.

### Workflow Recorder

- `core/workflow_manager.py` stores named workflows in `memory/workflows/`.
- `main.py` records successful action/plugin calls while recording.
- `actions/workflow_recorder.py` starts/stops/lists/runs/deletes workflows.
- Replay is performed directly through the action/plugin registries rather than asking the model to reconstruct the sequence.

### Event Rules

- `core/event_rules.py` stores persistent WHEN/THEN rules.
- Current events: `file_created`, `file_changed`, `process_started`.
- The event worker polls lightweight local state and sends a fired rule back through the normal J.A.R.V.I.S. command path.
- Enabled rules resume automatically on application startup.

### Hardware Diagnostics

- `core/hardware_diagnostics.py` collects CPU, RAM, temperature, battery, disk and Windows physical-disk data.
- Optional `smartctl` discovery can be requested with deep diagnostics.
- It does not automatically stress-test hardware.

### Self-Updater

- `core/self_updater.py` detects the GitHub repository from the Git origin.
- The updater checks the latest `main` commit and can apply only a fast-forward update.
- Dirty working trees are refused; no destructive hard reset is performed.

### Personal Workspaces

- `core/workspace_manager.py` stores persistent workspace profiles.
- Built-in profiles: Coding, Study, Work, Presentation, Travel.
- Profiles store context, description and optional application launch commands.
- Workspace context is injected into the Live system context.

## 10. Operating Modes

Operating modes are separate from personal workspaces.

### Normal

Standard existing behavior.

### Gaming

- Opens Steam.
- Stops only a conservative configurable set of optional desktop/background processes.
- Never targets the J.A.R.V.I.S. process or protected Windows processes.
- Returning to Normal does not guess which closed applications should be relaunched.

### Serious

- Explicitly selected autonomous mode.
- Mark 32 routine confirmation checks are relaxed.
- User-requested Mark 32 file/terminal/device operations can proceed without routine confirmation.
- Windows/OS permissions and UAC still apply.
- Universal interrupt/cancel remains available.

Implementation:
- `core/mode_manager.py`
- `actions/mode_control.py`
- Mark 32 `PermissionSystem` reads the active mode.
- The active mode is appended after the base system prompt so the live policy reflects the current mode.

## 9. Cancellation and Shutdown

### User interrupt

The interrupt path:

1. marks the current conversational turn interrupted
2. cancels active async tool tasks
3. signals file-search cancellation
4. cancels Mark 32 tasks
5. stops current speech/audio work

### Application shutdown

request_shutdown():

1. sets the shutdown flag
2. cancels active tools
3. stops WhatsApp monitoring
4. cancels the run supervisor
5. prevents new executor creation
6. exits the reconnect loop
7. shuts down the custom executor
8. prevents new network/tool work during interpreter shutdown

An interrupt stops the current operation. Shutdown stops the application infrastructure itself.

## 12. Long-Running Task Observability

Slow operations should expose progress in the floating TASK TERMINAL inside the Arc Core/HUD. The terminal is hidden while idle. main.py shows it only for tools classified as long-running, then hides it on completion or error. Interrupt and shutdown also hide it immediately. It is hidden when the full live camera feed replaces the Arc Core surface.

File search currently reports phases such as:

    SEARCHING
    ROOT
    SCANNING: common user folders
    SCANNING: development folders
    SCANNING: available drives
    FOUND
    CANCELLED

main.py also adds tool-level START, COMPLETE, ERROR and CANCELLED messages.

Every new slow action should:

- check cancellation inside loops
- emit useful phase/progress messages
- avoid blocking the Qt main thread

## 13. File Search

actions/file_search_advance.py provides:

- common user-directory search
- development-directory search
- available-drive search
- direct file matching
- folder matching
- exhaustive search
- expensive-directory exclusions
- cooperative cancellation
- task-terminal logging

The Mark 32 deep-search path additionally checks Path.exists() before reporting paths as verified.

## 14. WhatsApp Incoming Calls

actions/whatsapp_incoming_agent.py combines multiple Windows signals.

Screen-color regions alone must not create an incoming-call event because ordinary WhatsApp UI can contain green/red regions that resemble call controls.

Stronger evidence, such as a WhatsApp notification or a direct UI Automation Accept/Decline pair, is required before reporting an incoming call.

## 15. Memory and Configuration

memory/memory_manager.py handles:

- long-term facts
- memory search
- memory trimming
- UI memory listing
- session summaries

memory/config_manager.py handles:

- API key
- assistant/user identity
- voice
- wake-word state
- push-to-talk
- HUD style
- thinking/turn tuning
- proactive audio
- media resolution
- audio devices
- plugin settings

Runtime secrets and personal configuration should remain local and should not be committed to source control.

## 16. Runtime State

Mark 32 and the desktop app maintain local runtime state including:

- memory/mark32/
- memory/reminders.json
- Mark 32 dashboard JSON
- local configuration files under config/

These are runtime data, not application source.

## 17. Threading Model

### Qt main thread

Owns:

- widgets
- painting
- Qt state
- signal/slot handlers

### Async session thread/loop

Owns:

- Gemini Live session
- async receive/send flow
- reconnect supervisor
- tool task orchestration

### Worker threads/executors

Used for:

- filesystem scans
- terminal commands
- plugin execution
- camera work
- blocking integrations
- other slow tasks

Workers must not update Qt widgets directly. They communicate through JarvisUI or Qt signals.

## 18. Error Handling

### Recoverable

Examples include:

- network timeout
- optional capability unavailable
- invalid API key
- unsupported optional Live configuration
- user cancellation
- plugin/action loading failure

These should be logged and recovered where possible.

### Startup contract errors

A missing JarvisUI bridge is a programming error. It should be detected before runtime by compile/static checks and by keeping all main.py UI dependencies in the JarvisUI contract.

### Shutdown errors

No new executor task, network operation or background reconnect should be started once shutdown begins.

## 19. Development Rules

1. Put reusable tools in actions/.
2. Put cross-cutting engine logic in core/.
3. Keep runtime data in memory/ and config/.
4. Keep the Qt boundary inside ui.py.
5. Add every new main.py UI dependency to JarvisUI.
6. Never report a result that a tool did not actually return.
7. Long-running work must support cooperative cancellation.
8. Long-running work should provide visible progress when useful.
9. Destructive/external actions must pass the permission/confirmation layer.
10. Never commit API keys or other secrets.

## 20. Regression Checks

Before launching:

    python -m py_compile main.py ui.py core/mark32_engine.py actions/file_search_advance.py actions/mark32_advance.py actions/whatsapp_incoming_agent.py

Then test:

1. Application startup.
2. Text command.
3. Voice turn.
4. Interrupt during speech.
5. Interrupt during file search.
6. Close during a running task.
7. File-search results in the content panel.
8. Mark 32 execution.
9. Mark 32 cancellation.
10. Wake-word settings.
11. Camera start/stop.
12. Plugin discovery.
13. Invalid-API-key recovery.

A release should not be considered healthy until startup, interrupt, cancellation and clean shutdown all complete without traceback loops.

## 21. Current Startup Reliability Fixes

The current main/ui boundary includes these protections:

- JarvisUI.write_task_log() is exposed by the public wrapper.
- Wake-word callback bridges are explicitly exposed.
- Plugin speech request_say is explicitly exposed.
- JarvisUI.glance() delegates to the real HUD instead of an undefined wrapper field.
- main.py uses JarvisUI.ready rather than reaching into a private _win field.
- Task-terminal registration has a safe fallback to the normal activity logger.
- Shutdown/cancellation logic prevents background work from restarting during interpreter shutdown.
- File search cooperatively checks cancellation.

This file is the architectural contract for future Mark 32 changes.

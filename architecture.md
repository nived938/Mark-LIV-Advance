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
- live TASK TERMINAL
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

## 10. Long-Running Task Observability

Slow operations should expose progress in the left TASK TERMINAL.

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

## 11. File Search

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

## 12. WhatsApp Incoming Calls

actions/whatsapp_incoming_agent.py combines multiple Windows signals.

Screen-color regions alone must not create an incoming-call event because ordinary WhatsApp UI can contain green/red regions that resemble call controls.

Stronger evidence, such as a WhatsApp notification or a direct UI Automation Accept/Decline pair, is required before reporting an incoming call.

## 13. Memory and Configuration

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

## 14. Runtime State

Mark 32 and the desktop app maintain local runtime state including:

- memory/mark32/
- memory/reminders.json
- Mark 32 dashboard JSON
- local configuration files under config/

These are runtime data, not application source.

## 15. Threading Model

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

## 16. Error Handling

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

## 17. Development Rules

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

## 18. Regression Checks

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

## 19. Current Startup Reliability Fixes

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

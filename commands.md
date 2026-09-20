# J.A.R.V.I.S. Command Examples

This file lists practical commands for the new Mark 32 capability layer.

## Operating modes

Say:

- "Gaming mode"
- "Start gaming mode"
- "Normal mode"
- "Turn off gaming mode"
- "Serious mode"
- "Turn off serious mode"

Gaming mode opens Steam and attempts to stop only the configured optional background apps.

## Meeting Copilot

- "Start a meeting called Project Sync."
- "What is the meeting status?"
- "Stop the meeting and summarize it."

While a meeting is active, microphone input transcription is captured locally. Stopping the meeting saves a transcript and asks J.A.R.V.I.S. to summarize decisions, action items and unresolved questions.

## Knowledge Vault

- "Index G:\Coding into my Coding knowledge vault."
- "Search my knowledge vault for authentication."
- "Show knowledge vault status."

Index selected folders once, then ask questions that should be grounded in the indexed sources.

## Workflow Recorder

- "Start recording a workflow called Open My Dev Setup."
- Perform the normal J.A.R.V.I.S. actions.
- "Stop recording the workflow."
- "Run Open My Dev Setup."
- "List my workflows."

Workflows record action/plugin calls, not arbitrary voice text.

## Event Rules

- "When a PDF appears in Downloads, tell me."
- "When file test.txt changes, tell me."
- "When Steam starts, tell me."

The event engine uses lightweight local polling and sends the THEN instruction back through the normal J.A.R.V.I.S. command path.

## Hardware Diagnostics

- "Run a hardware diagnostic."
- "Run a deep hardware diagnostic."

Deep diagnostics optionally use smartctl when it is installed.

## Self-Updater

- "Check for a J.A.R.V.I.S. update."
- "Update J.A.R.V.I.S."

The updater refuses to overwrite a dirty Git working tree and never performs a destructive hard reset.

## Personal Workspaces

- "Switch to Coding workspace."
- "Switch to Study workspace."
- "Create a Photography workspace."
- "List my workspaces."

Workspace context is loaded into the Live system context on the next session build and also returned by the workspace tool when changed.

## Developer validation

```bat
python scripts\check_ui_contract.py
python -m py_compile main.py ui.py core\mark32_engine.py actions\file_search_advance.py actions\mark32_advance.py actions\whatsapp_incoming_agent.py
```

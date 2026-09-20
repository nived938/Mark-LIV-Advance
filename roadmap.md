# New Feature Roadmap

These are deliberately new product capabilities, not upgrades to existing J.A.R.V.I.S. features.

## 1. Meeting & Call Copilot

A dedicated meeting mode that can capture a permitted meeting conversation, create a live transcript, identify topics, produce decisions, extract action items, and generate a clean follow-up summary.

What makes it new:
- a dedicated meeting workspace
- meeting timeline
- speaker labels
- decision/action-item extraction
- post-meeting summary artifact

## 2. Knowledge Vault

A separate semantic knowledge system for user-selected folders, notes and reference material.

What makes it new:
- document ingestion pipeline
- local indexing
- semantic retrieval
- source-linked answers
- collections such as School, Coding, Projects, Personal

It is not just file search: it builds a persistent knowledge space that can answer questions across many documents.

## 3. Workflow Recorder

A visual recorder that lets the user perform a task once and save it as a reusable workflow.

Example:
```
Open browser
-> open a website
-> click the dashboard
-> export report
-> save result
```

Later:
```
"Run my weekly report workflow."
```

The important new capability is recording and naming workflows, not merely asking the existing agent to perform the task again.

## 4. Multi-User Identity

Support multiple people on the same PC with separate profiles.

Each profile gets:
- name and preferences
- selected voice
- memory namespace
- permissions
- custom shortcuts
- personal workflows

Optional local speaker recognition can switch profiles without requiring a login account.

## 5. Event Rules Engine

A true event-driven automation system, separate from normal time-based reminders.

Example:

```
WHEN USB drive is connected
IF it contains photos
THEN offer to import them
```

Other event sources:
- application opened
- file changed
- device connected
- network changed
- battery threshold
- Bluetooth device appears
- Windows notification detected

This is new because it adds condition/event triggers rather than another scheduler/reminder.

## 6. Hardware Diagnostics Center

A dedicated diagnostic subsystem that can inspect hardware health and produce actionable reports.

Possible checks:
- storage SMART health
- memory tests
- CPU/GPU stress diagnostics
- temperature history
- driver/device error reports
- network adapter diagnostics

It would produce a diagnostic report rather than just displaying current telemetry.

## 7. Secure Credential Vault

A native encrypted vault for API keys, service credentials and tokens.

Capabilities:
- OS-protected encryption
- scoped credentials per action/plugin
- no plaintext credentials in normal config
- credential rotation reminders
- audit history for credential use

This is a separate security product capability rather than an extension of ordinary configuration.

## 8. Plugin Marketplace

Turn the current plugin architecture into a discoverable ecosystem.

The marketplace would provide:
- searchable plugins
- categories
- version information
- compatibility metadata
- install/update/remove
- signatures or integrity checks
- permission summaries before installation

The new feature is plugin discovery and lifecycle management, not the existing plugin loader itself.

## 9. J.A.R.V.I.S. Self-Updater

A safe application update subsystem.

Flow:

```
Check update
-> show version/change summary
-> download
-> verify package
-> create restore point
-> install
-> restart
```

Required protections:
- signed/verified update package
- rollback on failed startup
- previous-version retention
- no update during critical user tasks

## 10. Personal Workspace Modes

Create persistent context modes such as:

- Coding
- Study
- Gaming
- Work
- Travel
- Presentation

Each workspace can define:
- preferred applications
- screen layout
- assistant tone/verbosity
- relevant knowledge collection
- notification rules
- shortcuts
- startup actions
- temporary context

This is a new context/workspace system, not a replacement for the existing task agent.

## Suggested implementation order

1. Meeting & Call Copilot
2. Knowledge Vault
3. Workflow Recorder
4. Event Rules Engine
5. Hardware Diagnostics Center
6. Secure Credential Vault
7. Multi-User Identity
8. Personal Workspace Modes
9. Plugin Marketplace
10. J.A.R.V.I.S. Self-Updater

The order is an implementation roadmap only; it is not a quality ranking.

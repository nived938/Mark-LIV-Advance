# J.A.R.V.I.S. Future Plan

> Status: planning document. These capabilities describe the long-term direction and are not claims about the current Mark 32 desktop build.

## Product Vision

The long-term goal is to make J.A.R.V.I.S. a personal AI that follows the user across devices rather than an assistant that exists only inside the Windows PC.

The system should have two equal nodes:

- J.A.R.V.I.S. Desktop on the Windows PC
- J.A.R.V.I.S. Mobile on the Android phone

The key requirement is that the phone remains useful when the PC is completely powered off.

When the PC is off, the phone becomes the active J.A.R.V.I.S. node. It can converse, use phone tools, maintain memory, queue desktop tasks, and synchronize everything automatically when the PC comes back online.

The future architecture should not depend on Google authentication and should support local-first, privacy-focused operation.

---

# 1. Two-Device J.A.R.V.I.S. Architecture

## Desktop Node

The Windows installation remains the high-power execution node.

It can provide:

- full computer control
- desktop applications
- terminal and development tools
- multi-monitor vision
- large local files
- high-resource automation
- PC hardware diagnostics
- desktop notifications
- long-running workflows
- desktop camera and audio
- the existing Mark32 automation engine

The desktop should expose a small authenticated J.A.R.V.I.S. device bridge instead of exposing the entire application remotely.

## Mobile Node

The phone becomes the always-available companion node.

It can provide:

- voice conversation
- local chat
- phone sensors
- phone camera
- microphone
- notifications
- contacts
- calendar
- phone applications
- mobile-specific automation
- location-aware actions
- local model inference
- queued commands for the PC

The phone should be a real J.A.R.V.I.S. runtime, not just a remote-control screen.

---

# 2. What Happens When the PC Is OFF?

This is a core requirement of the future architecture.

Example:

The PC is shut down.

The user says on the phone:

"Remember that I need to finish the school website tomorrow."

The phone stores the memory locally.

The user then says:

"When my PC is online, open the project and continue from where I stopped."

Because the PC is offline, the phone cannot directly perform the desktop operation.

Instead:

1. The phone classifies the request as a PC task.
2. The task is stored in an encrypted outgoing queue.
3. The task receives a unique ID and creation timestamp.
4. The phone tells the user that the task is waiting for the PC.
5. When the PC becomes available, the desktop bridge reconnects.
6. The queued task is transferred.
7. The PC executes it through Mark32.
8. The result is synchronized back to the phone.
9. The phone can show the result even when the user is away from the PC.

For tasks that need the PC to become available immediately, optional Wake-on-LAN can be supported. This only works when the PC and network hardware are configured for Wake-on-LAN.

---

# 3. Memory Synchronization

The desktop and phone should share one logical J.A.R.V.I.S. memory while keeping local copies.

## Recommended model

Use a local-first replicated event log rather than copying an entire database blindly.

Each memory record should contain:

- globally unique ID
- source device ID
- creation timestamp
- update timestamp
- type
- content
- metadata
- revision number
- deletion/tombstone state

This allows the phone and PC to create memories independently while offline.

## Sync direction

### Phone -> PC

New phone memories are uploaded when the PC becomes available.

### PC -> Phone

New PC memories are sent to the phone.

### PC <-> Phone

Updates are reconciled by stable IDs and revisions.

## Offline changes

Both devices may change data while disconnected.

Each device keeps an outbound queue. When a connection returns, queued operations are exchanged and reconciled.

## Conflict strategy

The first implementation can use:

- unique operation IDs
- per-record revisions
- deterministic conflict rules
- deletion tombstones
- conflict records for cases requiring user review

Important information should never disappear just because one device was offline.

---

# 4. Memory Storage Layers

The future system should separate canonical memory from search indexes.

## Canonical memory

Store the real memory records locally in encrypted SQLite.

## Search index

Each device can build its own FTS or vector/search index from canonical records.

Indexes can therefore be rebuilt without losing the underlying memory.

## Attachments

Photos, audio, documents and other large files should use a separate attachment store.

Memory records keep references and metadata instead of duplicating large files unnecessarily.

---

# 5. Sync Transport

The system should use a layered connection strategy.

## Layer 1: Local network

When the PC and phone are on the same Wi-Fi:

- discover the trusted device
- establish a secure local connection
- synchronize quickly
- transfer large files directly

## Layer 2: Secure relay

When the devices are on different networks:

- use an encrypted outbound channel
- support store-and-forward messages
- synchronize queued work
- reconnect automatically

The relay should not need to know the user's private memory contents.

Ideally, sensitive memory payloads are encrypted on the source device before they leave that device.

## Layer 3: Direct reconnection

When the devices return to the same local network, the system can switch back to direct synchronization.

---

# 6. Device Pairing

The first desktop-to-phone connection should be simple.

## Pairing flow

1. Open Phone Connection on the PC.
2. J.A.R.V.I.S. creates a short-lived pairing session.
3. The PC displays a QR code.
4. The phone scans the QR code.
5. Both devices exchange public identity information.
6. Each device stores the other as trusted.
7. The temporary pairing secret expires.

The QR code must not contain a permanent master password.

The user should be able to:

- rename the device
- revoke the device
- see connection status
- see last-seen time
- remove a trusted device
- rotate device keys
- disconnect all devices

---

# 7. PC Task Queue

The phone needs a dedicated PC Task Queue.

Suggested states:

- WAITING_FOR_PC
- PC_ONLINE
- RECEIVED
- RUNNING
- COMPLETED
- FAILED
- CANCELLED
- EXPIRED
- NEEDS_USER_INPUT

The queue should display:

- task description
- creation time
- device
- current state
- progress
- result
- error
- retry action

The phone can therefore remain useful even when the PC disappears.

---

# 8. Shared Conversation Continuity

A conversation should not belong to only one device.

Example:

On the PC:

"Open my Python project and inspect the failing tests."

Later on the phone:

"What did you find?"

J.A.R.V.I.S. should understand the relevant context.

The synchronization layer should support:

- conversation IDs
- user messages
- assistant messages
- important tool results
- task IDs
- compact conversation summaries

Large raw conversations can remain local while useful summaries and references are synchronized.

---

# 9. Phone-Only Mode

The phone should show a dedicated PHONE-ONLY MODE when the PC is unavailable.

In this state:

- the mobile model remains active
- phone tools remain available
- desktop tools are queued
- memory remains available
- conversations continue
- offline operation is explicit

The assistant must never claim that a desktop task was completed while the PC is offline.

Example response:

"The PC is offline. I queued that task for the next desktop connection."

---

# 10. PC-Connected Mode

When the PC is reachable, J.A.R.V.I.S. becomes a distributed assistant.

Example:

"Open the Coding workspace on my PC."

The request path is:

Phone -> Sync/Device Bridge -> Desktop J.A.R.V.I.S. -> Mark32 -> Result -> Phone

The phone should display remote task progress and final results.

---

# 11. Wake and Reconnect

Possible behavior:

### PC was shut down

The phone keeps queued work.

### PC wakes

Wake-on-LAN can optionally start the machine when hardware and network configuration support it.

### Desktop J.A.R.V.I.S. starts

The desktop reconnects using its trusted device identity.

### Synchronization begins

Memory, conversation summaries, device state and task events are exchanged.

### Queue resumes

Eligible desktop tasks continue.

The user should be able to decide which queued tasks are allowed to start automatically.

---

# 12. Security Model

Remote control is a sensitive capability, so the future multi-device architecture should treat every device as an authenticated node.

Required principles:

- every device has a unique identity
- connections are authenticated
- sensitive payloads are encrypted
- pairing credentials expire
- device revocation is supported
- remote commands are auditable
- the user can disconnect devices
- device permissions are configurable
- Serious mode does not bypass device authentication

Remote execution should remain visible in the task history.

---

# 13. Suggested Technical Architecture

## Android

Recommended direction:

- Kotlin
- Jetpack Compose
- Room or SQLite
- WorkManager
- Android notification APIs
- local speech and audio stack
- on-device model runtime

## Desktop

Keep the current:

- Python
- PyQt6
- Mark32 engine
- local memory
- action/plugin system

Add a small device bridge service beside the desktop application.

## Synchronization

Recommended concepts:

- HTTPS and/or WebSocket transport
- local-network discovery
- encrypted operation log
- public-key device identity
- resumable sync
- store-and-forward queue

## Optional relay

A future self-hosted relay can run on a small server, home machine or cloud VM.

The product should remain useful without requiring a permanent third-party service.

---

# 14. Development Phases

## Phase 1 — Mobile Foundation

Build the Android J.A.R.V.I.S. runtime.

Goals:

- chat
- voice
- local memory
- phone tools
- offline detection
- local model
- device identity

## Phase 2 — Desktop Bridge

Add:

- trusted-device pairing
- QR pairing
- desktop online/offline state
- secure request channel
- task queue

## Phase 3 — Shared Memory

Add:

- operation IDs
- synchronization
- conflict handling
- memory merge
- attachment references
- sync history

## Phase 4 — Remote PC Control

Add:

- remote task submission
- progress
- cancellation
- results
- optional PC wake support

## Phase 5 — Unified J.A.R.V.I.S.

Add:

- shared conversation continuity
- shared preferences
- cross-device context
- unified notifications
- distributed workflows
- intelligent device selection

## Phase 6 — Offline-First Intelligence

Make the phone a complete standalone J.A.R.V.I.S. when the PC is unavailable.

Goals:

- local model
- local tools
- local memory
- queued desktop tasks
- offline conversation
- delayed execution
- battery-aware background behavior

---

# 15. Example End-to-End Future Experience

## Morning

The PC is OFF.

The user speaks to the phone.

J.A.R.V.I.S. can still:

- answer questions
- read today's phone calendar
- remember tasks
- process phone files
- use the phone camera
- manage phone notifications

## Queue a desktop task

"When my PC turns on, open my Coding workspace and run the tests."

Phone response:

"Desktop is offline. The task is queued."

## Later

The PC is powered on.

Desktop J.A.R.V.I.S. connects.

The phone receives:

"Your desktop is online. One queued task is ready."

The desktop executes it.

Phone response:

"The test run finished. Four tests failed."

## Evening

The user adds a new memory on the phone.

Later, that memory is synchronized to the PC.

Both devices now share the updated information.

This is the core experience: one J.A.R.V.I.S., multiple devices, local intelligence, persistent memory and graceful operation when a device disappears.

---

# 16. New Feature Ideas — 30 Standalone Capabilities

These are intentionally new product capabilities rather than extensions of the existing Mark32 systems.

## 1. Cross-Device Continuity Hub

A single control center showing every trusted J.A.R.V.I.S. device, connection state, battery, last-seen time and active tasks.

## 2. Smart Home Control Center

Control supported lights, plugs, fans, thermostats and other smart-home equipment with natural language.

## 3. TV and Media Remote

Use the phone as a J.A.R.V.I.S. voice remote for supported TVs and media players.

## 4. Car Companion Mode

Provide a simplified in-car interface for navigation, messages, reminders and hands-free commands.

## 5. NFC Action Triggers

Touch an NFC tag to start a predefined J.A.R.V.I.S. behavior such as Study, Work or Leave Home.

## 6. QR Action Cards

Create printable QR codes that launch predefined J.A.R.V.I.S. actions when scanned.

## 7. Geofence Automations

Trigger selected actions when entering or leaving chosen places.

## 8. Network Device Discovery

Show computers, phones, printers, TVs and other devices discovered on the local network.

## 9. Internet Connection Diagnostics

Provide a dedicated dashboard for latency, packet loss, DNS failures and connectivity state.

## 10. Wi-Fi Analyzer

Show nearby Wi-Fi networks, channel usage and signal strength for network troubleshooting.

## 11. Printer Control Center

Discover printers, show queues, pause or cancel jobs and send supported print tasks.

## 12. Battery Charging Assistant

Track charging sessions and provide configurable charge and battery-saving notifications.

## 13. Data Usage Monitor

Track mobile and Wi-Fi data consumption by application and notify the user near selected limits.

## 14. Privacy Center

A single dashboard showing J.A.R.V.I.S. access to microphone, camera, files, notifications, location and trusted devices.

## 15. Screen-Time Companion

Track application usage and provide optional breaks, schedules and focus notifications.

## 16. Emergency Contact Mode

Provide a dedicated emergency screen for selected contacts, important information and predefined emergency actions.

## 17. Live Interpreter

Perform two-way spoken language translation during conversations.

## 18. Presentation Remote

Use the phone as a wireless presentation controller for the PC.

## 19. Streamer Control Deck

Provide a phone control surface for streaming scenes, recordings, timers and status.

## 20. Home Inventory

Maintain a private inventory of household devices, tools, appliances and other items with photos and metadata.

## 21. Warranty Tracker

Track product purchase dates, warranty periods, receipts and expiration reminders.

## 22. Package Tracker

Maintain shipment references and notify the user about expected delivery events.

## 23. Personal Expense Ledger

Record expenses by voice or text, categorize them and produce local summaries.

## 24. Receipt Organizer

Capture receipts with the phone camera and organize merchant, date and amount data.

## 25. Cooking Assistant

Turn available ingredients into recipes, timers and step-by-step cooking guidance.

## 26. Grocery Manager

Build grocery lists by voice, organize them by store section and remember recurring purchases.

## 27. Outfit Planner

Maintain a private wardrobe catalog and generate outfit combinations from stored clothing items.

## 28. School Timetable

Maintain classes, exam dates, assignment dates and daily study blocks in a dedicated student workspace.

## 29. Personal Journal

Provide a private local-first journal with voice entry, tags, search and optional reflection prompts.

## 30. Digital Legacy and Recovery Vault

Store recovery instructions, important device information, software setup notes and selected emergency documentation in an encrypted offline vault.

---

# 17. Long-Term Goal

The final J.A.R.V.I.S. should not feel like a chatbot installed on a PC.

It should feel like a personal AI system that lives across the user's devices.

The long-term system should provide:

- independent PC and phone J.A.R.V.I.S. nodes
- useful phone operation while the PC is off
- safe queued desktop actions
- two-way memory synchronization
- cross-device conversation continuity
- trusted and revocable devices
- local processing wherever practical
- optional cloud infrastructure
- explicit offline/online state
- honest task completion reporting
- user control over synchronization and remote execution

The strategic goal is to evolve J.A.R.V.I.S. from a desktop assistant into a persistent personal computing agent.

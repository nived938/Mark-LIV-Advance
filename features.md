# J.A.R.V.I.S. Features & Test Commands

This is the practical feature catalog for the J.A.R.V.I.S. desktop project. Each implemented feature has a short description and a natural-language command for testing.

## Start
Run from the repository root:

    python main.py

For source validation:

    python scripts\check_ui_contract.py
    python -m py_compile main.py ui.py core\mark32_engine.py core\mode_manager.py core\access_control.py core\device_services.py core\public_api_hub.py actions\jarvis_services.py actions\public_api.py

Some features require Windows permissions, an installed application, a microphone/camera, or internet access.

---

# 1. Core AI and Conversation

## 1. Live AI Conversation
Description: Real-time voice conversation through the Gemini Live session.
Test: Hello JARVIS, how are you?

## 2. Voice Input
Description: Captures microphone speech for the Live session.
Test: What is the current time?

## 3. Voice Output
Description: Streams J.A.R.V.I.S. responses to the selected output device.
Test: Say system voice output test complete.

## 4. Audio Device Settings
Description: Selects/configures microphone and speaker devices.
Test: Open audio device settings.

## 5. Push-to-Talk
Description: Optional microphone gating until the configured PTT control is held.
Test: Enable push to talk.

## 6. Wake Word
Description: Optional local Hey Jarvis wake-word mode.
Test: Enable wake word.

## 7. Universal Interrupt
Description: Stops active responses and cooperatively cancels supported long-running work.
Test: Start a long file search, then press Esc.

## 8. Session Resumption
Description: Keeps the Live resumption handle in memory for reconnects.
Test: Reconnect JARVIS.

## 9. Long-Term Memory
Description: Stores selected user facts locally.
Test: Remember that I use VS Code for coding.

## 10. Memory Recall
Description: Searches saved memory for relevant stored information.
Test: What do you remember about my coding editor?

---

# 2. Computer Control

## 11. App Launcher
Description: Opens desktop applications.
Test: Open Notepad.

## 12. Browser Agent
Description: Opens and interacts with supported browser pages.
Test: Open the browser and open GitHub.

## 13. Web Search
Description: Searches the web for current information.
Test: Search the web for the latest Python release.

## 14. Terminal Agent
Description: Runs terminal commands for system and development tasks.
Test: Run ipconfig and show me the result.

## 15. Coding Agent
Description: Inspects and works with software projects.
Test: Inspect my current project and find Python files.

## 16. Automatic Testing Agent
Description: Runs requested validation and test commands.
Test: Run the Python syntax checks for this project.

## 17. Natural-Language File Manager
Description: Finds and manages files through natural language.
Test: Find README.md in my Coding folder.

## 18. Deep File Search
Description: Searches configured drives and project locations exhaustively with cancellation support.
Test: Search every drive for files named README.md.

## 19. File Operations
Description: Supports supported file move, rename and delete operations subject to permissions.
Test: Rename test.txt to test2.txt.

## 20. Clipboard Intelligence
Description: Uses clipboard content as an assistant input and action source.
Test: Copy text, then say what is on my clipboard?

## 21. Screen Vision
Description: Captures and analyzes a current screen frame.
Test: Look at my screen and tell me what is open.

## 22. Camera Vision
Description: Captures a single webcam frame for visual analysis.
Test: Look at my camera and tell me what you see.

## 23. Embedded Camera
Description: Shows live webcam video inside the J.A.R.V.I.S. HUD.
Test: Open camera.

## 24. Camera Photo
Description: Saves the currently displayed camera frame as a JPEG.
Test: Take a camera photo.

## 25. Multi-Monitor Vision
Description: Supports monitor-focused screen analysis.
Test: Look at my second monitor.

## 26. Visual Computer Control
Description: Combines screen understanding and computer input automation.
Test: Look at the current window and click the visible Settings button.

## 27. Android Agent
Description: Uses the existing desktop-side Android control path.
Test: Check my connected Android device.

## 28. WhatsApp Incoming-Call Detection
Description: Watches Windows notification/UI signals for WhatsApp incoming calls; generic screen colors alone are not enough.
Test: Monitor WhatsApp for an incoming call.

## 29. System Status
Description: Reports CPU, RAM, GPU-related and process information where available.
Test: What is my computer status?

## 30. Background Monitoring
Description: Maintains selected topic/process monitoring rules.
Test: List my monitors.

---

# 3. Mark32 Agent Layer

## 31. Autonomous Task Planner
Description: Breaks larger goals into Mark32 task steps.
Test: Plan a task to inspect my Coding folder and report Python projects.

## 32. Self-Verification
Description: Verifies task outputs before success is reported.
Test: Verify that test.txt exists before reporting success.

## 33. Error Recovery
Description: Provides recovery infrastructure around failed Mark32 operations.
Test: Try the requested task and recover if a step fails.

## 34. Intelligent Tool Router
Description: Routes natural-language requests to the appropriate registered capability.
Test: Find my README and tell me its path.

## 35. Multi-Step Agent
Description: Coordinates several tools for one user goal.
Test: Find my latest Python project, inspect its files, and report the main entry point.

## 36. Permission and Safety System
Description: Applies operation-specific permission rules and confirmation requirements.
Test: Delete a test file.

## 37. Parallel Task Execution
Description: Runs independent supported work concurrently.
Test: Check these folders in parallel: G:\Coding and G:\Projects.

## 38. Live Task Dashboard / Task Terminal
Description: Shows long-running task progress inside the Arc Core HUD.
Test: Search every drive for all .log files.

## 39. Goal-Based Conversation
Description: Treats a larger objective as a continuing task context.
Test: My goal is to prepare my coding environment for tomorrow.

## 40. Universal Cancel
Description: Provides a common interruption path across supported task tools.
Test: Start an exhaustive search, then say stop the task.

---

# 4. New Mark32 Capability Systems

## 41. Meeting & Call Copilot
Description: Captures permitted Live microphone transcription, stores a transcript, and generates meeting summaries.
Test: Start a meeting called Project Sync.
Finish: Stop the meeting and summarize it.
Note: Current implementation does not independently diarize multiple external speakers.

## 42. Knowledge Vault
Description: Persistent local content index for selected folders and documents.
Test: Index G:\Coding into my Coding knowledge vault.
Search: Search my knowledge vault for authentication.
Status: Show knowledge vault status.

## 43. Workflow Recorder
Description: Records successful action/plugin calls and replays them as named workflows.
Test: Start recording a workflow called Open My Dev Setup.
Finish: Stop recording the workflow.
Replay: Run Open My Dev Setup.

## 44. Event Rules Engine
Description: Local WHEN/THEN rules triggered by supported file and process events.
Test: When test.txt changes, tell me.

## 45. Hardware Diagnostics Center
Description: Reports CPU, RAM, battery, temperature, disk and Windows storage information.
Test: Run a hardware diagnostic.

## 46. J.A.R.V.I.S. Self-Updater
Description: Detects the GitHub repo, compares local/remote main and safely updates a clean checkout.
Test: Check for a JARVIS update.
Update: Update JARVIS.

## 47. Personal Workspace System
Description: Persistent contextual workspaces such as Coding, Study, Work, Presentation and Travel.
Test: Switch to Coding workspace.
Other: List my workspaces.

---

# 5. Operating Modes

## 48. Normal Mode
Description: Standard J.A.R.V.I.S. operation and normal friendly/helpful tone.
Test: Normal mode.

## 49. Gaming Mode
Description: Opens Steam and stops only the configured conservative list of optional background applications.
Test: Gaming mode.

## 50. Serious Mode
Description: Enables Serious-mode Mark32 permissions and changes the assistant to a direct professional style.
Test: Serious mode.
Expected: Interface switches to a red danger theme and the header shows SERIOUS MODE.

## 51. Serious Theme Restoration
Description: Restores the previous normal accent palette when Serious mode ends.
Test: Serious mode, then Normal mode.
Expected: Red danger theme returns to the previous normal theme without restarting.

---

# 6. Secure Access

## 52. Startup Access Gate
Description: Blocks normal AI session startup until the user unlocks J.A.R.V.I.S.
Test: Restart J.A.R.V.I.S. and observe the Secure Access screen.

## 53. Local Password Authentication
Description: Stores a salted password hash locally for startup unlock.
Test: Enter the correct password, then restart and test an incorrect password.

## 54. Voice Passphrase Unlock
Description: Optional spoken passphrase unlock.
Test: On the Secure Access screen, choose Voice Unlock and say the configured phrase.
Note: This is spoken-passphrase recognition, not high-assurance biometric speaker identification.

---

# 7. Location, Map, Network and Personal Utilities

## 55. IP Location
Description: Estimates approximate location from an IP address.
Test: Find the location of my public IP.
Note: IP geolocation is approximate, not GPS.

## 56. Saved Device Locations
Description: Stores named device location records with coordinates or IP data.
Test: Save my phone as a device at latitude 12.5 longitude 75.0.

## 57. Device Location Lookup
Description: Loads a saved device and can display its location on the map.
Test: Show the location of my phone.

## 58. Google Find My Device View
Description: Opens the user's Find My Device page inside the J.A.R.V.I.S. webview.
Test: Find my phone.
Note: J.A.R.V.I.S. does not scrape private Google account/device coordinates.

## 59. Embedded Location Map
Description: Displays Google Maps content in-app without a normal visible address bar.
Test: Show Kanhangad on the map.

## 60. Geofences
Description: Stores a location/radius rule and checks enter/leave state.
Test: Create a 100 meter geofence around latitude 12.5 longitude 75.0 called Home.

## 61. Network Device Discovery
Description: Uses Windows ARP/neighbour information to identify local devices.
Test: Show devices on my local network.

## 62. Internet Diagnostics
Description: Tests DNS, HTTP reachability, ping on Windows, and public-IP information.
Test: Run an internet connection diagnostic.

## 63. Wi-Fi Analyzer
Description: Lists visible Windows WLAN networks, signal, channel and authentication.
Test: Analyze the Wi-Fi networks around me.

## 64. Screen-Time Tracking
Description: Tracks active-window usage locally and reports today's totals.
Test: Start screen-time tracking.
Status: Show my screen time.

## 65. Data Usage Monitor
Description: Reports system network bytes and active connection information.
Test: Show my network data usage.
Note: Current Windows implementation does not claim exact per-process byte totals.

## 66. Presentation Remote
Description: Sends supported presentation navigation keys.
Test: Next slide.

---

# 8. QR Code Features

## 67. Camera QR Scanner
Description: Reuses the embedded camera stream to scan for QR codes.
Test: Scan the QR code with the camera.

## 68. Screen QR Scanner
Description: Captures the desktop and decodes a visible QR code.
Test: Scan the QR code on my screen.

## 69. Second-Monitor QR Scanner
Description: Targets monitor 2 for screen QR scanning.
Test: Scan the QR code on the second screen.

## 70. QR URL Opening
Description: Opens decoded HTTP/HTTPS QR destinations; other QR text is returned as text.
Test: Point a QR URL at the camera and say scan it.

---

# 9. Public API Hub

The 20 selected Public APIs are integrated in core/public_api_hub.py and exposed to J.A.R.V.I.S. through actions/public_api.py.

Important: You do not manually paste these API URLs into config/api_keys.json. The 20 selected services are already coded into the hub. For future key-based integrations, secrets should be stored locally in config/api_keys.json and the integration code must read them. Never commit secrets to GitHub.

## 71. Open-Meteo
Description: Weather forecasts and related meteorological data.
Test: What is the weather in Kanhangad?

## 72. Nominatim
Description: Forward and reverse geocoding.
Test: Find the coordinates of Kanhangad.

## 73. IPinfo
Description: IP information and approximate network geolocation.
Test: Look up my public IP location.

## 74. Sunrise and Sunset
Description: Sunrise and sunset times for coordinates.
Test: Get sunrise and sunset for latitude 12.5 longitude 75.0.

## 75. Frankfurter
Description: Currency exchange rates and conversion.
Test: Convert 100 USD to EUR using Frankfurter.

## 76. World Time & Weather
Description: Time and timezone information.
Test: What time is it in Asia/Kolkata using World Time and Weather?

## 77. RainViewer
Description: Weather radar map metadata.
Test: Get the current RainViewer radar map data.

## 78. NASA
Description: NASA science and astronomy data using the APOD endpoint.
Test: Show today's NASA Astronomy Picture of the Day.
Note: Current implementation uses NASA DEMO_KEY.

## 79. Open Library
Description: Book search and bibliographic metadata.
Test: Search Open Library for books about Python.

## 80. Free Dictionary
Description: Definitions, pronunciation and examples.
Test: Look up asynchronous in the Free Dictionary.

## 81. Jikan
Description: MyAnimeList-derived anime information.
Test: Search Jikan for One Piece.

## 82. Kroki
Description: Produces a diagram URL from diagram text.
Test: Create a simple Mermaid Start-to-Finish diagram using Kroki.

## 83. JSONPlaceholder
Description: Safe fake REST data for integration testing.
Test: Get sample users from JSONPlaceholder.

## 84. AviationWeather
Description: Aviation weather and METAR data.
Test: Get the METAR for airport ICAO VOCI.

## 85. SWAPI
Description: Star Wars data.
Test: Look up Star Wars character 1 with SWAPI.

## 86. Crossref
Description: Scholarly publication metadata search.
Test: Search Crossref for artificial intelligence papers.

## 87. Gutendex
Description: Project Gutenberg book search.
Test: Search Gutenberg books for Frankenstein.

## 88. Hacker News
Description: Technology and startup stories.
Test: Show the top Hacker News stories.

## 89. MusicBrainz
Description: Music artist and release metadata.
Test: Search MusicBrainz for Daft Punk.

## 90. OpenLigaDB
Description: Football league and match data.
Test: Get OpenLigaDB Bundesliga match data.

---

# 10. Communication and Productivity

## 91. Calendar Agent
Description: Uses the configured calendar integration.
Test: Show my calendar for today.

## 92. Email Agent
Description: Uses the configured email integration.
Test: Check my email.

## 93. Unified Communication Agent
Description: Unified path for supported communication actions.
Test: Show my communication options.

## 94. Contact Intelligence
Description: Finds and works with supported contacts.
Test: Find my contact for John.

## 95. Proactive Notifications
Description: Surfaces configured proactive alerts and information.
Test: Show my proactive notifications.

## 96. Task Scheduler
Description: Creates persistent scheduled tasks/reminders.
Test: Remind me tomorrow at 9 AM to check my project.

## 97. OCR / Document Processing
Description: Processes supported images/documents and extracts text when the tool is available.
Test: Process the current document and extract its text.

## 98. File Processor
Description: Processes supported documents and media files.
Test: Process the selected PDF and summarize it.

## 99. Browser / Website Interaction
Description: Uses browser tools to inspect and interact with supported websites.
Test: Open the browser and inspect the current page.

---

# 11. User Interface

## 100. Arc Core HUD
Description: Main J.A.R.V.I.S. holographic interface.
Test: Start J.A.R.V.I.S.

## 101. Live Audio Waveform
Description: Visualizes current audio levels.
Test: Speak while J.A.R.V.I.S. is listening.

## 102. Avatar Viseme Animation
Description: Animates the avatar mouth during J.A.R.V.I.S. speech.
Test: Tell me a long sentence.

## 103. Mode Indicator
Description: Shows NORMAL, GAMING or SERIOUS state in the header.
Test: Serious mode.

## 104. Red Serious Theme
Description: Full danger-style red theme while Serious mode is active.
Test: Serious mode.

## 105. Floating Task Terminal
Description: Places long-task terminal output inside the Arc Core HUD.
Test: Search every drive for all Python files.

## 106. Embedded Map Webview
Description: Displays map/location web content without a normal visible address bar.
Test: Show Kanhangad on the map.

## 107. Embedded Camera Webview
Description: Displays live camera video inside the app.
Test: Open camera.

## 108. Phone Remote Dashboard
Description: Existing dashboard allows compatible phone/browser remote interaction.
Test: Open remote control.

---

# 12. Configuration

## 109. Assistant Identity Customization
Description: Changes the displayed assistant name and identity settings.
Test: Change my assistant name to Friday.

## 110. Normal UI Accent Customization
Description: Changes the normal interface accent while preserving the separate Serious red theme.
Test: Change my interface color to purple.

## 111. Voice Selection
Description: Stores the selected Live voice and reconnects when needed.
Test: Change my JARVIS voice.

## 112. Configuration Persistence
Description: Keeps supported settings across restarts.
Test: Restart JARVIS and check that my settings remain.

---

# 13. Future Features

These items are planned, not current live features. They have no live test command yet.

## 113. Cross-Device Continuity Hub
Description: One dashboard for trusted PC and phone J.A.R.V.I.S. nodes.
Status: Planned.

## 114. Android J.A.R.V.I.S. Standalone Node
Description: Full phone installation that remains useful while the PC is off.
Status: Planned.

## 115. PC-Phone Two-Way Memory Sync
Description: Local-first replicated memory between desktop and phone.
Status: Planned.

## 116. Offline PC Task Queue
Description: Phone queues desktop work until the PC reconnects.
Status: Planned.

## 117. Secure Device Pairing
Description: QR pairing with trusted-device identity and revocation.
Status: Planned.

## 118. Remote PC Wake
Description: Optional Wake-on-LAN support for queued desktop tasks.
Status: Planned.

## 119. Shared Conversation Continuity
Description: Continue the same conversation between phone and desktop.
Status: Planned.

## 120. Secure Credential Vault
Description: Native encrypted storage for service credentials and tokens.
Status: Planned.

## 121. Multi-User Identity
Description: Separate profiles with individual memory, preferences and permissions.
Status: Planned.

## 122. Plugin Marketplace
Description: Discover, install, update and remove J.A.R.V.I.S. plugins.
Status: Planned.

## 123. Smart Home Control Center
Description: Natural-language control of compatible smart-home devices.
Status: Planned.

## 124. TV and Media Remote
Description: Voice control for supported TVs and media devices.
Status: Planned.

## 125. Car Companion Mode
Description: Simplified hands-free driving interface.
Status: Planned.

## 126. NFC Action Triggers
Description: NFC tags launch selected J.A.R.V.I.S. actions.
Status: Planned.

## 127. QR Action Cards
Description: Physical QR cards launch predefined actions.
Status: Planned.

## 128. Advanced Cross-Device Geofencing
Description: Phone location events trigger distributed PC/phone workflows.
Status: Planned.

## 129. Printer Control Center
Description: Discover printers and manage supported print queues.
Status: Planned.

## 130. Battery Charging Assistant
Description: Charging history and battery-focused notifications.
Status: Planned.

## 131. Live Interpreter
Description: Two-way spoken language translation.
Status: Planned.

## 132. Streamer Control Deck
Description: Phone-based controls for streaming scenes and recording.
Status: Planned.

## 133. Home Inventory
Description: Private catalog of household equipment.
Status: Planned.

## 134. Warranty Tracker
Description: Tracks purchases, warranties and expiration dates.
Status: Planned.

## 135. Package Tracker
Description: Tracks shipments and delivery events.
Status: Planned.

## 136. Personal Expense Ledger
Description: Local voice/text expense tracking.
Status: Planned.

## 137. Receipt Organizer
Description: Camera-based receipt capture and organization.
Status: Planned.

## 138. Cooking Assistant
Description: Ingredient-based recipes, timers and cooking guidance.
Status: Planned.

## 139. Grocery Manager
Description: Intelligent shopping lists and recurring items.
Status: Planned.

## 140. Outfit Planner
Description: Private wardrobe catalog and outfit combinations.
Status: Planned.

## 141. Personal Journal
Description: Local-first private journal with voice entry and search.
Status: Planned.

## 142. Digital Legacy and Recovery Vault
Description: Encrypted recovery instructions and important documentation.
Status: Planned.

---

# 14. Public API Testing Notes

Internet access is required for Public API tests. External services can change, rate-limit or go offline.

Generic command pattern:

    Use the public API service open_meteo for weather in Kanhangad.

Useful examples:

    Use Open-Meteo for weather in Kanhangad.
    Use Nominatim to geocode Kanhangad.
    Use Frankfurter to convert 100 USD to EUR.
    Use Open Library to find Python books.
    Use the Free Dictionary to define asynchronous.
    Use NASA to show today's APOD.
    Use Hacker News to show the top stories.

Location note: IP geolocation is approximate and should not be described as GPS tracking.

QR note: Camera QR scanning reuses the same embedded camera stream so it does not open a second webcam handle.

Voice access note: the current voice unlock is spoken-passphrase recognition, not a strong biometric identity system.

---

# 15. Main Implementation Files

main.py — Live session supervisor, tool dispatch, reconnect and audio lifecycle.
ui.py — PyQt6 interface, HUD, camera, task terminal, access gate and map webview.
core/mark32_engine.py — Mark32 planning, verification, permissions and automation engine.
core/mode_manager.py / actions/mode_control.py — Normal, Gaming and Serious modes.
core/workspace_manager.py / actions/workspace_control.py — persistent workspaces.
core/meeting_manager.py / actions/meeting_copilot.py — Meeting Copilot.
core/knowledge_vault.py / actions/knowledge_vault.py — Knowledge Vault.
core/workflow_manager.py / actions/workflow_recorder.py — Workflow Recorder.
core/event_rules.py / actions/event_rules.py — Event Rules Engine.
core/hardware_diagnostics.py / actions/hardware_diagnostics.py — hardware diagnostics.
core/self_updater.py / actions/self_updater.py — self updater.
core/access_control.py — local startup password and voice passphrase storage/verification.
core/device_services.py / actions/jarvis_services.py — location, network, geofence, QR and utility services.
core/public_api_hub.py / actions/public_api.py — selected Public API integrations.
scripts/check_ui_contract.py — UI contract validation.
Feuture-Plan.md — long-term phone + PC architecture and future roadmap.
features.md — this feature and testing catalog.

# 16. Feature Status Rule

Only features in the implemented sections should be treated as available for testing.
Planned features must be moved into the implemented sections once their real code exists.
Never claim a feature completed when the underlying tool returned an error, timeout or unavailable status.
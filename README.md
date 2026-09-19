# Mark-LIV Advance

Advanced capability pack for [Mark-LIV](https://github.com/FatihMakes/Mark-LIV).

This repository is intentionally built as an upgrade layer: the upstream Mark-LIV engine provides the Gemini Live voice/UI/session system, while this repository adds a self-registering action pack for PC control, screen capture, mouse/keyboard, web search, browser automation, files, terminal, memory, reminders, notifications, email, calendar, clipboard, and WhatsApp.

## Setup

1. Run `python setup_advance.py`.
2. The script downloads the upstream Mark-LIV engine into this project and preserves the Advance action files.
3. Install dependencies with `python -m pip install -r requirements-advance.txt`.
4. Configure the Gemini API key using the upstream Mark-LIV setup.
5. Run `python main.py`.

Destructive actions such as deleting files, sending messages, sending email, and starting WhatsApp calls are confirmation-gated by the action itself or by the upstream confirmation system.

## Added capabilities

- PC/application control
- screenshots and screen information
- mouse and keyboard control
- web search
- browser opening/automation
- advanced file search and file operations
- PowerShell/terminal execution
- long-term local memory
- clipboard management
- reminders
- desktop notifications
- calendar helpers
- email helpers
- WhatsApp Web helpers
- multi-step tool-friendly actions

The action modules use the same `TOOL` self-registration pattern used by modern Mark-LIV builds.

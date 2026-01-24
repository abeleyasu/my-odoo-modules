# My Odoo Modules

Repository for custom Odoo 18 modules ready for the Odoo App Store.

## Modules

### 1. jitsi_meet_ui (O-Meet)
**Google Meet-style video conferencing for Odoo 18**

- 📹 Instant and scheduled meetings
- 🔗 Public join links (no login required)
- 📅 Calendar integration
- 🔐 JWT authentication support
- 🎨 Modern Google Meet-inspired UI

### 2. office_document_creator
**Google Drive-like document management for Odoo Community Edition**

- 📝 Create Word, Excel, PowerPoint documents
- ✏️ ONLYOFFICE integration for editing
- 📂 Folder organization
- 🔗 Document sharing
- 🗑️ Trash and restore functionality

### 3. alkez_appointment
**Appointment scheduling and booking for Odoo 18**

- 🗓️ Public booking pages
- ✅ Online confirmations and reminders
- 🔒 Staff availability and calendars

### 4. RingCentral Suite (bundle)
**All RingCentral modules packaged in a single bundle folder**

- 📞 Voice, SMS, WebRTC, Recording, AI, Voicemail
- 🧩 CRM, Sales, Project, Helpdesk, HR integrations
- 📊 Analytics, compliance, and quality tools

## Structure

Each module is in its own folder at the repository root, following Odoo App Store requirements:

```
my-odoo-modules/
├── jitsi_meet_ui/              # O-Meet module
│   ├── static/description/
│   │   ├── icon.png           # 256x256 PNG icon
│   │   ├── index.html         # Rich HTML description
│   │   └── images/            # Screenshots
│   ├── doc/
│   │   └── index.rst          # Documentation
│   ├── LICENSE                # LGPL-3 license
│   └── __manifest__.py        # Module manifest
│
├── office_document_creator/   # Office module
    ├── static/description/
    │   ├── icon.png           # 256x256 PNG icon
    │   ├── index.html         # Rich HTML description
    │   └── images/            # Screenshots
    ├── doc/
    │   └── index.rst          # Documentation
    ├── LICENSE                # LGPL-3 license
    └── __manifest__.py        # Module manifest

├── alkez_appointment/         # Appointment module
│   ├── static/description/
│   ├── LICENSE
│   └── __manifest__.py

└── ringcentral_suite/          # RingCentral bundle folder
    ├── ringcentral_suite/      # Main suite module
    ├── ringcentral_base/       # Core API integration
    ├── ringcentral_call/       # Voice calling
    ├── ringcentral_sms/        # SMS/MMS
    ├── ringcentral_webrtc/     # Softphone
    ├── ringcentral_recording/  # Recording
    ├── ringcentral_ai/         # AI transcription
    ├── ringcentral_voicemail/  # Voicemail
    ├── alkez_ringcentral_fax/  # Fax
    └── ...                     # Other RingCentral integrations
```

## Installation

1. Clone this repository
2. Copy desired module folder to your Odoo addons path
3. Update apps list in Odoo
4. Install the module from Apps menu

## License

- Repository: MIT License
- Modules: LGPL-3 (see LICENSE file in each module folder)

## Odoo Version

All modules are compatible with **Odoo 18.0** (Community and Enterprise Edition)

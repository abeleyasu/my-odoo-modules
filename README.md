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
└── office_document_creator/   # Office module
    ├── static/description/
    │   ├── icon.png           # 256x256 PNG icon
    │   ├── index.html         # Rich HTML description
    │   └── images/            # Screenshots
    ├── doc/
    │   └── index.rst          # Documentation
    ├── LICENSE                # LGPL-3 license
    └── __manifest__.py        # Module manifest
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

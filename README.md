# My Odoo Modules

Repository for custom Odoo 18 modules ready for the Odoo App Store.

## 💎 Commercial Modules

Both modules are **paid/proprietary software** licensed under OPL-1 (Odoo Proprietary License).

## Modules

### 1. O-Meet (jitsi_meet_ui) - $200 USD
**Google Meet-style video conferencing for Odoo 18**

- 📹 Instant and scheduled meetings
- 🔗 Public join links (no login required)
- 📅 Calendar integration
- 🔐 JWT authentication support
- 🎨 Modern Google Meet-inspired UI

**Price:** $200 USD (one-time)  
**License:** OPL-1

### 2. Office Document Creator - $250 USD
**Google Drive-like document management for Odoo Community Edition**

- 📝 Create Word, Excel, PowerPoint documents
- ✏️ ONLYOFFICE integration for editing
- 📂 Folder organization
- 🔗 Document sharing
- 🗑️ Trash and restore functionality

**Price:** $250 USD (one-time)  
**License:** OPL-1

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
│   ├── LICENSE                # OPL-1 license
│   └── __manifest__.py        # Module manifest
│
└── office_document_creator/   # Office module
    ├── static/description/
    │   ├── icon.png           # 256x256 PNG icon
    │   ├── index.html         # Rich HTML description
    │   └── images/            # Screenshots
    ├── doc/
    │   └── index.rst          # Documentation
    ├── LICENSE                # OPL-1 license
    └── __manifest__.py        # Module manifest
```

## Installation

1. Clone this repository
2. Copy desired module folder to your Odoo addons path
3. Update apps list in Odoo
4. Install the module from Apps menu

## License

- Repository: MIT License
- Modules: OPL-1 (Odoo Proprietary License) - Paid modules (see LICENSE file in each module folder)

## Odoo Version

All modules are compatible with **Odoo 18.0** (Community and Enterprise Edition)

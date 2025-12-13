# Odoo App Store Publishing Guide

This document provides step-by-step instructions for publishing your custom Odoo modules on the Odoo App Store.

## ✅ Pre-Publishing Checklist

Both modules (`jitsi_meet_ui` and `office_document_creator`) are now properly structured and ready for the Odoo App Store. Here's what has been completed:

### Module Structure ✅
- [x] Each module is in a separate folder at the repository root
- [x] Proper directory structure following Odoo standards
- [x] All required files are in place

### Icons ✅
- [x] **jitsi_meet_ui**: 256x256 PNG icon at `static/description/icon.png`
- [x] **office_document_creator**: 256x256 PNG icon at `static/description/icon.png`
- [x] PNG format (not SVG or other formats)
- [x] Proper dimensions (256x256 pixels)

### Descriptions ✅
- [x] Rich HTML description at `static/description/index.html` for both modules
- [x] Professional formatting with features, screenshots, and use cases
- [x] Clear installation and usage instructions

### Documentation ✅
- [x] RST documentation at `doc/index.rst` for both modules
- [x] Comprehensive documentation including:
  - Overview and features
  - Installation instructions
  - Configuration guide
  - Usage examples
  - Troubleshooting

### Screenshots ✅
- [x] Multiple screenshots in `static/description/images/` folder
- [x] Main screenshot (main_screenshot.png) for featured image
- [x] Additional feature screenshots
- [x] All images in PNG format
- [x] Manifest 'images' key properly configured

### License ✅
- [x] LGPL-3 license file in each module folder
- [x] License key in manifest set to 'LGPL-3'
- [x] Compatible with Odoo Community Edition (LGPL-3)

### Manifest Files ✅
- [x] Proper module metadata (name, version, category, summary)
- [x] All dependencies listed
- [x] Images key with screenshots
- [x] License specified
- [x] Author and website information
- [x] Installable flag set to True
- [x] Application flag set to True

## 📋 Module Details

### jitsi_meet_ui (O-Meet)

**Name:** O-Meet (Jitsi)  
**Technical Name:** jitsi_meet_ui  
**Version:** 1.1.0  
**Category:** Discuss  
**License:** LGPL-3  
**Odoo Version:** 18.0

**Dependencies:**
- base
- web
- website
- calendar

**External Dependencies:**
- Python: jwt (PyJWT)

**Key Features:**
- Instant and scheduled meetings
- Public join links (no login required)
- Calendar integration
- JWT authentication
- Google Meet-style UI

### office_document_creator

**Name:** Office Document Creator  
**Technical Name:** office_document_creator  
**Version:** 18.0.4.0.0  
**Category:** Productivity  
**License:** LGPL-3  
**Odoo Version:** 18.0

**Dependencies:**
- base
- mail
- onlyoffice_odoo

**Key Features:**
- Create Word, Excel, PowerPoint documents
- ONLYOFFICE integration
- Folder organization
- Document sharing
- Trash and restore

## 🚀 Publishing Steps

### 1. Prepare Your Repository

Your repository is already properly structured! Each module is in its own folder:

```
my-odoo-modules/
├── jitsi_meet_ui/
└── office_document_creator/
```

### 2. Make Repository Public

If your repository is private, you need to:

**Option A: Make it public** (recommended for free distribution)

**Option B: Grant access to Odoo**
- GitHub: Add `online-odoo` user as collaborator (NOT `odoo-online`)
- GitLab: Add `OdooApps` (apps@odoo.com) user
- Bitbucket: Add Odoo's SSH public key

### 3. Repository URL Format

Use SSH URL format when registering:

```
ssh://git@github.com/abeleyasu/my-odoo-modules#18.0
```

Format: `ssh://git@gitServer(:port)/mypath#version`

**Important:**
- Use SSH URL (not HTTPS)
- Include branch/version after `#` (e.g., `#18.0`)
- No passwords should be in the URL
- Port is optional (use colon if needed)

### 4. Register on Odoo Apps Store

1. Go to https://apps.odoo.com/
2. Sign in with your Odoo account
3. Click "Publish Your App"
4. Fill in repository details:
   - Repository URL: `ssh://git@github.com/abeleyasu/my-odoo-modules#18.0`
   - Select branch/version: 18.0
5. Odoo will scan your repository and find both modules

### 5. Module Registration

For each module (jitsi_meet_ui and office_document_creator):

1. **Basic Information** (auto-filled from manifest):
   - Name
   - Technical name
   - Summary
   - Category
   - License

2. **Description** (auto-loaded from index.html):
   - Rich HTML description with features
   - Screenshots and images
   - Use cases and benefits

3. **Pricing** (choose one):
   - Free
   - Paid (set price)
   - Freemium

4. **Support**:
   - Support options
   - Contact information
   - Documentation links

5. **Publishing**:
   - Review all information
   - Submit for review
   - Wait for approval (if applicable)

## 📝 Post-Publishing

### Updating Modules

When you update your modules:

1. Update version in `__manifest__.py`
2. Commit and push changes to GitHub
3. Odoo Apps Store will auto-detect updates
4. New version appears on your app page

### Marketing Your Modules

1. **Write Good Descriptions**
   - Clear feature list ✅ (already done)
   - Use cases ✅ (already done)
   - Screenshots ✅ (already done)

2. **Engage with Users**
   - Respond to reviews
   - Answer questions
   - Provide support

3. **Keep Modules Updated**
   - Fix bugs quickly
   - Add requested features
   - Maintain compatibility

## ⚠️ Important Rules to Follow

### R1. No Stealing or Cheating
- Don't copy others' work without permission
- Give proper credit according to licenses
- No cheating on ratings

### R2. No Dynamic Code Loading
- No downloading code at runtime
- No installing executable code
- No obfuscated/encrypted code

### R3. Transparent Features
- All features documented
- No hidden functionality
- Description matches actual behavior

### R4. User Consent for Data Collection
- Explicitly mention any data collection
- Link to Privacy Policy
- Get user consent

### R5. Respect Other Authors
- Don't harm others' reputation
- Proper attribution
- No false authorship

### R6. Provide Support
- Help customers who bought your module
- Respond to support requests
- Fix reported bugs

## 🔍 Module Compatibility

### jitsi_meet_ui Dependencies

**Compatible with:**
- LGPL-3 ✅
- GPL-3 ✅
- AGPL-3 ✅

**PyJWT (MIT License):** Compatible with LGPL-3 ✅

### office_document_creator Dependencies

**Required:**
- onlyoffice_odoo module (check its license)

**Important:** Verify onlyoffice_odoo license compatibility before publishing.

## 📊 Expected Review Process

1. **Automatic Checks**
   - Repository access
   - Module structure
   - Icon format and size
   - Manifest validation

2. **Manual Review** (may be required)
   - Code quality
   - Security issues
   - License compliance
   - Description accuracy

3. **Approval**
   - Module appears on Apps Store
   - Available for users to install

## 🛠️ Testing Before Publishing

### Local Testing

Test both modules thoroughly:

```bash
# Install in test database
odoo-bin -d test_db -i jitsi_meet_ui --stop-after-init
odoo-bin -d test_db -i office_document_creator --stop-after-init

# Test all features
# Check error logs
# Verify dependencies
```

### Test Installation from Repository

```bash
# Clone fresh copy
git clone ssh://git@github.com/abeleyasu/my-odoo-modules.git
cd my-odoo-modules

# Verify structure
ls -la jitsi_meet_ui/
ls -la office_document_creator/

# Check required files
ls jitsi_meet_ui/static/description/icon.png
ls jitsi_meet_ui/static/description/index.html
ls jitsi_meet_ui/LICENSE
```

## 📞 Support Contacts

- **Odoo Apps Support:** https://www.odoo.com/help
- **Community Forum:** https://www.odoo.com/forum
- **Developer Documentation:** https://www.odoo.com/documentation/18.0/

## 🎉 You're Ready!

Your modules are now properly structured and ready for the Odoo App Store!

**Next Steps:**
1. Choose your pricing model (Free/Paid/Freemium)
2. Prepare support channels (email, forum, etc.)
3. Register your repository on apps.odoo.com
4. Submit modules for review
5. Start helping users!

## 📝 Additional Notes

### Branch Strategy

Consider creating version-specific branches:
- `18.0` - Current Odoo 18 version (create this branch)
- `17.0` - If you backport to Odoo 17
- `main` - Development branch

**To create 18.0 branch:**
```bash
git checkout -b 18.0
git push origin 18.0
```

Then use this URL for App Store:
```
ssh://git@github.com/abeleyasu/my-odoo-modules#18.0
```

### Maintainer Information

Update manifest author and website fields with your information:
- Author: Your Company/Name
- Website: Your website/GitHub profile
- Support: Your support email

### Screenshots Quality

For better presentation, consider:
- Taking actual application screenshots
- Using high-resolution images
- Showing real functionality
- Adding annotations/highlights

The current placeholder screenshots work for publishing, but real screenshots will attract more users!

---

**Good luck with your Odoo App Store modules! 🚀**

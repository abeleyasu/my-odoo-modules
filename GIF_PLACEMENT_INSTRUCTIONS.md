# GIF Placement Instructions

## Overview

The Office Document Creator module's description page (index.html) has been updated to include animated GIF demonstrations. The GIF files need to be placed in the correct location for them to display properly.

## Required GIF Files

The following GIF files are referenced in the Office Document Creator description:

1. **One-Click Creation.gif** - Demonstrates creating documents with one click
2. **One-Click Creation 2.gif** - Alternative view of document creation
3. **Real-Time Editing.gif** - Shows real-time document editing with ONLYOFFICE
4. **_Multi-Format Upload.gif** - Demonstrates multi-format file upload
5. **Smart Sharing.gif** - Shows document sharing functionality
6. **Trash & Restore.gif** - Demonstrates trash and restore features

## Where to Place GIF Files

All GIF files should be placed in:

```
office_document_creator/static/description/
```

This is the same directory where `index.html` is located.

### Directory Structure

```
office_document_creator/
├── static/
│   └── description/
│       ├── icon.png
│       ├── icon.svg
│       ├── index.html
│       ├── images/
│       │   ├── main_screenshot.png
│       │   ├── feature_1.png
│       │   ├── feature_2.png
│       │   └── feature_3.png
│       ├── One-Click Creation.gif          <- Place here
│       ├── One-Click Creation 2.gif         <- Place here
│       ├── Real-Time Editing.gif            <- Place here
│       ├── _Multi-Format Upload.gif         <- Place here
│       ├── Smart Sharing.gif                <- Place here
│       └── Trash & Restore.gif              <- Place here
```

## Steps to Add GIF Files

1. **Upload GIFs to the repository:**
   ```bash
   cd /path/to/my-odoo-modules
   cp /path/to/your/gifs/*.gif office_document_creator/static/description/
   ```

2. **Verify the files are in place:**
   ```bash
   ls -la office_document_creator/static/description/*.gif
   ```

3. **Update the manifest images list** (optional but recommended):
   
   Edit `office_document_creator/__manifest__.py` and add the GIFs to the `images` list:
   ```python
   'images': [
       'static/description/images/main_screenshot.png',
       'static/description/images/feature_1.png',
       'static/description/images/feature_2.png',
       'static/description/images/feature_3.png',
       'static/description/One-Click Creation.gif',
       'static/description/One-Click Creation 2.gif',
       'static/description/Real-Time Editing.gif',
       'static/description/_Multi-Format Upload.gif',
       'static/description/Smart Sharing.gif',
       'static/description/Trash & Restore.gif',
   ],
   ```

4. **Commit and push:**
   ```bash
   git add office_document_creator/static/description/*.gif
   git add office_document_creator/__manifest__.py  # if you updated it
   git commit -m "Add GIF demonstrations for features"
   git push
   ```

## GIF File Requirements

For best display on the Odoo App Store:

- **Format:** GIF (animated)
- **Recommended dimensions:** 800-1200px width (responsive)
- **File size:** Keep under 5MB per GIF for fast loading
- **Frame rate:** 10-15 fps for smooth animation
- **Colors:** Optimize color palette to reduce file size

## How They Display

In the updated `index.html`:

1. **One-Click Creation** section shows both GIFs stacked vertically
2. Each other feature section shows one GIF
3. GIFs are styled with:
   - Rounded corners (border-radius: 8px)
   - Shadow effect for depth
   - Responsive width (max-width: 100%)
   - Center alignment

## Verification

After adding the GIFs, you can verify they work by:

1. Opening `office_document_creator/static/description/index.html` in a browser
2. Checking that all GIF animations load and play
3. Testing the Odoo App Store preview (if already published)

## Notes

- The HTML file has been pre-configured with proper image tags
- GIF file names must match exactly (including spaces and special characters)
- If GIF files have different names, update the `<img src="...">` tags in `index.html`
- All GIFs should demonstrate actual functionality of the module

## Current Status

✅ HTML description updated with GIF references
✅ Pricing information added ($250 USD)
✅ License changed to OPL-1
⏳ GIF files need to be uploaded to the repository

Once the GIF files are uploaded, the module will be ready for publishing to the Odoo App Store!

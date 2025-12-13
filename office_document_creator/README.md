# Office Document Creator for Odoo 18

## Overview
This module provides a "Google Drive-like" document creation and management experience within Odoo Community Edition, seamlessly integrated with ONLYOFFICE. It allows users to create, edit, and organize Word, Excel, and PowerPoint documents directly from Odoo without needing the Enterprise "Documents" app.

## Key Features
*   **One-Click Creation:** Create new Word (`.docx`), Excel (`.xlsx`), and PowerPoint (`.pptx`) documents from a beautiful dashboard.
*   **Seamless ONLYOFFICE Integration:** Documents open directly in the ONLYOFFICE editor for real-time editing.
*   **Folder Organization:** Organize documents into nested folders.
*   **Sharing & Permissions:** Documents are private by default but can be shared with other users.
*   **Premium UI:** A modern, card-based dashboard interface for a professional user experience.

## Technical Architecture
*   **Custom Models:**
    *   `office.document`: Stores document metadata and links to the physical file.
    # Office Document Creator — Odoo Module

    This module provides server-side document creation and conversion tools inside Odoo. It generates office documents (ODT/DOCX/PDF) from templates, fills them with Odoo data (records, partners, and reports), and optionally converts them to PDF for download or email.

    **Module path:** `/opt/odoo/custom_addons/office_document_creator`

    **Module version:** v1.0.0

    Purpose
    - Generate office documents (ODT/DOCX) from templates with variable substitution.
    - Convert generated office documents to PDF for download, sharing, or email.
    - Integrate with Odoo workflows (sales, invoices, HR letters) and with attachments storage.

    **High-level architecture**
    - Odoo: Hosts the module and runs the template rendering and file-generation logic. Typical components:
        - Models to store templates and generation rules.
        - Wizards to capture user choices (target record, format, recipient).
        - Controllers to serve download URLs (if required).
    - Conversion layer (choose one):
        - LibreOffice (headless) / UNO bridge: runs on the same server and converts ODT/DOCX to PDF.
        - `pandoc` / third-party converters for specialized workflows.
        - Optional HTTP conversion microservice (containerized) that accepts a document and returns a converted file.
    - Storage: Odoo `ir.attachment` by default. Optionally S3/MinIO for scale-out storage.

    Components and roles
    - `odoo` — application server executing generation and storing attachments.
    - `libreoffice` — optional headless converter used for reliable ODT/DOCX→PDF conversions.
    - `conversion service` — optional external service for conversions in isolated environments.

    Odoo configuration parameters (set via `ir.config_parameter`)
    - `office_document_creator.converter` — preferred converter: `libreoffice`, `pandoc`, or `service`.
    - `office_document_creator.libreoffice.cmd` — libreoffice command prefix (default: `libreoffice --headless --convert-to pdf --outdir`).
    - `office_document_creator.service.url` — URL of an external conversion microservice (e.g. `http://127.0.0.1:8000/convert`).
    - `office_document_creator.storage_backend` — `local` or `s3`.
    - `office_document_creator.s3.endpoint` — S3/MinIO endpoint (if using S3-compatible storage).
    - `office_document_creator.s3.bucket` — bucket name for attachments (optional).

    Where the module uses these: Generation and conversion code consults `ir.config_parameter` to select the converter and its command or service URL.

    Installation
    1. Place `office_document_creator` in your `addons_path` (e.g. `/opt/odoo/custom_addons/`).
    2. Update apps list and install the module from Apps or run as `odoo` user:

    ```bash
    sudo -u odoo python3 /opt/odoo/odoo-18/odoo-bin -d <your_db> -u office_document_creator --stop-after-init
    ```

    3. If you plan to use `libreoffice` headless conversion, install LibreOffice on the server:

    ```bash
    # Debian/Ubuntu example
    sudo apt update
    sudo apt install -y libreoffice
    ```

    4. If using an external conversion microservice, deploy it and set `office_document_creator.service.url` accordingly.

    Usage
    - Create a template record (module may provide a model like `office.template`) and upload an ODT/DOCX template file.
    - From the target record (invoice, sale order, employee), open the module's wizard/action (e.g., "Generate document") and select template + output format.
    - The generated file is stored as an `ir.attachment`; download or attach to the record/email.

    Example: Generate Invoice PDF
    1. Open an Invoice form.
    2. Click `Generate Document` (or the module's provided action).
    3. Choose the invoice template and output `PDF`.
    4. Click `Generate` and download or send the attachment.

    Reverse proxy / web notes
    - If the module exposes download endpoints, ensure your reverse proxy (nginx) forwards requests to Odoo. Large conversions may require increased proxy body size and timeouts.

    Common issues & troubleshooting
    - Converted PDF corrupt or empty:
        - Check converter logs (LibreOffice stdout/stderr). Capture the command output when conversion is run.
        - Ensure conversion command can write to the output directory or temporary directory.
    - `libreoffice` not found:
        - Install LibreOffice or set `office_document_creator.converter` to `service` and use an external converter.
    - Timeouts on large docs:
        - Increase worker, systemd, or proxy timeouts.
    - Placeholders not replaced:
        - Confirm templating syntax used by the module and that context fields exist on target records.
    - Attachments missing or inaccessible:
        - Check `ir.attachment` access rights and `res_model`/`res_id` values.

    Troubleshooting checklist
    1. Verify template renders locally using Odoo shell.
    2. Tail Odoo logs for conversion errors: `sudo journalctl -u odoo -f`.
    3. Manually run LibreOffice conversion to reproduce:

    ```bash
    libreoffice --headless --convert-to pdf --outdir /tmp /path/to/example.odt
    ```

    4. If using a service: `curl -F "file=@/path/to/file.odt" "${office_document_creator.service.url}"` and inspect responses.

    Useful commands (on server)
    ```bash
    # Manual conversion (LibreOffice)
    libreoffice --headless --convert-to pdf --outdir /tmp /path/to/file.odt

    # Tail Odoo logs
    sudo journalctl -u odoo -f

    # Check a system parameter via Odoo shell
    sudo -u odoo python3 /opt/odoo/odoo-18/odoo-bin shell -d <your_db> -c "from odoo import registry; env = registry('<your_db>').cursor().env; print(env['ir.config_parameter'].sudo().get_param('office_document_creator.converter'))"
    ```

    Testing steps
    1. Create a simple template with a placeholder.
    2. Generate a document for a sample record and download it.
    3. If PDF conversion is enabled, verify the PDF opens in a browser.
    4. For smoke tests, run the generation flow from Odoo shell and assert an `ir.attachment` is created.

    Security notes
    - Secure any external conversion service behind an internal network or authentication.
    - Sanitize templates that accept user-supplied content to avoid injection risks.
    - Restrict template creation/upload permissions to trusted roles.

    Where to look in this module
    - `models/` — template models and generation logic (e.g. `office.template`, `office.generator`).
    - `wizards/` — user-facing generation wizards.
    - `controllers/` — file download endpoints or webhooks.
    - `data/` — demo templates and default settings.
    - `tests/` — unit/integration tests (if present).

    If you want, I can add an `UPGRADE.md` with commands to install LibreOffice, deploy a containerized converter, or provide sample systemd service files for background workers. Tell me if you want that included.

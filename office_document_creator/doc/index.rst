==========================================
Office Document Creator
==========================================

Overview
========

Office Document Creator brings Google Drive-like document management to Odoo Community Edition.
Create, edit, and organize Word, Excel, and PowerPoint documents with seamless ONLYOFFICE integration.

Features
========

Document Creation
-----------------

Create documents with one click:

* **Word Documents** (.docx): Letters, reports, proposals
* **Excel Spreadsheets** (.xlsx): Data analysis, budgets, tables
* **PowerPoint Presentations** (.pptx): Slides, presentations
* **Text Files** (.txt): Quick notes, plain text

Document Editing
----------------

Real-time editing with ONLYOFFICE:

* Edit documents directly in browser
* No desktop software required
* Auto-save functionality
* Full Microsoft Office compatibility
* Collaborative editing support

Organization
------------

Organize documents efficiently:

* **Folders**: Create nested folder hierarchy
* **Starred**: Mark important documents
* **Recent**: Quick access to recent files
* **Shared**: Documents shared with you
* **Trash**: Safe deletion with restore

File Management
---------------

Comprehensive file operations:

* Upload multiple file formats (PDF, CSV, RTF, etc.)
* Drag-and-drop file upload
* Make copies of documents
* Download documents
* Move to folders
* Delete and restore

Sharing
-------

Share documents securely:

* Share with specific users
* Share via links
* Control access permissions
* Track shared documents
* Private by default

Storage Analytics
-----------------

Monitor storage usage:

* Total storage used
* Breakdown by document type
* Number of documents
* Storage statistics

Installation
============

Prerequisites
-------------

* Odoo 18.0 Community Edition
* ONLYOFFICE Document Server
* onlyoffice_odoo connector module

ONLYOFFICE Setup
----------------

**Option 1: Cloud Service**

1. Sign up for ONLYOFFICE cloud service
2. Get Document Server URL
3. Configure in Odoo

**Option 2: Self-Hosted**

1. Deploy ONLYOFFICE Document Server
2. Install onlyoffice_odoo module
3. Configure server URL

Module Installation
-------------------

1. Install onlyoffice_odoo module first
2. Place office_document_creator in addons path
3. Update apps list
4. Install "Office Document Creator"
5. Configure ONLYOFFICE connection

Configuration
=============

ONLYOFFICE Connector
--------------------

Configure via Settings → General Settings → ONLYOFFICE:

* Document Server URL
* JWT Secret (for security)
* Connection timeout
* Test connection

Access Rights
-------------

Two security groups:

* **Office User**: Create and manage own documents
* **Office Manager**: Full access to all documents

Module Settings
---------------

Configure via Settings → Technical → System Parameters:

* Storage backend (local/S3)
* Default folder structure
* File size limits

Usage
=====

Creating Documents
------------------

**From Dashboard:**

1. Go to Office → Dashboard
2. Click document type button:
   
   * "Word Document"
   * "Excel Spreadsheet"
   * "PowerPoint Presentation"
   * "Text File"

3. Document opens in ONLYOFFICE editor
4. Start editing
5. Changes save automatically

**From My Drive:**

1. Go to Office → My Drive
2. Click "Create" button
3. Select document type
4. Fill in details
5. Click "Create & Edit"

Editing Documents
-----------------

1. Open document from any view
2. Click "Edit" button
3. ONLYOFFICE editor opens in new tab
4. Make changes
5. Close tab when done (auto-saved)

Organizing Documents
--------------------

**Create Folders:**

1. Go to My Drive
2. Click "New Folder"
3. Enter folder name
4. Save

**Move Documents:**

1. Select document
2. Click "Move to Folder"
3. Choose destination folder
4. Confirm

**Drag and Drop:**

* Drag documents between folders
* Drag files from computer to upload
* Reorganize folder structure

Sharing Documents
-----------------

1. Open document
2. Click "Share" button
3. Add users or generate link
4. Set permissions
5. Share link via email/chat

Uploading Files
---------------

**Single File:**

1. Click "Upload" button
2. Select file
3. Choose destination folder
4. Upload

**Multiple Files:**

1. Drag files to dashboard
2. Drop in target area
3. Files upload automatically

Using Starred
-------------

Mark important documents:

1. Open document
2. Click star icon
3. Access via "Starred" menu

Working with Trash
------------------

**Delete Document:**

1. Select document
2. Click "Delete"
3. Document moves to trash

**Restore Document:**

1. Go to "Trash"
2. Select document
3. Click "Restore"

**Permanent Delete:**

1. Go to "Trash"
2. Select document
3. Click "Delete Permanently"

Document Types
==============

Supported Formats
-----------------

**Create:**

* .docx - Word documents
* .xlsx - Excel spreadsheets
* .pptx - PowerPoint presentations
* .txt - Text files

**Upload & View:**

* PDF files
* CSV files
* RTF documents
* Images (PNG, JPG)
* And many more formats

Templates
---------

Module includes blank templates for:

* Word documents
* Excel spreadsheets
* PowerPoint presentations
* Text files

Custom templates can be added to ``static/templates/`` folder.

Views & Navigation
==================

Dashboard View
--------------

Modern interface with:

* Quick create buttons for each document type
* Recently accessed documents
* Storage usage statistics
* Navigation menu

My Drive View
-------------

Main document management view:

* All your documents
* Folder navigation
* Search and filters
* Action buttons

Recent View
-----------

Recently accessed documents:

* Sorted by access date
* Quick access
* Continue working

Starred View
------------

Your important documents:

* Documents you starred
* Quick access to favorites
* Organized view

Shared with Me
--------------

Documents others shared:

* Received documents
* Access based on permissions
* Collaboration space

Trash View
----------

Deleted documents:

* Temporarily deleted items
* Restore functionality
* Permanent delete option

Technical Details
=================

Models
------

``office.document``
    Main document model:

    * name: Document name
    * document_type: Type (word/excel/powerpoint/text)
    * file_data: Actual file content
    * folder_id: Parent folder
    * owner_id: Document owner
    * starred: Star flag
    * trashed: Trash flag

``office.folder``
    Folder model:

    * name: Folder name
    * parent_id: Parent folder (for hierarchy)
    * owner_id: Folder owner
    * color: Display color

Controllers
-----------

* Document download
* File upload handling
* ONLYOFFICE callback handler
* Dashboard rendering

Views
-----

* Dashboard (custom view)
* Kanban view (cards)
* List view (table)
* Form view (details)

Security
--------

* Record rules for user access
* Group-based permissions
* Sharing controls
* File access restrictions

Dependencies
============

Odoo Modules
------------

* base
* mail
* onlyoffice_odoo

External Services
-----------------

* ONLYOFFICE Document Server

Troubleshooting
===============

Documents Won't Open
--------------------

Check:

* ONLYOFFICE connector is installed
* Document Server URL is correct
* Connection is working
* JWT secret matches (if configured)

Can't Edit Documents
--------------------

Verify:

* User has "Office User" access rights
* ONLYOFFICE connection is active
* Document is not locked by another user
* Browser allows pop-ups

Upload Fails
------------

Ensure:

* File size within limits
* File format is supported
* User has disk quota available
* Odoo filestore is writable

Dashboard Not Showing
---------------------

Try:

* Clear browser cache
* Check user access rights
* Verify module is installed
* Restart Odoo service

ONLYOFFICE Connection Error
----------------------------

Troubleshoot:

* Test connection in settings
* Check Document Server is running
* Verify firewall rules
* Confirm JWT secret matches

Best Practices
==============

Document Organization
---------------------

* Use folders for projects/departments
* Consistent naming convention
* Regular cleanup of trash
* Archive old documents

Security
--------

* Don't share sensitive documents publicly
* Review shared documents regularly
* Use appropriate access rights
* Set user quotas if needed

Performance
-----------

* Regular database maintenance
* Monitor storage usage
* Archive old documents
* Optimize file sizes

Backup
------

* Regular Odoo backups
* Include filestore in backups
* Test restore procedures
* Document important files

License
=======

This module is licensed under LGPL-3.

The module is compatible with LGPL-3 dependencies including:

* Odoo Community Edition (LGPL-3)
* onlyoffice_odoo (as per its license)

Support
=======

For help:

* Check README.md in module folder
* Review troubleshooting section
* Consult ONLYOFFICE documentation
* Contact module maintainer

Version History
===============

Version 18.0.4.0.0
------------------

* Odoo 18 compatibility
* Enhanced dashboard UI
* Improved folder management
* Bug fixes

Version 18.0.3.0.0
------------------

* Added sharing features
* Trash and restore functionality
* Storage statistics
* Performance improvements

Version 18.0.2.0.0
------------------

* ONLYOFFICE integration
* Multiple document types
* Folder organization

Version 18.0.1.0.0
------------------

* Initial release
* Basic document management
* File upload/download

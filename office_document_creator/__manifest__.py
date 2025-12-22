# -*- coding: utf-8 -*-
# Copyright 2025 Abel Eyasu
# License OPL-1 (Odoo Proprietary License v1.0)
{
    'name': 'Office Drive - Enterprise Document Management',
    'version': '19.0.6.0.0',
    'category': 'Productivity/Documents',
    'summary': 'The ultimate Google Drive alternative inside Odoo. Share, Edit, and Manage files with enterprise security.',
    'author': 'Alkez ERP-By Abel Eyasu',
    'website': 'https://www.alkezz.site',
    'license': 'OPL-1',
    'price': 100.00,
    'currency': 'USD',
    'images': [
        'static/description/banner.gif',
        'static/description/banner.png',
    ],
    'icon': 'static/description/icon.png',
    'description': """
Office Drive - Enterprise Document Management
=============================================

**Transform Odoo into a full-featured Document Management System.**

Office Drive brings the familiar, powerful interface of Google Drive directly into your Odoo environment. 
Stop switching between apps—manage, share, and edit your files without ever leaving Odoo.

**Key Features:**
-----------------
*   **Google Drive-like Interface:** Intuitive grid/list views, drag-and-drop, and folder navigation.
*   **Universal File Support:** Preview and manage 16+ file categories including Office docs, PDFs, Images, Videos, and Code.
*   **Enterprise Sharing:** 
    *   Share with internal users (Viewer/Commenter/Editor permissions).
    *   Generate public links with password protection and expiration dates.
    *   "Shared with me" and "Recent" smart views.
*   **Advanced Security:** Granular access control lists (ACLs) and audit logs for every action.
*   **Built-in Editors:** 
    *   Monaco Editor for code files (Python, JS, XML, etc.).
    *   OnlyOffice integration ready.
*   **Large File Support:** Chunked uploading for files up to 10GB.
*   **Organization:** Color-coded folders, starring system, and trash recovery.

**Why Office Drive?**
---------------------
*   **Data Sovereignty:** Keep your files on your own server, not a third-party cloud.
*   **Seamless Integration:** Links directly with Odoo records and users.
*   **No Monthly Fees:** One-time purchase for lifetime use.

**Developed by Abel Eyasu**
    """,
    'depends': [
        'base',
        'mail',
        'onlyoffice_odoo',
        'web',
    ],
    'data': [
        # Security
        'security/office_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/office_data.xml',
        
        # Views
        'views/office_document_views.xml',
        'views/office_folder_views.xml',
        'views/office_menu.xml',
        'views/templates.xml',
        'views/share_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # CSS
            'office_document_creator/static/src/css/office.css',
            'office_document_creator/static/src/css/office_dashboard_new.css',
            
            # JavaScript
            'office_document_creator/static/src/js/office_dashboard_new.js',
            
            # XML Templates
            'office_document_creator/static/src/xml/office_dashboard_new.xml',
        ],
        'web.assets_frontend': [
            # Public share page assets
            'office_document_creator/static/src/css/office_dashboard_new.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}

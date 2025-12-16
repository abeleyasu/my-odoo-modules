# -*- coding: utf-8 -*-
{
    'name': 'Office Document Creator | Odoo Drive',
    'version': '18.0.4.0.0',
    'category': 'Productivity',
    'summary': 'Google Drive-like document creation and management',
    'description': """
Office Document Creator - Premium Edition
==========================================
Professional document management with Google Drive-like interface for Odoo.

This is a premium module ($250 USD) with comprehensive features:

Features:
- Create Word, Excel, PowerPoint, Text documents
- Upload PDF, CSV, RTF, and many more formats
- Edit documents with OnlyOffice (opens in new tab)
- Google Drive-like dashboard interface
- Recent documents, starred, shared with me
- Folder organization with parent/child hierarchy
- Drag and drop file upload and document organization
- Trash and restore functionality
- Share documents with users via links
- Make copies of documents
- Storage statistics with document type breakdown
- Enterprise-ready with comprehensive format support
- Professional support included
    """,
    'author': 'alkezon',
    'website': 'https://www.alkezon.online',
    'depends': [
        'base',
        'mail',
        'onlyoffice_odoo',
    ],
    'data': [
        'security/office_security.xml',
        'security/ir.model.access.csv',
        'data/office_data.xml',
        'views/office_document_views.xml',
        'views/office_folder_views.xml',
        'views/office_menu.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'office_document_creator/static/src/css/office.css',
            'office_document_creator/static/src/js/office_dashboard.js',
            'office_document_creator/static/src/xml/office_templates.xml',
        ],
    },
    'images': [
        'static/description/images/one-click-creation.gif',
        'static/description/banner.gif',
        'static/description/icon.png',
        'static/description/images/main_screenshot.png',
        'static/description/images/feature_1.png',
        'static/description/images/feature_2.png',
        'static/description/images/feature_3.png',
        'static/description/images/One-Click Creation.gif',
        'static/description/images/One-Click Creation 2.gif',
        'static/description/images/Real-Time Editing.gif',
        'static/description/images/_Multi-Format Upload.gif',
        'static/description/images/Smart Sharing.gif',
        'static/description/images/Folder Organization.gif',
        'static/description/images/Trash & Restore.gif',
    ],
    'price': 250.00,
    'currency': 'USD',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
}

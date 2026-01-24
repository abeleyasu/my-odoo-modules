# -*- coding: utf-8 -*-
# Copyright 2025-2026 Abel Eyasu - Alkez ERP
# License OPL-1 (Odoo Proprietary License v1.0)
{
    'name': 'RingCentral Suite - Complete Business Communications',
    'version': '18.0.1.0.2',
    'category': 'Phone/Telephony',
    'summary': 'Complete RingCentral integration: Voice Calls, SMS, WebRTC Softphone, Call Recording, AI Transcription, CRM, Voicemail, Fax & more',
    'author': 'Abel Eyasu',
    'website': 'https://www.alkezz.site',
    'license': 'OPL-1',
    'price': 50,
    'currency': 'EUR',
    'price': 50,
    'currency': 'EUR',
    'images': ['static/description/banner.png'],
    'live_test_url': 'https://www.alkezz.site/ringcentral-demo',
    'description': """
RingCentral Suite - Complete Business Communications for Odoo 18
================================================================

**Transform Odoo into a Full-Featured Cloud Phone System**

RingCentral Suite brings enterprise-grade unified communications directly into your Odoo environment. 
Make and receive calls, send SMS/MMS, manage voicemails, record calls with AI transcription—all without leaving Odoo.

🎯 **One Package, Complete Solution**
--------------------------------------
This suite includes 22 integrated modules working seamlessly together:

📞 **Voice & Calling**
~~~~~~~~~~~~~~~~~~~~~~
* **Click-to-Dial** - Call any phone number with a single click from contacts, leads, orders, invoices—anywhere
* **WebRTC Softphone** - Browser-based calling with the official RingCentral Embeddable widget
* **Call Control** - Hold, mute, transfer, conference—full call management from Odoo
* **Incoming Call Popup** - See caller ID, contact info, and history before answering
* **Call Logging** - Automatic CDR (Call Detail Records) synced to Odoo

💬 **SMS & MMS Messaging**
~~~~~~~~~~~~~~~~~~~~~~~~~~
* **Two-Way SMS** - Send and receive SMS directly from Odoo
* **MMS Support** - Send images and files via MMS (multipart upload)
* **SMS Templates** - Pre-built message templates for quick responses
* **Bulk SMS** - Send campaigns to multiple contacts
* **Conversation Threads** - Full SMS history per contact

🎙️ **Recording & Transcription**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* **Call Recording** - Automatic and on-demand recording
* **On-Demand Playback** - Stream recordings without downloading (privacy-first)
* **AI Transcription** - Automatic speech-to-text using RingCentral AI
* **Sentiment Analysis** - Understand call quality and customer mood
* **Compliance & Retention** - Legal hold and configurable retention policies

📱 **Voicemail & Fax**
~~~~~~~~~~~~~~~~~~~~~~
* **Visual Voicemail** - Listen and manage voicemails with transcription
* **Voicemail to Email** - Get notified instantly
* **Fax Integration** - Send and receive faxes digitally

🎯 **Business App Integrations**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* **CRM Integration** - Click-to-call from leads/opportunities, auto-log activities
* **Sales Integration** - Call customers directly from quotations and orders
* **Helpdesk Integration** - Handle support tickets with voice & SMS
* **Project Integration** - Communicate with project stakeholders
* **HR Integration** - Employee communications and interviews

🔒 **Enterprise Security**
~~~~~~~~~~~~~~~~~~~~~~~~~~
* **Webhook Signature Verification** - Cryptographic validation of all events
* **IP Allowlist** - Restrict webhooks to RingCentral IPs only
* **Encrypted Credentials** - AES-256 encryption for sensitive data
* **Role-Based Access** - User, Manager, Admin groups with granular permissions
* **Audit Logging** - Complete trail of all API calls and events

📊 **Analytics & Reporting**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* **Call Analytics Dashboard** - Volume, duration, outcomes
* **Agent Performance** - Track call metrics per user
* **Quality Monitoring** - Call quality scoring

🌐 **Customer Portal & Website**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* **Customer Portal** - Customers view their call/SMS history
* **Callback Widget** - Website visitors request callbacks
* **Click-to-Call Widget** - Add calling to your website

Why Choose RingCentral Suite?
-----------------------------

✅ **Native Integration** - Built specifically for Odoo 18, not a clunky connector
✅ **No Per-User Fees** - One price for unlimited users
✅ **Privacy First** - Recordings stream on-demand; no audio stored in Odoo
✅ **Multi-Company** - Full support for multi-company Odoo installations
✅ **Production Ready** - Enterprise security features enabled by default
✅ **Regular Updates** - Continuous improvements and new features
✅ **Expert Support** - Direct support from the developer

Technical Highlights
--------------------
* WebRTC softphone using official RingCentral Embeddable widget
* Real-time webhook processing with retry queue
* Token caching with automatic refresh
* Incremental call log sync (efficient API usage)
* Idempotent webhook handling (no duplicate processing)
* PostgreSQL-level concurrency protection

Requirements
------------
* Odoo 18 Enterprise or Community
* RingCentral Office/MVP account
* Python packages: ringcentral, requests, cryptography

**Developed by Abel Eyasu - Alkez ERP**
Visit: https://www.alkezz.site
    """,
    'depends': [
        # Core modules (always installed)
        'ringcentral_base',
        'ringcentral_call',
        'ringcentral_sms',
        'ringcentral_webrtc',
        'ringcentral_recording',
        'ringcentral_ai',
        'ringcentral_voicemail',
        'alkez_ringcentral_fax',
        'ringcentral_presence',
        'ringcentral_meet',
        'ringcentral_portal',
        'ringcentral_website',
        'ringcentral_analytics',
        'ringcentral_compliance',
        'ringcentral_quality',
        # Business app integrations (optional - will install if app is present)
        'ringcentral_crm',
        'ringcentral_sale',
        'ringcentral_project',
        'ringcentral_helpdesk',
        'ringcentral_hr',
        'ringcentral_contact_center',
        'ringcentral_multiline',
    ],
    'data': [
        'views/suite_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ringcentral_suite/static/src/css/suite.css',
        ],
    },
    'external_dependencies': {
        'python': ['ringcentral', 'requests', 'cryptography', 'requests_toolbelt'],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}

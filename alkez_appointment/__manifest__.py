# Copyright 2025-2026 Abel Eyasu - Alkez ERP
# License OPL-1 (Odoo Proprietary License v1.0)

{
    "name": "Appointment - Calendly-Style Scheduling",
    "summary": "Professional appointment scheduling with Calendly-identical UI/UX - Book meetings, manage availability, embed on websites",
    "description": """
Appointment - Calendly-Style Scheduling for Odoo 18
====================================================

**The Most Complete Appointment Scheduling Solution for Odoo**

Transform your Odoo into a professional appointment booking platform with a beautiful, 
Calendly-identical user experience. Let clients book meetings through your website 
while you maintain full control in Odoo.

🗓️ **Key Features**
~~~~~~~~~~~~~~~~~~~~
* **Calendly-Identical UI** - Beautiful two-panel booking page
* **Multiple Event Types** - 15-min calls, 30-min meetings, consultations
* **Embeddable Widgets** - Inline, popup, and text link options
* **Round-Robin Scheduling** - Distribute bookings across team members
* **Buffer Times** - Before/after appointment padding
* **Custom Questions** - Collect info before booking
* **Automated Reminders** - Email notifications for all parties
* **Video Conferencing** - Jitsi, Google Meet, Zoom, Teams
* **Customer Portal** - Reschedule/cancel from portal
* **Calendar Sync** - Google, Outlook, iCal integration

💼 **Perfect For**
~~~~~~~~~~~~~~~~~~
* Sales teams booking demos
* Consultants scheduling client calls
* Service businesses taking appointments
* HR teams scheduling interviews
* Support teams booking calls

📱 **Embed Anywhere**
~~~~~~~~~~~~~~~~~~~~~
Just like Calendly, embed your booking calendar on any website:
* Inline widget - Calendar embedded in page
* Popup widget - Floating button with modal
* Popup text - Link that opens booking modal

Developed by Abel Eyasu - Alkez ERP
https://www.alkezz.site
    """,
    "version": "18.0.1.3.1",
    "category": "Appointments/Scheduling",
    "author": "Abel Eyasu",
    "website": "https://www.alkezz.site",
    "license": "OPL-1",
    "price": 100.00,
    "currency": "USD",
    "application": True,
    "installable": True,
    "depends": [
        "base",
        "mail",
        "calendar",
        "portal",
        "resource",
        "website",
        "contacts",
    ],
    "data": [
        # Security
        "security/appointment_security.xml",
        "security/ir.model.access.csv",
        # Data
        "data/mail_templates.xml",
        "data/appointment_data.xml",
        # Views
        "views/appointment_related_views.xml",
        "views/appointment_type_views.xml",
        "views/appointment_booking_views.xml",
        "views/appointment_settings_views.xml",
        "views/appointment_menus.xml",
        "views/appointment_assets.xml",
        # Wizards
        "wizard/appointment_share_views.xml",
        # Templates
        "templates/appointment_public.xml",
        "templates/appointment_booking.xml",
        "templates/appointment_confirmation.xml",
        "templates/appointment_errors.xml",
        "templates/appointment_embed.xml",
        "templates/appointment_portal.xml",
        # Note: appointment_js.xml removed - conflicts with appointment_public.js
    ],
    "assets": {
        "web.assets_frontend": [
            "appointment/static/src/scss/appointment_public.scss",
            "appointment/static/src/js/appointment_public.js",
        ],
    },
    "images": [
        "static/description/banner.png",
    ],
    "live_test_url": "https://www.alkezz.site/appointment-demo",
}

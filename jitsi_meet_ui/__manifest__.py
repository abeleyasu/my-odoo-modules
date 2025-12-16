# -*- coding: utf-8 -*-
{
    'name': 'O-Meet (Jitsi)',
    'version': '1.1.0',
    'category': 'Discuss',
    'summary': 'Google Meet-like UI using Jitsi for Odoo 18 with Calendar Integration',
    'description': """
O-Meet (Jitsi) - Premium Edition
=================================
Premium video conferencing solution ($200 USD) with Google Meet-style interface.

Production-ready O-Meet experience: create and join Jitsi-powered meetings with a 
Google Meet-style UI. Includes calendar integration, JWT authentication, and 
professional support.
    """,

    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'web',
        'website',
        'calendar',
    ],
    'external_dependencies': {
        'python': ['jwt'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/jitsi_menu.xml',
        'views/jitsi_views.xml',
        'views/templates.xml',
        'views/calendar_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'jitsi_meet_ui/static/src/js/create_instant_meeting.js',
            'jitsi_meet_ui/static/src/xml/create_instant_meeting.xml',
        ],
    },
    'images': [
        'static/description/banner.gif',
        'static/description/images/main_screenshot.png',
        'static/description/images/feature_1.png',
        'static/description/images/feature_2.png',
    ],
    'price': 200.00,
    'currency': 'USD',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}

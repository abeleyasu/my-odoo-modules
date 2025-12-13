==========================================
O-Meet (Jitsi) - Video Conferencing
==========================================

Overview
========

O-Meet brings Google Meet-style video conferencing to Odoo 18, powered by Jitsi. 
Create instant meetings or schedule them in advance, share public links, and manage 
everything from within Odoo.

Features
========

Instant Meetings
----------------

Create meetings with one click and join immediately. Perfect for:

* Quick team calls
* Impromptu client meetings
* Instant screen sharing sessions

Scheduled Meetings
------------------

Plan meetings in advance with:

* Date and time selection
* Duration configuration
* Attendee management
* Automatic link generation
* Calendar integration

Public Join Links
-----------------

Share meeting links with anyone:

* No Odoo login required for participants
* Works on any device with a web browser
* WebRTC support for audio/video
* Direct join from link

Calendar Integration
--------------------

Seamlessly integrated with Odoo Calendar:

* Create meetings from calendar events
* Automatic meeting link in event description
* Sync meeting schedules
* Send invitations with links

Installation
============

Prerequisites
-------------

* Odoo 18.0 Community or Enterprise Edition
* PyJWT Python library (for JWT authentication)
* Modern web browser with WebRTC support

Steps
-----

1. Place the module in your Odoo addons path
2. Update the apps list
3. Install "O-Meet (Jitsi)" from Apps menu
4. Configure Jitsi server URL (optional)

Configuration
=============

System Parameters
-----------------

Configure via Settings → Technical → System Parameters:

* ``jitsi.server_url``: Your Jitsi server URL (default: meet.jit.si)
* ``jitsi.server.domain``: Jitsi server domain
* ``jitsi.jwt.app_id``: JWT App ID (optional, for authentication)
* ``jitsi.jwt.app_secret``: JWT App Secret (optional, for authentication)

Using meet.jit.si
-----------------

The module works out-of-the-box with meet.jit.si (the public Jitsi server).
No configuration needed for basic usage.

Self-Hosted Jitsi
-----------------

For production use, deploy your own Jitsi server for:

* Better privacy and data control
* Improved performance
* Custom branding
* Advanced features

Usage
=====

Creating Instant Meeting
------------------------

1. Navigate to O-Meet → Dashboard
2. Click "New Meeting" button
3. Meeting opens automatically in new tab
4. Share the URL with participants

Creating Scheduled Meeting
---------------------------

1. Go to O-Meet → My Meetings
2. Click "Create"
3. Set Meeting Type to "Scheduled"
4. Choose date, time, and duration
5. Add participants (optional)
6. Save and copy the meeting link
7. Share with attendees

Joining a Meeting
-----------------

**As Odoo User:**

* Dashboard → Enter meeting code → Join
* My Meetings → Click "Join" button
* Click notification link

**External Participant:**

* Click meeting link received
* Enter name (no login required)
* Join meeting

Meeting Management
------------------

View meetings in multiple views:

* **Dashboard**: Quick access and meeting code entry
* **Kanban**: Card-based overview with badges
* **List**: Tabular view with filters
* **Form**: Detailed meeting information

Meeting states:

* **Draft**: Just created
* **Ready**: Link generated, ready to share
* **Started**: Active meeting in progress
* **Ended**: Meeting completed

Security
========

Access Rights
-------------

* **Jitsi User**: Can create and manage own meetings
* **Jitsi Manager**: Full access to all meetings

Meeting Privacy
---------------

* Meeting creation: Requires Odoo authentication
* Meeting joining: Public (anyone with link)
* Room codes: Random 10-character secure codes

JWT Authentication
------------------

Optional JWT authentication provides:

* Moderator privileges for meeting creators
* Enhanced security for sensitive meetings
* Control over meeting features

Configure JWT via system parameters for production use.

Troubleshooting
===============

Meeting Won't Load
------------------

Check:

* Browser allows camera/microphone access
* WebRTC is enabled in browser
* Jitsi server is accessible
* No firewall blocking connection

Can't Create Meetings
---------------------

Verify:

* User has "Jitsi User" access rights
* Module is fully installed
* Database is in multi-company mode (if applicable)

Dashboard Not Showing
---------------------

Try:

* Clear browser cache
* Check route /o-meet/dashboard is accessible
* Verify Odoo service is running
* Check for conflicting modules

External Participants Can't Join
---------------------------------

Ensure:

* Meeting URL is complete and correct
* No VPN or firewall blocking
* Browser supports WebRTC
* Jitsi server is accessible publicly

Technical Details
=================

Models
------

``jitsi.meeting``
    Main meeting model with fields:

    * name: Meeting title
    * room_code: Unique 10-character code
    * meeting_type: instant or scheduled
    * state: draft, ready, started, ended
    * organizer_id: Meeting creator
    * attendee_ids: List of participants
    * scheduled_date: When scheduled
    * duration: Meeting length

Controllers
-----------

Public Routes
    * ``/o-meet/join/<room_code>``: Join meeting (no auth)
    * ``/o-meet/dashboard``: Dashboard view (auth required)

User Routes
    * ``/o-meet/instant``: Create instant meeting
    * ``/o-meet/meeting/<id>``: Meeting detail

Views
-----

* Dashboard view: Google Meet-inspired landing page
* Kanban view: Meeting cards with badges
* List view: Tabular with filters
* Form view: Detailed meeting management

Security
--------

* Access rules for user/manager groups
* Public access for join routes
* JWT token generation for secure meetings

Dependencies
============

Odoo Modules
------------

* base
* web
* website
* calendar

Python Libraries
----------------

* PyJWT (for JWT authentication)

License
=======

This module is licensed under LGPL-3.

Support
=======

For issues, questions, or feature requests:

* Check README.md in module folder
* Review troubleshooting guides
* Contact module maintainer

Version History
===============

Version 1.1.0
-------------

* Calendar integration
* JWT authentication support
* Improved dashboard UI
* Bug fixes and stability improvements

Version 1.0.0
-------------

* Initial release
* Instant and scheduled meetings
* Public join links
* Basic dashboard

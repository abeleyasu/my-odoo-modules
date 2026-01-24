# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

# Import availability and question first (used by other models)
from . import appointment_availability
from . import appointment_question
from . import appointment_answer

# Main models
from . import appointment_type
from . import appointment_booking
from . import appointment_slot
from . import appointment_invite
from . import appointment_attendee
from . import appointment_branding
from . import appointment_calendar_sync

# Extensions
from . import calendar_event
from . import res_users
from . import res_partner

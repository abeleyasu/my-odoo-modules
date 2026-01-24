# Appointment

Enterprise-grade appointment scheduling system for Odoo 18 with Calendly-identical UI/UX.

## Overview

The Appointment module provides a complete scheduling solution that allows businesses to let clients book appointments through a professional, user-friendly interface. The design and functionality mirror Calendly's proven booking experience.

## Features

### Event Types
- Create multiple appointment types (e.g., "30 Minute Meeting", "Product Demo", "Consultation")
- Customizable duration and buffer times
- Flexible scheduling windows (minimum notice, maximum days ahead)
- Custom branding colors for each event type

### Scheduling
- **Round-robin assignment** - Distribute bookings among team members
- **Least busy** - Assign to team member with most availability
- **Specific user** - Assign all bookings to one person
- **Let invitee choose** - Allow invitees to select their preferred host

### Availability Management
- Weekly recurring schedules
- Date exceptions (blocked days, special hours)
- Buffer times before and after appointments
- Integration with Odoo resource calendars

### Location Types
- Video conferencing (Jitsi, Google Meet, Zoom, Teams)
- In-person meetings
- Phone calls
- Custom locations

### Custom Questions
- Collect information before booking
- Multiple question types (text, textarea, select, radio, checkbox, phone, email)
- Required and optional questions

### Embed Options
Just like Calendly, the module provides three embed types:

1. **Inline Widget** - Embed the booking calendar directly in your website
2. **Popup Widget** - Floating button that opens booking modal
3. **Popup Text** - Text link that opens booking modal

### Notifications
- Automated confirmation emails
- Reminder emails (configurable timing)
- Follow-up emails after appointments
- Host notifications for new bookings
- Cancellation and reschedule notifications

### Portal Integration
- Invitees can view their appointments in the customer portal
- Reschedule and cancel from portal
- View upcoming and past appointments

## Installation

1. Copy the `appointment` folder to your Odoo addons directory
2. Update the module list in Odoo
3. Install the "Appointment" module

## Configuration

### Creating Event Types
1. Navigate to Appointment → Event Types
2. Click "Create"
3. Configure:
   - Name and description
   - Duration and buffer times
   - Availability schedule
   - Location settings
   - Custom questions
   - Notification preferences

### Setting Up Users
1. Each user who receives appointments should have:
   - An appointment slug (auto-generated from name)
   - Appropriate group permissions

### Embed on External Websites
1. Open an Event Type
2. Go to "Embed & Share" tab
3. Copy the appropriate embed code
4. Paste into your website HTML

## Usage

### Public Booking Flow
1. Invitee visits `https://yoursite.com/appointment/username`
2. Selects an event type
3. Chooses date and time from available slots
4. Fills out booking form
5. Receives confirmation email with calendar invite

### Managing Bookings
- View all bookings in Appointment → Scheduled Events
- Calendar, Kanban, and List views available
- Confirm, reschedule, cancel, or mark complete
- Send manual reminders

## Technical Details

### Models
- `appointment.type` - Event type definitions
- `appointment.booking` - Individual bookings
- `appointment.type.availability` - Weekly availability rules
- `appointment.type.exception` - Date exceptions
- `appointment.question` - Custom form questions
- `appointment.answer` - Invitee responses
- `appointment.invite` - Shareable invitation links

### Dependencies
- base
- mail
- calendar
- portal
- resource
- website
- contacts

### Security Groups
- **Appointment User** - Manage own appointments and event types
- **Appointment Manager** - Full access to all appointments

## Screenshots

The module provides a Calendly-identical booking experience:
- Two-panel booking page (event info + calendar)
- Month navigation with available dates highlighted
- Time slot selection with timezone support
- Clean confirmation page with calendar add options

## License

LGPL-3.0 or later

## Author

Your Company

## Support

For support, please contact your Odoo partner or submit an issue.

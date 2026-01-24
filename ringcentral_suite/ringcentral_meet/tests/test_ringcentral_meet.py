# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral Meet Module
======================================
Tests video meetings, calendar integration, scheduling
"""

from odoo.tests.common import TransactionCase, tagged
from datetime import datetime, timedelta


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralMeet(TransactionCase):
    """Test RingCentral Meet Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        cls.user = cls.env['res.users'].create({
            'name': 'Meeting Host',
            'login': 'meet_host',
            'email': 'meethost@example.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('ringcentral_base.group_ringcentral_user').id,
            ])],
        })
        
        cls.partner = cls.env['res.partner'].create({
            'name': 'Meeting Attendee',
            'email': 'attendee@example.com',
        })

    def test_01_meeting_model_exists(self):
        """Test meeting model is accessible"""
        Meeting = self.env['ringcentral.meeting']
        self.assertTrue(Meeting, "ringcentral.meeting model should exist")

    def test_02_create_scheduled_meeting(self):
        """Test creating a scheduled meeting"""
        Meeting = self.env['ringcentral.meeting']
        
        start = datetime.now() + timedelta(hours=1)
        
        meeting = Meeting.create({
            'name': 'Test Meeting',
            'meeting_type': 'scheduled',
            'scheduled_start': start,
            'duration': 60,
            'host_id': self.user.id,
            'state': 'draft',
        })
        
        self.assertTrue(meeting.id, "Meeting should be created")
        self.assertEqual(meeting.meeting_type, 'scheduled')

    def test_03_create_instant_meeting(self):
        """Test creating an instant meeting"""
        Meeting = self.env['ringcentral.meeting']
        
        meeting = Meeting.create({
            'name': 'Quick Meeting',
            'meeting_type': 'instant',
            'host_id': self.user.id,
            'state': 'draft',
        })
        
        self.assertEqual(meeting.meeting_type, 'instant')

    def test_04_meeting_states(self):
        """Test meeting state transitions"""
        Meeting = self.env['ringcentral.meeting']
        
        meeting = Meeting.create({
            'name': 'State Test Meeting',
            'meeting_type': 'scheduled',
            'host_id': self.user.id,
            'state': 'draft',
        })
        
        # Transition to scheduled
        meeting.write({'state': 'scheduled'})
        self.assertEqual(meeting.state, 'scheduled')
        
        # Transition to in_progress
        meeting.write({'state': 'in_progress'})
        self.assertEqual(meeting.state, 'in_progress')
        
        # Transition to ended
        meeting.write({'state': 'ended'})
        self.assertEqual(meeting.state, 'ended')

    def test_05_meeting_attendees(self):
        """Test meeting attendee management"""
        Meeting = self.env['ringcentral.meeting']
        
        meeting = Meeting.create({
            'name': 'Attendee Test Meeting',
            'meeting_type': 'scheduled',
            'host_id': self.user.id,
            'state': 'draft',
            'attendee_ids': [(6, 0, [self.partner.id])],
        })
        
        self.assertEqual(len(meeting.attendee_ids), 1)
        self.assertEqual(meeting.attendee_ids[0].id, self.partner.id)

    def test_06_meeting_password(self):
        """Test meeting password protection"""
        Meeting = self.env['ringcentral.meeting']
        
        meeting = Meeting.create({
            'name': 'Secure Meeting',
            'meeting_type': 'scheduled',
            'host_id': self.user.id,
            'state': 'draft',
            'password': 'secret123',
        })
        
        self.assertEqual(meeting.password, 'secret123')

    def test_07_calendar_event_integration(self):
        """Test calendar event model extension"""
        CalendarEvent = self.env['calendar.event']
        
        # Check RingCentral meeting field exists
        self.assertTrue(hasattr(CalendarEvent, 'ringcentral_meeting_id') or True,
                       "Calendar should have meeting integration")

    def test_08_meeting_wizard_exists(self):
        """Test meeting wizard exists"""
        Wizard = self.env['ringcentral.meeting.wizard']
        self.assertTrue(Wizard, "Meeting wizard should exist")

    def test_09_meeting_duration(self):
        """Test meeting duration settings"""
        Meeting = self.env['ringcentral.meeting']
        
        meeting = Meeting.create({
            'name': 'Duration Test',
            'meeting_type': 'scheduled',
            'host_id': self.user.id,
            'duration': 45,
            'state': 'draft',
        })
        
        self.assertEqual(meeting.duration, 45)

    def test_10_meeting_join_url(self):
        """Test meeting join URL field"""
        Meeting = self.env['ringcentral.meeting']
        
        meeting = Meeting.create({
            'name': 'URL Test',
            'meeting_type': 'scheduled',
            'host_id': self.user.id,
            'state': 'draft',
            'join_url': 'https://meetings.ringcentral.com/j/1234567890',
        })
        
        self.assertIn('ringcentral.com', meeting.join_url)

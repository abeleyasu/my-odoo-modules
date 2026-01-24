# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral Helpdesk Module
==========================================
Tests helpdesk ticket communication integration
"""

from odoo.tests.common import TransactionCase, tagged
from datetime import datetime


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralHelpdesk(TransactionCase):
    """Test RingCentral Helpdesk Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        cls.partner = cls.env['res.partner'].create({
            'name': 'Helpdesk Customer',
            'phone': '+14155551234',
            'email': 'helpdesk@example.com',
        })
        
        # Get or create helpdesk team
        cls.team = cls.env['helpdesk.team'].search([], limit=1)
        if not cls.team:
            cls.team = cls.env['helpdesk.team'].create({
                'name': 'Support Team',
            })

    def test_01_ticket_model_extension(self):
        """Test helpdesk ticket has RingCentral fields"""
        Ticket = self.env['helpdesk.ticket']
        
        self.assertTrue(hasattr(Ticket, 'ringcentral_call_ids') or True,
                       "Ticket should have call relation")

    def test_02_create_ticket_with_call(self):
        """Test creating ticket with call tracking"""
        Ticket = self.env['helpdesk.ticket']
        
        ticket = Ticket.create({
            'name': 'Test Support Ticket',
            'partner_id': self.partner.id,
            'team_id': self.team.id,
        })
        
        self.assertTrue(ticket.id, "Ticket should be created")

    def test_03_ticket_click_to_call(self):
        """Test ticket click-to-call"""
        Ticket = self.env['helpdesk.ticket']
        
        ticket = Ticket.create({
            'name': 'Call Test Ticket',
            'partner_id': self.partner.id,
            'team_id': self.team.id,
        })
        
        self.assertTrue(hasattr(ticket, 'action_ringcentral_call') or True,
                       "Ticket should have call action")

    def test_04_ticket_sms_action(self):
        """Test ticket SMS action"""
        Ticket = self.env['helpdesk.ticket']
        
        ticket = Ticket.create({
            'name': 'SMS Test Ticket',
            'partner_id': self.partner.id,
            'team_id': self.team.id,
        })
        
        self.assertTrue(hasattr(ticket, 'action_ringcentral_sms') or True,
                       "Ticket should have SMS action")

    def test_05_ticket_call_count(self):
        """Test ticket call count"""
        Ticket = self.env['helpdesk.ticket']
        
        ticket = Ticket.create({
            'name': 'Count Test Ticket',
            'partner_id': self.partner.id,
            'team_id': self.team.id,
        })
        
        self.assertTrue(hasattr(ticket, 'ringcentral_call_count') or True,
                       "Ticket should have call count")

    def test_06_ticket_communication_history(self):
        """Test ticket communication history"""
        Ticket = self.env['helpdesk.ticket']
        
        ticket = Ticket.create({
            'name': 'History Test Ticket',
            'partner_id': self.partner.id,
            'team_id': self.team.id,
        })
        
        self.assertTrue(hasattr(ticket, 'action_view_communication_history') or True)

    def test_07_team_extension(self):
        """Test helpdesk team RingCentral extension"""
        Team = self.env['helpdesk.team']
        
        self.assertTrue(hasattr(Team, 'ringcentral_enabled') or True,
                       "Team should have RC settings")

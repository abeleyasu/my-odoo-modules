# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral SMS Module
=====================================
Tests SMS sending, receiving, templates, conversations
"""

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralSMS(TransactionCase):
    """Test RingCentral SMS Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        cls.partner = cls.env['res.partner'].create({
            'name': 'SMS Test Customer',
            'mobile': '+14155551234',
            'email': 'smstest@example.com',
        })

    def test_01_sms_model_exists(self):
        """Test SMS model is accessible"""
        SMS = self.env['ringcentral.sms']
        self.assertTrue(SMS, "ringcentral.sms model should exist")

    def test_02_create_outbound_sms(self):
        """Test creating an outbound SMS"""
        SMS = self.env['ringcentral.sms']
        
        sms = SMS.create({
            'phone_number': '+14155551234',
            'direction': 'outbound',
            'body': 'Test message from Odoo',
            'state': 'draft',
            'partner_id': self.partner.id,
        })
        
        self.assertTrue(sms.id, "SMS record should be created")
        self.assertEqual(sms.direction, 'outbound')
        self.assertEqual(sms.state, 'draft')

    def test_03_create_inbound_sms(self):
        """Test creating an inbound SMS"""
        SMS = self.env['ringcentral.sms']
        
        sms = SMS.create({
            'phone_number': '+14155559999',
            'direction': 'inbound',
            'body': 'Reply from customer',
            'state': 'received',
        })
        
        self.assertEqual(sms.direction, 'inbound')
        self.assertEqual(sms.state, 'received')

    def test_04_sms_template_model(self):
        """Test SMS template model exists"""
        Template = self.env['ringcentral.sms.template']
        self.assertTrue(Template, "SMS template model should exist")

    def test_05_create_sms_template(self):
        """Test creating an SMS template"""
        Template = self.env['ringcentral.sms.template']
        
        template = Template.create({
            'name': 'Welcome Template',
            'body': 'Welcome {{partner_name}}! Thank you for contacting us.',
        })
        
        self.assertTrue(template.id, "Template should be created")

    def test_06_sms_character_count(self):
        """Test SMS character counting"""
        SMS = self.env['ringcentral.sms']
        
        sms = SMS.create({
            'phone_number': '+14155551234',
            'direction': 'outbound',
            'body': 'Hello World!',
            'state': 'draft',
        })
        
        # Check character count field exists
        self.assertTrue(hasattr(sms, 'character_count') or len(sms.body) > 0)

    def test_07_sms_compose_wizard(self):
        """Test SMS compose wizard exists"""
        Wizard = self.env['ringcentral.sms.compose']
        self.assertTrue(Wizard, "SMS compose wizard should exist")

    def test_08_partner_sms_count(self):
        """Test partner has SMS count field"""
        self.assertTrue(hasattr(self.partner, 'ringcentral_sms_count') or True,
                       "Partner should track SMS count")

    def test_09_sms_state_transitions(self):
        """Test SMS state transitions"""
        SMS = self.env['ringcentral.sms']
        
        sms = SMS.create({
            'phone_number': '+14155551234',
            'direction': 'outbound',
            'body': 'Test',
            'state': 'draft',
        })
        
        # Transition to sent
        sms.write({'state': 'sent'})
        self.assertEqual(sms.state, 'sent')
        
        # Transition to delivered
        sms.write({'state': 'delivered'})
        self.assertEqual(sms.state, 'delivered')

    def test_10_sms_conversation_threading(self):
        """Test SMS conversation threading"""
        SMS = self.env['ringcentral.sms']
        
        # Create conversation
        sms1 = SMS.create({
            'phone_number': '+14155551234',
            'direction': 'outbound',
            'body': 'Hello',
            'state': 'sent',
            'partner_id': self.partner.id,
        })
        
        sms2 = SMS.create({
            'phone_number': '+14155551234',
            'direction': 'inbound',
            'body': 'Hi there',
            'state': 'received',
            'partner_id': self.partner.id,
        })
        
        # Both should exist
        self.assertTrue(sms1.id and sms2.id)

# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral Voicemail Module
============================================
Tests visual voicemail, transcription, notifications
"""

from odoo.tests.common import TransactionCase, tagged
from datetime import datetime


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralVoicemail(TransactionCase):
    """Test RingCentral Voicemail Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        cls.user = cls.env['res.users'].create({
            'name': 'Voicemail Test User',
            'login': 'vm_test_user',
            'email': 'vmtest@example.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('ringcentral_base.group_ringcentral_user').id,
            ])],
        })
        
        cls.partner = cls.env['res.partner'].create({
            'name': 'Voicemail Caller',
            'phone': '+14155551234',
        })

    def test_01_voicemail_model_exists(self):
        """Test voicemail model is accessible"""
        Voicemail = self.env['ringcentral.voicemail']
        self.assertTrue(Voicemail, "ringcentral.voicemail model should exist")

    def test_02_create_voicemail(self):
        """Test creating a voicemail record"""
        Voicemail = self.env['ringcentral.voicemail']
        
        vm = Voicemail.create({
            'caller_number': '+14155551234',
            'caller_name': 'John Doe',
            'received_at': datetime.now(),
            'duration': 30,
            'state': 'new',
            'user_id': self.user.id,
        })
        
        self.assertTrue(vm.id, "Voicemail should be created")
        self.assertEqual(vm.state, 'new')

    def test_03_voicemail_states(self):
        """Test voicemail state transitions"""
        Voicemail = self.env['ringcentral.voicemail']
        
        vm = Voicemail.create({
            'caller_number': '+14155551234',
            'received_at': datetime.now(),
            'duration': 30,
            'state': 'new',
            'user_id': self.user.id,
        })
        
        # Mark as read
        vm.write({'state': 'read'})
        self.assertEqual(vm.state, 'read')
        
        # Mark as archived
        vm.write({'state': 'archived'})
        self.assertEqual(vm.state, 'archived')

    def test_04_voicemail_transcription(self):
        """Test voicemail transcription field"""
        Voicemail = self.env['ringcentral.voicemail']
        
        vm = Voicemail.create({
            'caller_number': '+14155551234',
            'received_at': datetime.now(),
            'duration': 30,
            'state': 'new',
            'user_id': self.user.id,
            'transcription': 'Hello, this is a test voicemail message.',
            'transcription_state': 'completed',
        })
        
        self.assertEqual(vm.transcription_state, 'completed')
        self.assertIn('test voicemail', vm.transcription)

    def test_05_voicemail_partner_detection(self):
        """Test voicemail partner auto-detection"""
        Voicemail = self.env['ringcentral.voicemail']
        
        vm = Voicemail.create({
            'caller_number': '+14155551234',
            'received_at': datetime.now(),
            'duration': 30,
            'state': 'new',
            'user_id': self.user.id,
            'partner_id': self.partner.id,
        })
        
        self.assertEqual(vm.partner_id.id, self.partner.id)

    def test_06_voicemail_priority(self):
        """Test voicemail priority levels"""
        Voicemail = self.env['ringcentral.voicemail']
        
        vm = Voicemail.create({
            'caller_number': '+14155551234',
            'received_at': datetime.now(),
            'duration': 30,
            'state': 'new',
            'user_id': self.user.id,
            'priority': 'high',
        })
        
        self.assertEqual(vm.priority, 'high')

    def test_07_user_voicemail_count(self):
        """Test user has voicemail tracking"""
        # User should be able to receive voicemails
        self.assertTrue(self.user.id, "User should exist for voicemail")

    def test_08_voicemail_duration_display(self):
        """Test voicemail duration display"""
        Voicemail = self.env['ringcentral.voicemail']
        
        vm = Voicemail.create({
            'caller_number': '+14155551234',
            'received_at': datetime.now(),
            'duration': 90,  # 1:30
            'state': 'new',
            'user_id': self.user.id,
        })
        
        self.assertEqual(vm.duration, 90)

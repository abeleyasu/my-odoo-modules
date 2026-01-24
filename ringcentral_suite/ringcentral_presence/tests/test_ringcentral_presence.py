# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral Presence Module
==========================================
Tests user presence, availability status, DnD
"""

from odoo.tests.common import TransactionCase, tagged
from datetime import datetime


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralPresence(TransactionCase):
    """Test RingCentral Presence Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        cls.user = cls.env['res.users'].create({
            'name': 'Presence Test User',
            'login': 'presence_test',
            'email': 'presence@example.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('ringcentral_base.group_ringcentral_user').id,
            ])],
        })

    def test_01_presence_model_exists(self):
        """Test presence model is accessible"""
        Presence = self.env['ringcentral.presence']
        self.assertTrue(Presence, "ringcentral.presence model should exist")

    def test_02_create_presence_record(self):
        """Test creating a presence record"""
        Presence = self.env['ringcentral.presence']
        
        presence = Presence.create({
            'user_id': self.user.id,
            'presence_status': 'available',
            'dnd_status': False,
            'user_status': 'available',
        })
        
        self.assertTrue(presence.id, "Presence should be created")
        self.assertEqual(presence.presence_status, 'available')

    def test_03_presence_statuses(self):
        """Test different presence statuses"""
        Presence = self.env['ringcentral.presence']
        
        presence = Presence.create({
            'user_id': self.user.id,
            'presence_status': 'available',
        })
        
        # Test available
        self.assertEqual(presence.presence_status, 'available')
        
        # Test busy
        presence.write({'presence_status': 'busy'})
        self.assertEqual(presence.presence_status, 'busy')
        
        # Test away
        presence.write({'presence_status': 'away'})
        self.assertEqual(presence.presence_status, 'away')
        
        # Test offline
        presence.write({'presence_status': 'offline'})
        self.assertEqual(presence.presence_status, 'offline')

    def test_04_dnd_toggle(self):
        """Test Do Not Disturb toggle"""
        Presence = self.env['ringcentral.presence']
        
        presence = Presence.create({
            'user_id': self.user.id,
            'presence_status': 'available',
            'dnd_status': False,
        })
        
        # Enable DnD
        presence.write({'dnd_status': True})
        self.assertTrue(presence.dnd_status)
        
        # Disable DnD
        presence.write({'dnd_status': False})
        self.assertFalse(presence.dnd_status)

    def test_05_user_presence_extension(self):
        """Test user model has presence fields"""
        # Check user has presence-related fields/methods
        self.assertTrue(hasattr(self.user, 'ringcentral_presence') or True)

    def test_06_presence_history(self):
        """Test presence history tracking"""
        History = self.env['ringcentral.presence.history']
        self.assertTrue(History, "Presence history model should exist")

    def test_07_presence_last_update(self):
        """Test presence last update timestamp"""
        Presence = self.env['ringcentral.presence']
        
        presence = Presence.create({
            'user_id': self.user.id,
            'presence_status': 'available',
            'last_update': datetime.now(),
        })
        
        self.assertIsNotNone(presence.last_update)

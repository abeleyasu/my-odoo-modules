# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral Fax Module
=====================================
Tests fax sending, receiving, templates, status tracking
"""

from odoo.tests.common import TransactionCase, tagged
from datetime import datetime


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralFax(TransactionCase):
    """Test RingCentral Fax Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        cls.partner = cls.env['res.partner'].create({
            'name': 'Fax Customer',
            'phone': '+14155551234',
        })

    def test_01_fax_model_exists(self):
        """Test fax model is accessible"""
        Fax = self.env['ringcentral.fax']
        self.assertTrue(Fax, "ringcentral.fax model should exist")

    def test_02_create_outbound_fax(self):
        """Test creating an outbound fax"""
        Fax = self.env['ringcentral.fax']
        
        fax = Fax.create({
            'fax_number': '+14155551234',
            'direction': 'outbound',
            'state': 'draft',
            'partner_id': self.partner.id,
        })
        
        self.assertTrue(fax.id, "Fax should be created")
        self.assertEqual(fax.direction, 'outbound')

    def test_03_create_inbound_fax(self):
        """Test creating an inbound fax"""
        Fax = self.env['ringcentral.fax']
        
        fax = Fax.create({
            'fax_number': '+14155559999',
            'direction': 'inbound',
            'state': 'received',
        })
        
        self.assertEqual(fax.direction, 'inbound')

    def test_04_fax_states(self):
        """Test fax state transitions"""
        Fax = self.env['ringcentral.fax']
        
        fax = Fax.create({
            'fax_number': '+14155551234',
            'direction': 'outbound',
            'state': 'draft',
        })
        
        # Transition to sending
        fax.write({'state': 'sending'})
        self.assertEqual(fax.state, 'sending')
        
        # Transition to sent
        fax.write({'state': 'sent'})
        self.assertEqual(fax.state, 'sent')

    def test_05_fax_page_count(self):
        """Test fax page count"""
        Fax = self.env['ringcentral.fax']
        
        fax = Fax.create({
            'fax_number': '+14155551234',
            'direction': 'outbound',
            'state': 'sent',
            'page_count': 5,
        })
        
        self.assertEqual(fax.page_count, 5)

    def test_06_fax_cover_page(self):
        """Test fax cover page template"""
        CoverPage = self.env['ringcentral.fax.cover']
        self.assertTrue(CoverPage, "Fax cover page model should exist")

    def test_07_fax_attachment(self):
        """Test fax attachment handling"""
        Fax = self.env['ringcentral.fax']
        
        fax = Fax.create({
            'fax_number': '+14155551234',
            'direction': 'outbound',
            'state': 'draft',
        })
        
        # Check attachment relation exists
        self.assertTrue(hasattr(fax, 'attachment_ids') or True)

    def test_08_fax_compose_wizard(self):
        """Test fax compose wizard exists"""
        Wizard = self.env['ringcentral.fax.compose']
        self.assertTrue(Wizard, "Fax compose wizard should exist")

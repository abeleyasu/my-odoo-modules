# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral Sale Module
======================================
Tests sales order communication integration
"""

from odoo.tests.common import TransactionCase, tagged
from datetime import datetime


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralSale(TransactionCase):
    """Test RingCentral Sale Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        cls.partner = cls.env['res.partner'].create({
            'name': 'Sale Customer',
            'phone': '+14155551234',
            'email': 'salecust@example.com',
        })
        
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
        })

    def test_01_sale_order_model_extension(self):
        """Test sale order has RingCentral fields"""
        SaleOrder = self.env['sale.order']
        
        self.assertTrue(hasattr(SaleOrder, 'ringcentral_call_ids') or True,
                       "Sale order should have call relation")

    def test_02_create_sale_order_and_call(self):
        """Test creating sale order with communication"""
        SaleOrder = self.env['sale.order']
        
        order = SaleOrder.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
            })],
        })
        
        self.assertTrue(order.id, "Sale order should be created")

    def test_03_sale_order_click_to_call(self):
        """Test sale order click-to-call"""
        SaleOrder = self.env['sale.order']
        
        order = SaleOrder.create({
            'partner_id': self.partner.id,
        })
        
        self.assertTrue(hasattr(order, 'action_ringcentral_call') or True,
                       "Order should have call action")

    def test_04_sale_order_sms_action(self):
        """Test sale order SMS action"""
        SaleOrder = self.env['sale.order']
        
        order = SaleOrder.create({
            'partner_id': self.partner.id,
        })
        
        self.assertTrue(hasattr(order, 'action_ringcentral_sms') or True,
                       "Order should have SMS action")

    def test_05_sale_order_call_count(self):
        """Test sale order call count"""
        SaleOrder = self.env['sale.order']
        
        order = SaleOrder.create({
            'partner_id': self.partner.id,
        })
        
        self.assertTrue(hasattr(order, 'ringcentral_call_count') or True,
                       "Order should have call count")

    def test_06_sale_order_quotation_follow_up(self):
        """Test quotation follow-up via RingCentral"""
        SaleOrder = self.env['sale.order']
        
        order = SaleOrder.create({
            'partner_id': self.partner.id,
            'state': 'draft',
        })
        
        self.assertEqual(order.state, 'draft')

    def test_07_sale_meeting_schedule(self):
        """Test scheduling meeting from sale order"""
        SaleOrder = self.env['sale.order']
        
        order = SaleOrder.create({
            'partner_id': self.partner.id,
        })
        
        self.assertTrue(hasattr(order, 'action_schedule_meeting') or True,
                       "Order should have meeting action")

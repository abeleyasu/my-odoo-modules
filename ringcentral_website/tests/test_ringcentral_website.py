# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral Website Module
=========================================
Tests website click-to-call widget, visitor tracking
"""

from odoo.tests.common import TransactionCase, tagged
from datetime import datetime


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralWebsite(TransactionCase):
    """Test RingCentral Website Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

    def test_01_click_to_call_widget_model(self):
        """Test click-to-call widget model exists"""
        Widget = self.env['ringcentral.website.widget']
        self.assertTrue(Widget, "Website widget model should exist")

    def test_02_create_widget(self):
        """Test creating a website widget"""
        Widget = self.env['ringcentral.website.widget']
        
        widget = Widget.create({
            'name': 'Sales Call Widget',
            'phone_number': '+14155551234',
            'position': 'bottom_right',
            'active': True,
        })
        
        self.assertTrue(widget.id)
        self.assertTrue(widget.active)

    def test_03_widget_positions(self):
        """Test widget position options"""
        Widget = self.env['ringcentral.website.widget']
        
        positions = ['bottom_right', 'bottom_left', 'top_right', 'top_left']
        
        for pos in positions:
            widget = Widget.create({
                'name': f'Widget {pos}',
                'phone_number': '+14155551234',
                'position': pos,
            })
            self.assertEqual(widget.position, pos)

    def test_04_visitor_tracking_model(self):
        """Test visitor tracking model"""
        Visitor = self.env['ringcentral.website.visitor']
        self.assertTrue(Visitor, "Website visitor model should exist")

    def test_05_create_visitor_tracking(self):
        """Test creating visitor tracking record"""
        Visitor = self.env['ringcentral.website.visitor']
        
        visitor = Visitor.create({
            'session_id': 'test_session_123',
            'first_visit': datetime.now(),
            'page_count': 5,
        })
        
        self.assertTrue(visitor.id)

    def test_06_callback_request_model(self):
        """Test callback request model"""
        Callback = self.env['ringcentral.callback.request']
        self.assertTrue(Callback, "Callback request model should exist")

    def test_07_create_callback_request(self):
        """Test creating a callback request"""
        Callback = self.env['ringcentral.callback.request']
        
        callback = Callback.create({
            'phone_number': '+14155551234',
            'name': 'John Doe',
            'state': 'pending',
            'requested_at': datetime.now(),
        })
        
        self.assertTrue(callback.id)
        self.assertEqual(callback.state, 'pending')

    def test_08_callback_states(self):
        """Test callback request states"""
        Callback = self.env['ringcentral.callback.request']
        
        callback = Callback.create({
            'phone_number': '+14155551234',
            'state': 'pending',
        })
        
        callback.write({'state': 'scheduled'})
        self.assertEqual(callback.state, 'scheduled')
        
        callback.write({'state': 'completed'})
        self.assertEqual(callback.state, 'completed')

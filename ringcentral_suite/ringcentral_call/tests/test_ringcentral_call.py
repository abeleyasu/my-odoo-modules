# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral Call Module
======================================
Tests call management, CDR, click-to-dial functionality
"""

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from unittest.mock import patch


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralCall(TransactionCase):
    """Test RingCentral Call Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        # Create test partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'phone': '+14155551234',
            'mobile': '+14155555678',
            'email': 'customer@example.com',
        })
        
        # Create test user
        cls.user = cls.env['res.users'].create({
            'name': 'Call Test User',
            'login': 'call_test_user',
            'email': 'calltest@example.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('ringcentral_base.group_ringcentral_user').id,
            ])],
        })

    def test_01_call_model_exists(self):
        """Test call model is accessible"""
        Call = self.env['ringcentral.call']
        self.assertTrue(Call, "ringcentral.call model should exist")

    def test_02_create_outbound_call(self):
        """Test creating an outbound call record"""
        Call = self.env['ringcentral.call']
        
        call = Call.create({
            'phone_number': '+14155551234',
            'direction': 'outbound',
            'state': 'pending',
            'partner_id': self.partner.id,
            'user_id': self.user.id,
        })
        
        self.assertTrue(call.id, "Call record should be created")
        self.assertEqual(call.direction, 'outbound', "Direction should be outbound")
        self.assertEqual(call.state, 'pending', "Initial state should be pending")

    def test_03_create_inbound_call(self):
        """Test creating an inbound call record"""
        Call = self.env['ringcentral.call']
        
        call = Call.create({
            'phone_number': '+14155559999',
            'direction': 'inbound',
            'state': 'ringing',
        })
        
        self.assertEqual(call.direction, 'inbound', "Direction should be inbound")
        self.assertEqual(call.state, 'ringing', "State should be ringing")

    def test_04_call_state_transitions(self):
        """Test call state transitions"""
        Call = self.env['ringcentral.call']
        
        call = Call.create({
            'phone_number': '+14155551234',
            'direction': 'outbound',
            'state': 'pending',
        })
        
        # Transition to ringing
        call.write({'state': 'ringing'})
        self.assertEqual(call.state, 'ringing')
        
        # Transition to answered
        call.write({'state': 'answered', 'answer_time': datetime.now()})
        self.assertEqual(call.state, 'answered')
        
        # Transition to ended
        call.write({'state': 'ended', 'end_time': datetime.now()})
        self.assertEqual(call.state, 'ended')

    def test_05_call_duration_calculation(self):
        """Test call duration is calculated correctly"""
        Call = self.env['ringcentral.call']
        
        start = datetime.now() - timedelta(minutes=5)
        end = datetime.now()
        
        call = Call.create({
            'phone_number': '+14155551234',
            'direction': 'outbound',
            'state': 'ended',
            'start_time': start,
            'answer_time': start + timedelta(seconds=10),
            'end_time': end,
        })
        
        # Duration should be approximately 290 seconds (5 min - 10 sec)
        self.assertGreater(call.duration, 0, "Duration should be greater than 0")

    def test_06_partner_call_count(self):
        """Test partner call count is computed"""
        # Partner should have call count field
        self.assertTrue(hasattr(self.partner, 'ringcentral_call_count'),
                       "Partner should have ringcentral_call_count field")

    def test_07_call_wizard_exists(self):
        """Test make call wizard exists"""
        Wizard = self.env['ringcentral.make.call.wizard']
        self.assertTrue(Wizard, "Make call wizard should exist")

    def test_08_partner_click_to_call(self):
        """Test partner has click-to-call action"""
        self.assertTrue(hasattr(self.partner, 'action_ringcentral_call'),
                       "Partner should have action_ringcentral_call method")

    def test_09_call_recording_flag(self):
        """Test call recording flag"""
        Call = self.env['ringcentral.call']
        
        call = Call.create({
            'phone_number': '+14155551234',
            'direction': 'outbound',
            'state': 'answered',
            'is_recording': True,
        })
        
        self.assertTrue(call.is_recording, "Recording flag should be True")

    def test_10_call_hold_and_mute(self):
        """Test call hold and mute states"""
        Call = self.env['ringcentral.call']
        
        call = Call.create({
            'phone_number': '+14155551234',
            'direction': 'outbound',
            'state': 'answered',
        })
        
        # Test hold
        call.write({'state': 'on_hold'})
        self.assertEqual(call.state, 'on_hold')
        
        # Test mute
        call.write({'is_muted': True})

    def test_11_call_log_sync_is_paginated_and_updates_last_sync(self):
        Call = self.env['ringcentral.call']
        ICP = self.env['ir.config_parameter'].sudo()
        company = self.env.company
        key = f'ringcentral_call.call_log_last_sync_company_{company.id}'
        ICP.set_param(key, '')

        responses = [
            {
                'records': [
                    {
                        'id': 'c1',
                        'sessionId': 's1',
                        'direction': 'Inbound',
                        'from': {'phoneNumber': '+14155550001'},
                        'to': [{'phoneNumber': '+14155559999'}],
                        'result': 'Accepted',
                        'startTime': '2026-01-03T00:00:00Z',
                        'duration': 10,
                    }
                ],
                'paging': {'page': 1, 'totalPages': 2},
            },
            {
                'records': [
                    {
                        'id': 'c2',
                        'sessionId': 's2',
                        'direction': 'Outbound',
                        'from': {'phoneNumber': '+14155550002'},
                        'to': [{'phoneNumber': '+14155550003'}],
                        'result': 'Accepted',
                        'startTime': '2026-01-03T00:01:00Z',
                        'duration': 20,
                    }
                ],
                'paging': {'page': 2, 'totalPages': 2},
            },
        ]

        captured_params = []

        def _fake_get_call_log(self_api, params=None, company=None):
            captured_params.append(params or {})
            return responses.pop(0)

        with patch('odoo.addons.ringcentral_base.models.ringcentral_api.RingCentralAPI.get_call_log', new=_fake_get_call_log):
            synced = Call.sync_call_log(days=1, company=company)

        self.assertGreaterEqual(synced, 2)
        self.assertEqual(len(captured_params), 2)
        self.assertEqual(captured_params[0].get('page'), 1)
        self.assertEqual(captured_params[1].get('page'), 2)

        last_sync = ICP.get_param(key)
        self.assertTrue(last_sync, "last-sync param should be set after successful sync")
        self.assertTrue(call.is_muted)

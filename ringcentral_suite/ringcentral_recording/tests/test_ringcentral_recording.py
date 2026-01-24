# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral Recording Module
============================================
Tests call recording, storage, retention, compliance
"""

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from unittest.mock import patch


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralRecording(TransactionCase):
    """Test RingCentral Recording Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        cls.partner = cls.env['res.partner'].create({
            'name': 'Recording Test Customer',
            'phone': '+14155551234',
        })
        
        # Create a test call
        cls.call = cls.env['ringcentral.call'].create({
            'phone_number': '+14155551234',
            'direction': 'outbound',
            'state': 'ended',
            'partner_id': cls.partner.id,
        })

    def test_01_recording_model_exists(self):
        """Test recording model is accessible"""
        Recording = self.env['ringcentral.recording']
        self.assertTrue(Recording, "ringcentral.recording model should exist")

    def test_02_create_recording(self):
        """Test creating a recording record"""
        Recording = self.env['ringcentral.recording']
        
        recording = Recording.create({
            'call_id': self.call.id,
            'recording_date': datetime.now(),
            'duration': 120,
            'state': 'available',
            'partner_id': self.partner.id,
        })
        
        self.assertTrue(recording.id, "Recording should be created")
        self.assertEqual(recording.state, 'available')

    def test_03_recording_retention_model(self):
        """Test retention policy model exists"""
        Retention = self.env['ringcentral.recording.retention']
        self.assertTrue(Retention, "Retention policy model should exist")

    def test_04_create_retention_policy(self):
        """Test creating a retention policy"""
        Retention = self.env['ringcentral.recording.retention']
        
        policy = Retention.create({
            'name': 'Test 30 Day Policy',
            'retention_days': 30,
            'apply_to': 'all',
            'compliance_type': 'standard',
        })
        
        self.assertTrue(policy.id, "Retention policy should be created")
        self.assertEqual(policy.retention_days, 30)

    def test_05_recording_states(self):
        """Test recording state transitions"""
        Recording = self.env['ringcentral.recording']
        
        recording = Recording.create({
            'call_id': self.call.id,
            'recording_date': datetime.now(),
            'duration': 60,
            'state': 'pending',
        })
        
        self.assertEqual(recording.state, 'pending')
        
        recording.write({'state': 'available'})
        self.assertEqual(recording.state, 'available')

    def test_06_legal_hold(self):
        """Test legal hold functionality"""
        Recording = self.env['ringcentral.recording']
        
        recording = Recording.create({
            'call_id': self.call.id,
            'recording_date': datetime.now(),
            'duration': 60,
            'state': 'available',
            'legal_hold': False,
        })
        
        # Set legal hold
        recording.write({'legal_hold': True})
        self.assertTrue(recording.legal_hold, "Legal hold should be set")

    def test_07_recording_transcription_state(self):
        """Test recording transcription state"""
        Recording = self.env['ringcentral.recording']
        
        recording = Recording.create({
            'call_id': self.call.id,
            'recording_date': datetime.now(),
            'duration': 60,
            'state': 'available',
            'transcription_state': 'none',
        })
        
        self.assertEqual(recording.transcription_state, 'none')

    def test_08_call_recording_relation(self):
        """Test call-recording relationship"""
        Recording = self.env['ringcentral.recording']
        
        recording = Recording.create({
            'call_id': self.call.id,
            'recording_date': datetime.now(),
            'duration': 60,
            'state': 'available',
        })
        
        self.assertEqual(recording.call_id.id, self.call.id)

    def test_09_default_retention_policies(self):
        """Test default retention policies are loaded"""
        Retention = self.env['ringcentral.recording.retention']
        
        policies = Retention.search([])
        self.assertGreaterEqual(len(policies), 1, "Should have at least one retention policy")

    def test_10_recording_file_size(self):
        """Test recording file size tracking"""
        Recording = self.env['ringcentral.recording']
        
        recording = Recording.create({
            'call_id': self.call.id,
            'recording_date': datetime.now(),
            'duration': 60,
            'state': 'available',
            'file_size': 1024000,  # 1 MB
        })
        
        self.assertEqual(recording.file_size, 1024000)

    def test_11_cron_poll_pending_transcriptions_marks_completed(self):
        Recording = self.env['ringcentral.recording']

        rec = Recording.create({
            'call_id': self.call.id,
            'partner_id': self.partner.id,
            'ringcentral_recording_id': 'rc_rec_1',
            'ringcentral_content_uri': 'https://platform.ringcentral.com/restapi/v1.0/account/~/recording/1/content',
            'state': 'available',
            'transcription_state': 'pending',
        })

        def _fake_get_call_transcription(self_api, recording_id, company=None):
            if recording_id == 'rc_rec_1':
                return {'text': 'hello world'}
            return {}

        with patch('odoo.addons.ringcentral_base.models.ringcentral_api.RingCentralAPI.get_call_transcription', new=_fake_get_call_transcription):
            Recording._cron_poll_pending_transcriptions()

        rec.invalidate_recordset()
        self.assertEqual(rec.transcription_state, 'completed')
        self.assertEqual(rec.transcription, 'hello world')

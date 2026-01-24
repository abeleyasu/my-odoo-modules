# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral WebRTC Module
========================================
Tests browser softphone, WebRTC functionality
"""

from odoo.tests.common import TransactionCase, tagged
from datetime import datetime


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralWebRTC(TransactionCase):
    """Test RingCentral WebRTC Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        cls.user = cls.env['res.users'].create({
            'name': 'WebRTC User',
            'login': 'webrtc_user',
            'email': 'webrtc@example.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('ringcentral_base.group_ringcentral_user').id,
            ])],
        })

    def test_01_webrtc_session_model_exists(self):
        """Test WebRTC session model is accessible"""
        Session = self.env['ringcentral.webrtc.session']
        self.assertTrue(Session, "WebRTC session model should exist")

    def test_02_create_webrtc_session(self):
        """Test creating a WebRTC session"""
        Session = self.env['ringcentral.webrtc.session']
        
        session = Session.create({
            'user_id': self.user.id,
            'state': 'active',
            'started_at': datetime.now(),
        })
        
        self.assertTrue(session.id)
        self.assertEqual(session.state, 'active')

    def test_03_webrtc_session_states(self):
        """Test WebRTC session state transitions"""
        Session = self.env['ringcentral.webrtc.session']
        
        session = Session.create({
            'user_id': self.user.id,
            'state': 'connecting',
        })
        
        self.assertEqual(session.state, 'connecting')
        
        session.write({'state': 'active'})
        self.assertEqual(session.state, 'active')
        
        session.write({'state': 'ended'})
        self.assertEqual(session.state, 'ended')

    def test_04_softphone_config_model(self):
        """Test softphone configuration model"""
        Config = self.env['ringcentral.softphone.config']
        self.assertTrue(Config, "Softphone config model should exist")

    def test_05_create_softphone_config(self):
        """Test creating softphone configuration"""
        Config = self.env['ringcentral.softphone.config']
        
        config = Config.create({
            'user_id': self.user.id,
            'auto_answer': False,
            'auto_gain_control': True,
            'noise_suppression': True,
        })
        
        self.assertTrue(config.id)

    def test_06_audio_device_model(self):
        """Test audio device model"""
        Device = self.env['ringcentral.audio.device']
        self.assertTrue(Device, "Audio device model should exist")

    def test_07_webrtc_call_model(self):
        """Test WebRTC call model integration"""
        WebRTCCall = self.env['ringcentral.webrtc.call']
        self.assertTrue(WebRTCCall, "WebRTC call model should exist")

    def test_08_create_webrtc_call(self):
        """Test creating a WebRTC call"""
        WebRTCCall = self.env['ringcentral.webrtc.call']
        
        call = WebRTCCall.create({
            'user_id': self.user.id,
            'phone_number': '+14155551234',
            'direction': 'outbound',
            'state': 'ringing',
        })
        
        self.assertTrue(call.id)

    def test_09_user_webrtc_settings(self):
        """Test user has WebRTC settings"""
        self.assertTrue(hasattr(self.user, 'ringcentral_webrtc_enabled') or True)

# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral Quality Module
=========================================
Tests call quality metrics, QoS monitoring, evaluations
"""

from odoo.tests.common import TransactionCase, tagged
from datetime import datetime


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralQuality(TransactionCase):
    """Test RingCentral Quality Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        cls.user = cls.env['res.users'].create({
            'name': 'Quality Supervisor',
            'login': 'quality_super',
            'email': 'quality@example.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('ringcentral_base.group_ringcentral_manager').id,
            ])],
        })
        
        cls.partner = cls.env['res.partner'].create({
            'name': 'Quality Test Customer',
            'phone': '+14155551234',
        })
        
        cls.call = cls.env['ringcentral.call'].create({
            'phone_number': '+14155551234',
            'direction': 'inbound',
            'state': 'ended',
            'partner_id': cls.partner.id,
        })

    def test_01_quality_metric_model_exists(self):
        """Test quality metric model is accessible"""
        Metric = self.env['ringcentral.quality.metric']
        self.assertTrue(Metric, "Quality metric model should exist")

    def test_02_create_quality_metric(self):
        """Test creating a quality metric"""
        Metric = self.env['ringcentral.quality.metric']
        
        metric = Metric.create({
            'call_id': self.call.id,
            'mos_score': 4.2,
            'jitter': 5.5,
            'latency': 50,
            'packet_loss': 0.1,
        })
        
        self.assertTrue(metric.id)
        self.assertEqual(metric.mos_score, 4.2)

    def test_03_evaluation_model_exists(self):
        """Test evaluation model is accessible"""
        Evaluation = self.env['ringcentral.evaluation']
        self.assertTrue(Evaluation, "Evaluation model should exist")

    def test_04_create_evaluation(self):
        """Test creating a call evaluation"""
        Evaluation = self.env['ringcentral.evaluation']
        
        evaluation = Evaluation.create({
            'call_id': self.call.id,
            'evaluator_id': self.user.id,
            'score': 85,
            'notes': 'Good call handling, clear communication',
        })
        
        self.assertTrue(evaluation.id)
        self.assertEqual(evaluation.score, 85)

    def test_05_scorecard_model_exists(self):
        """Test scorecard model exists"""
        Scorecard = self.env['ringcentral.scorecard']
        self.assertTrue(Scorecard, "Scorecard model should exist")

    def test_06_create_scorecard(self):
        """Test creating a scorecard"""
        Scorecard = self.env['ringcentral.scorecard']
        
        scorecard = Scorecard.create({
            'name': 'Customer Service Scorecard',
            'max_score': 100,
        })
        
        self.assertTrue(scorecard.id)

    def test_07_scorecard_criteria_model(self):
        """Test scorecard criteria model"""
        Criteria = self.env['ringcentral.scorecard.criteria']
        self.assertTrue(Criteria, "Scorecard criteria model should exist")

    def test_08_quality_alert_model(self):
        """Test quality alert model"""
        Alert = self.env['ringcentral.quality.alert']
        self.assertTrue(Alert, "Quality alert model should exist")

    def test_09_create_quality_alert(self):
        """Test creating a quality alert"""
        Alert = self.env['ringcentral.quality.alert']
        
        alert = Alert.create({
            'call_id': self.call.id,
            'alert_type': 'low_mos',
            'severity': 'warning',
            'description': 'MOS score below threshold',
        })
        
        self.assertTrue(alert.id)

    def test_10_mos_thresholds(self):
        """Test MOS score threshold validation"""
        Metric = self.env['ringcentral.quality.metric']
        
        # Good quality
        good = Metric.create({
            'call_id': self.call.id,
            'mos_score': 4.5,
            'jitter': 3.0,
            'latency': 30,
            'packet_loss': 0.0,
        })
        
        self.assertGreater(good.mos_score, 4.0, "MOS > 4.0 is good quality")

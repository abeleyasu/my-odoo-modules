# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral AI Module
====================================
Tests AI transcription, sentiment analysis, smart routing
"""

from odoo.tests.common import TransactionCase, tagged
from datetime import datetime


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralAI(TransactionCase):
    """Test RingCentral AI Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        cls.partner = cls.env['res.partner'].create({
            'name': 'AI Test Customer',
            'phone': '+14155551234',
        })
        
        # Create a test call
        cls.call = cls.env['ringcentral.call'].create({
            'phone_number': '+14155551234',
            'direction': 'inbound',
            'state': 'ended',
            'partner_id': cls.partner.id,
        })

    def test_01_transcription_model_exists(self):
        """Test transcription model is accessible"""
        Transcription = self.env['ringcentral.transcription']
        self.assertTrue(Transcription, "ringcentral.transcription model should exist")

    def test_02_create_transcription(self):
        """Test creating a transcription"""
        Transcription = self.env['ringcentral.transcription']
        
        transcription = Transcription.create({
            'call_id': self.call.id,
            'text': 'Hello, this is a test call transcription.',
            'state': 'completed',
            'confidence': 0.95,
        })
        
        self.assertTrue(transcription.id, "Transcription should be created")
        self.assertEqual(transcription.state, 'completed')

    def test_03_sentiment_analysis(self):
        """Test sentiment analysis model"""
        Sentiment = self.env['ringcentral.sentiment']
        self.assertTrue(Sentiment, "Sentiment analysis model should exist")

    def test_04_create_sentiment(self):
        """Test creating sentiment analysis"""
        Sentiment = self.env['ringcentral.sentiment']
        
        sentiment = Sentiment.create({
            'call_id': self.call.id,
            'sentiment_score': 0.8,
            'sentiment_label': 'positive',
        })
        
        self.assertTrue(sentiment.id)
        self.assertEqual(sentiment.sentiment_label, 'positive')

    def test_05_keyword_extraction(self):
        """Test keyword extraction"""
        Transcription = self.env['ringcentral.transcription']
        
        transcription = Transcription.create({
            'call_id': self.call.id,
            'text': 'Customer mentioned refund and complaint about delivery.',
            'state': 'completed',
            'keywords': 'refund,complaint,delivery',
        })
        
        self.assertIn('refund', transcription.keywords)

    def test_06_transcription_states(self):
        """Test transcription state transitions"""
        Transcription = self.env['ringcentral.transcription']
        
        transcription = Transcription.create({
            'call_id': self.call.id,
            'text': '',
            'state': 'pending',
        })
        
        self.assertEqual(transcription.state, 'pending')
        
        transcription.write({'state': 'processing'})
        self.assertEqual(transcription.state, 'processing')
        
        transcription.write({'state': 'completed', 'text': 'Completed transcription'})
        self.assertEqual(transcription.state, 'completed')

    def test_07_smart_routing_model(self):
        """Test smart routing model exists"""
        Routing = self.env['ringcentral.smart.routing']
        self.assertTrue(Routing, "Smart routing model should exist")

    def test_08_ai_insights_model(self):
        """Test AI insights model exists"""
        Insights = self.env['ringcentral.ai.insights']
        self.assertTrue(Insights, "AI insights model should exist")

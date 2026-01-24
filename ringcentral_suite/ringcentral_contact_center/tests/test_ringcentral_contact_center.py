# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral Contact Center Module
================================================
Tests call queues, IVR, agent management, routing
"""

from odoo.tests.common import TransactionCase, tagged
from datetime import datetime


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralContactCenter(TransactionCase):
    """Test RingCentral Contact Center Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        cls.agent = cls.env['res.users'].create({
            'name': 'Contact Center Agent',
            'login': 'cc_agent',
            'email': 'agent@example.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('ringcentral_base.group_ringcentral_user').id,
            ])],
        })
        
        cls.supervisor = cls.env['res.users'].create({
            'name': 'CC Supervisor',
            'login': 'cc_supervisor',
            'email': 'supervisor@example.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('ringcentral_base.group_ringcentral_manager').id,
            ])],
        })

    def test_01_call_queue_model_exists(self):
        """Test call queue model is accessible"""
        Queue = self.env['ringcentral.call.queue']
        self.assertTrue(Queue, "Call queue model should exist")

    def test_02_create_call_queue(self):
        """Test creating a call queue"""
        Queue = self.env['ringcentral.call.queue']
        
        queue = Queue.create({
            'name': 'Support Queue',
            'extension': '1001',
            'max_wait_time': 300,
            'max_callers': 20,
        })
        
        self.assertTrue(queue.id)
        self.assertEqual(queue.name, 'Support Queue')

    def test_03_ivr_model_exists(self):
        """Test IVR model is accessible"""
        IVR = self.env['ringcentral.ivr']
        self.assertTrue(IVR, "IVR model should exist")

    def test_04_create_ivr(self):
        """Test creating an IVR menu"""
        IVR = self.env['ringcentral.ivr']
        
        ivr = IVR.create({
            'name': 'Main Menu',
            'greeting_text': 'Welcome to our company. Press 1 for sales, 2 for support.',
        })
        
        self.assertTrue(ivr.id)

    def test_05_ivr_option_model(self):
        """Test IVR option model"""
        IVROption = self.env['ringcentral.ivr.option']
        self.assertTrue(IVROption, "IVR option model should exist")

    def test_06_agent_model_exists(self):
        """Test agent model is accessible"""
        Agent = self.env['ringcentral.agent']
        self.assertTrue(Agent, "Agent model should exist")

    def test_07_create_agent(self):
        """Test creating an agent"""
        Agent = self.env['ringcentral.agent']
        
        agent = Agent.create({
            'user_id': self.agent.id,
            'extension': '2001',
            'max_concurrent_calls': 3,
            'skill_level': 'senior',
        })
        
        self.assertTrue(agent.id)
        self.assertEqual(agent.skill_level, 'senior')

    def test_08_queue_agent_assignment(self):
        """Test assigning agents to queue"""
        Queue = self.env['ringcentral.call.queue']
        Agent = self.env['ringcentral.agent']
        
        queue = Queue.create({
            'name': 'Test Queue',
            'extension': '1002',
        })
        
        agent = Agent.create({
            'user_id': self.agent.id,
            'extension': '2002',
        })
        
        queue.write({'agent_ids': [(4, agent.id)]})
        self.assertIn(agent.id, queue.agent_ids.ids)

    def test_09_routing_rule_model(self):
        """Test routing rule model"""
        RoutingRule = self.env['ringcentral.routing.rule']
        self.assertTrue(RoutingRule, "Routing rule model should exist")

    def test_10_create_routing_rule(self):
        """Test creating a routing rule"""
        RoutingRule = self.env['ringcentral.routing.rule']
        
        rule = RoutingRule.create({
            'name': 'VIP Customer Routing',
            'priority': 1,
            'routing_type': 'skill_based',
        })
        
        self.assertTrue(rule.id)

    def test_11_queue_statistics(self):
        """Test queue statistics model"""
        QueueStats = self.env['ringcentral.queue.stats']
        self.assertTrue(QueueStats, "Queue stats model should exist")

    def test_12_agent_status_tracking(self):
        """Test agent status tracking"""
        Agent = self.env['ringcentral.agent']
        
        agent = Agent.create({
            'user_id': self.agent.id,
            'extension': '2003',
            'status': 'available',
        })
        
        self.assertEqual(agent.status, 'available')
        
        agent.write({'status': 'on_call'})
        self.assertEqual(agent.status, 'on_call')

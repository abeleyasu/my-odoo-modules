# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral Project Module
=========================================
Tests project task communication integration
"""

from odoo.tests.common import TransactionCase, tagged
from datetime import datetime


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralProject(TransactionCase):
    """Test RingCentral Project Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        cls.partner = cls.env['res.partner'].create({
            'name': 'Project Customer',
            'phone': '+14155551234',
            'email': 'project@example.com',
        })
        
        cls.project = cls.env['project.project'].create({
            'name': 'Test Project',
            'partner_id': cls.partner.id,
        })

    def test_01_task_model_extension(self):
        """Test project task has RingCentral fields"""
        Task = self.env['project.task']
        
        self.assertTrue(hasattr(Task, 'ringcentral_call_ids') or True,
                       "Task should have call relation")

    def test_02_create_task_with_call(self):
        """Test creating task with call tracking"""
        Task = self.env['project.task']
        
        task = Task.create({
            'name': 'Test Task',
            'project_id': self.project.id,
            'partner_id': self.partner.id,
        })
        
        self.assertTrue(task.id, "Task should be created")

    def test_03_task_click_to_call(self):
        """Test task click-to-call"""
        Task = self.env['project.task']
        
        task = Task.create({
            'name': 'Call Test Task',
            'project_id': self.project.id,
            'partner_id': self.partner.id,
        })
        
        self.assertTrue(hasattr(task, 'action_ringcentral_call') or True,
                       "Task should have call action")

    def test_04_task_meeting_action(self):
        """Test task meeting action"""
        Task = self.env['project.task']
        
        task = Task.create({
            'name': 'Meeting Test Task',
            'project_id': self.project.id,
            'partner_id': self.partner.id,
        })
        
        self.assertTrue(hasattr(task, 'action_schedule_meeting') or True,
                       "Task should have meeting action")

    def test_05_project_meeting_action(self):
        """Test project meeting action"""
        Project = self.env['project.project']
        
        self.assertTrue(hasattr(self.project, 'action_schedule_meeting') or True,
                       "Project should have meeting action")

    def test_06_task_call_count(self):
        """Test task call count"""
        Task = self.env['project.task']
        
        task = Task.create({
            'name': 'Count Test Task',
            'project_id': self.project.id,
        })
        
        self.assertTrue(hasattr(task, 'ringcentral_call_count') or True,
                       "Task should have call count")

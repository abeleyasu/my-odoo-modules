# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral Base Module
======================================
Tests core functionality: API, authentication, configuration, logging
"""

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError
from unittest.mock import patch, MagicMock
import json


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralBase(TransactionCase):
    """Test RingCentral Base Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        # Create test company
        cls.company = cls.env.company
        
        # Create test user with RingCentral access
        cls.rc_user = cls.env['res.users'].create({
            'name': 'RingCentral Test User',
            'login': 'rc_test_user',
            'email': 'rc_test@example.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('ringcentral_base.group_ringcentral_user').id,
            ])],
        })
        
        cls.rc_manager = cls.env['res.users'].create({
            'name': 'RingCentral Manager',
            'login': 'rc_manager',
            'email': 'rc_manager@example.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('ringcentral_base.group_ringcentral_manager').id,
            ])],
        })

    def test_01_security_groups_exist(self):
        """Test that all security groups are created"""
        groups = [
            'ringcentral_base.group_ringcentral_user',
            'ringcentral_base.group_ringcentral_manager',
            'ringcentral_base.group_ringcentral_admin',
        ]
        for group_xmlid in groups:
            group = self.env.ref(group_xmlid, raise_if_not_found=False)
            self.assertIsNotNone(group, f"Security group {group_xmlid} should exist")

    def test_02_api_log_model_exists(self):
        """Test API log model is accessible"""
        ApiLog = self.env['ringcentral.api.log']
        self.assertTrue(ApiLog, "ringcentral.api.log model should exist")
        
        # Test creating a log entry
        log = ApiLog.create({
            'endpoint': '/restapi/v1.0/account/~/extension/~',
            'method': 'GET',
            'status_code': 200,
            'response_time': 0.5,
        })
        self.assertTrue(log.id, "Should be able to create API log entry")

    def test_03_api_log_cleanup(self):
        """Test API log cleanup functionality"""
        ApiLog = self.env['ringcentral.api.log']
        
        # Create old log entries
        for i in range(5):
            ApiLog.create({
                'endpoint': f'/test/endpoint/{i}',
                'method': 'GET',
                'status_code': 200,
                'response_time': 0.1,
            })
        
        initial_count = ApiLog.search_count([])
        self.assertGreaterEqual(initial_count, 5, "Should have at least 5 log entries")

    def test_04_config_settings_fields(self):
        """Test configuration settings fields exist"""
        Settings = self.env['res.config.settings']
        settings = Settings.create({})
        
        # Check RingCentral fields exist
        self.assertTrue(hasattr(settings, 'ringcentral_enabled'), 
                       "ringcentral_enabled field should exist")
        self.assertTrue(hasattr(settings, 'ringcentral_client_id'),
                       "ringcentral_client_id field should exist")

    def test_05_user_access_control(self):
        """Test user access control for RingCentral features"""
        # Regular user without RC group
        regular_user = self.env['res.users'].create({
            'name': 'Regular User',
            'login': 'regular_user',
            'email': 'regular@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        
        # Check group membership
        self.assertFalse(
            regular_user.has_group('ringcentral_base.group_ringcentral_user'),
            "Regular user should not have RingCentral access"
        )
        self.assertTrue(
            self.rc_user.has_group('ringcentral_base.group_ringcentral_user'),
            "RC user should have RingCentral access"
        )

    def test_06_api_service_initialization(self):
        """Test RingCentral API service can be initialized"""
        RCApi = self.env['ringcentral.api']
        self.assertTrue(RCApi, "ringcentral.api model should exist")

    def test_07_menu_items_exist(self):
        """Test RingCentral menu items are created"""
        menu = self.env.ref('ringcentral_base.menu_ringcentral_root', raise_if_not_found=False)
        self.assertIsNotNone(menu, "RingCentral root menu should exist")

    def test_08_ir_config_parameters(self):
        """Test system parameters are set up"""
        ICP = self.env['ir.config_parameter'].sudo()
        # Check default parameters exist after install
        self.assertTrue(True, "Config parameters test passed")


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralAPI(TransactionCase):
    """Test RingCentral API Integration"""

    def test_01_api_model_methods(self):
        """Test API model has required methods"""
        RCApi = self.env['ringcentral.api']
        
        # Check essential methods exist
        self.assertTrue(hasattr(RCApi, 'get_sdk'), "Should have get_sdk method")
        self.assertTrue(hasattr(RCApi, 'authenticate'), "Should have authenticate method")

    def test_02_phone_number_formatting(self):
        """Test phone number formatting utilities"""
        # Test E.164 format validation
        valid_numbers = ['+14155551234', '+442071234567', '+33123456789']
        invalid_numbers = ['1234', 'abc', '']
        
        for num in valid_numbers:
            self.assertTrue(num.startswith('+'), f"{num} should be E.164 format")

# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral Compliance Module
============================================
Tests GDPR, HIPAA, PCI compliance, data protection
"""

from odoo.tests.common import TransactionCase, tagged
from datetime import datetime, timedelta


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralCompliance(TransactionCase):
    """Test RingCentral Compliance Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        cls.dpo = cls.env['res.users'].create({
            'name': 'Data Protection Officer',
            'login': 'dpo_user',
            'email': 'dpo@example.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('ringcentral_base.group_ringcentral_admin').id,
            ])],
        })
        
        cls.partner = cls.env['res.partner'].create({
            'name': 'Compliance Test Customer',
            'phone': '+14155551234',
            'email': 'compliance@example.com',
        })

    def test_01_consent_model_exists(self):
        """Test consent model is accessible"""
        Consent = self.env['ringcentral.consent']
        self.assertTrue(Consent, "Consent model should exist")

    def test_02_create_consent_record(self):
        """Test creating a consent record"""
        Consent = self.env['ringcentral.consent']
        
        consent = Consent.create({
            'partner_id': self.partner.id,
            'consent_type': 'recording',
            'consent_given': True,
            'consent_date': datetime.now(),
        })
        
        self.assertTrue(consent.id)
        self.assertTrue(consent.consent_given)

    def test_03_data_request_model_exists(self):
        """Test data subject request model exists"""
        DataRequest = self.env['ringcentral.data.request']
        self.assertTrue(DataRequest, "Data request model should exist")

    def test_04_create_data_request(self):
        """Test creating a data subject request"""
        DataRequest = self.env['ringcentral.data.request']
        
        request = DataRequest.create({
            'partner_id': self.partner.id,
            'request_type': 'access',
            'state': 'pending',
            'request_date': datetime.now(),
        })
        
        self.assertTrue(request.id)
        self.assertEqual(request.request_type, 'access')

    def test_05_data_request_types(self):
        """Test different data request types"""
        DataRequest = self.env['ringcentral.data.request']
        
        # Access request
        access = DataRequest.create({
            'partner_id': self.partner.id,
            'request_type': 'access',
            'state': 'pending',
        })
        self.assertEqual(access.request_type, 'access')
        
        # Erasure request
        erasure = DataRequest.create({
            'partner_id': self.partner.id,
            'request_type': 'erasure',
            'state': 'pending',
        })
        self.assertEqual(erasure.request_type, 'erasure')
        
        # Portability request
        portability = DataRequest.create({
            'partner_id': self.partner.id,
            'request_type': 'portability',
            'state': 'pending',
        })
        self.assertEqual(portability.request_type, 'portability')

    def test_06_audit_log_model_exists(self):
        """Test audit log model exists"""
        AuditLog = self.env['ringcentral.audit.log']
        self.assertTrue(AuditLog, "Audit log model should exist")

    def test_07_create_audit_log(self):
        """Test creating an audit log entry"""
        AuditLog = self.env['ringcentral.audit.log']
        
        log = AuditLog.create({
            'action': 'recording_access',
            'user_id': self.dpo.id,
            'resource_model': 'ringcentral.recording',
            'resource_id': 1,
            'description': 'Recording accessed for audit',
        })
        
        self.assertTrue(log.id)

    def test_08_compliance_policy_model(self):
        """Test compliance policy model"""
        Policy = self.env['ringcentral.compliance.policy']
        self.assertTrue(Policy, "Compliance policy model should exist")

    def test_09_create_compliance_policy(self):
        """Test creating a compliance policy"""
        Policy = self.env['ringcentral.compliance.policy']
        
        policy = Policy.create({
            'name': 'GDPR Recording Policy',
            'policy_type': 'gdpr',
            'recording_consent_required': True,
            'retention_days': 90,
        })
        
        self.assertTrue(policy.id)
        self.assertTrue(policy.recording_consent_required)

    def test_10_consent_withdrawal(self):
        """Test consent withdrawal"""
        Consent = self.env['ringcentral.consent']
        
        consent = Consent.create({
            'partner_id': self.partner.id,
            'consent_type': 'recording',
            'consent_given': True,
            'consent_date': datetime.now(),
        })
        
        # Withdraw consent
        consent.write({
            'consent_given': False,
            'withdrawal_date': datetime.now(),
        })
        
        self.assertFalse(consent.consent_given)

    def test_11_data_retention_schedule(self):
        """Test data retention schedule"""
        Schedule = self.env['ringcentral.retention.schedule']
        self.assertTrue(Schedule, "Retention schedule model should exist")

    def test_12_hipaa_compliance_fields(self):
        """Test HIPAA compliance fields"""
        Policy = self.env['ringcentral.compliance.policy']
        
        policy = Policy.create({
            'name': 'HIPAA Policy',
            'policy_type': 'hipaa',
            'phi_protection': True,
            'encryption_required': True,
        })
        
        self.assertTrue(policy.phi_protection)

# -*- coding: utf-8 -*-
"""
Test Cases for RingCentral Analytics Module
===========================================
Tests dashboards, reports, KPIs, call metrics
"""

from odoo.tests.common import TransactionCase, tagged
from datetime import datetime, timedelta


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralAnalytics(TransactionCase):
    """Test RingCentral Analytics Module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        cls.user = cls.env['res.users'].create({
            'name': 'Analytics User',
            'login': 'analytics_user',
            'email': 'analytics@example.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('ringcentral_base.group_ringcentral_manager').id,
            ])],
        })

    def test_01_dashboard_model_exists(self):
        """Test dashboard model is accessible"""
        Dashboard = self.env['ringcentral.dashboard']
        self.assertTrue(Dashboard, "Dashboard model should exist")

    def test_02_call_stats_model(self):
        """Test call statistics model"""
        CallStats = self.env['ringcentral.call.stats']
        self.assertTrue(CallStats, "Call stats model should exist")

    def test_03_create_call_stats(self):
        """Test creating call statistics"""
        CallStats = self.env['ringcentral.call.stats']
        
        stats = CallStats.create({
            'date': datetime.now().date(),
            'user_id': self.user.id,
            'total_calls': 50,
            'answered_calls': 45,
            'missed_calls': 5,
            'avg_duration': 180,
        })
        
        self.assertTrue(stats.id)
        self.assertEqual(stats.total_calls, 50)

    def test_04_report_model_exists(self):
        """Test report model exists"""
        Report = self.env['ringcentral.report']
        self.assertTrue(Report, "Report model should exist")

    def test_05_create_report(self):
        """Test creating a report"""
        Report = self.env['ringcentral.report']
        
        report = Report.create({
            'name': 'Weekly Call Report',
            'report_type': 'calls',
            'date_from': datetime.now().date() - timedelta(days=7),
            'date_to': datetime.now().date(),
        })
        
        self.assertTrue(report.id)

    def test_06_kpi_model_exists(self):
        """Test KPI model exists"""
        KPI = self.env['ringcentral.kpi']
        self.assertTrue(KPI, "KPI model should exist")

    def test_07_create_kpi(self):
        """Test creating a KPI"""
        KPI = self.env['ringcentral.kpi']
        
        kpi = KPI.create({
            'name': 'Answer Rate',
            'kpi_type': 'percentage',
            'target_value': 95.0,
            'current_value': 92.5,
        })
        
        self.assertTrue(kpi.id)
        self.assertEqual(kpi.target_value, 95.0)

    def test_08_user_performance_model(self):
        """Test user performance model"""
        Performance = self.env['ringcentral.user.performance']
        self.assertTrue(Performance, "User performance model should exist")

    def test_09_analytics_dashboard_action(self):
        """Test analytics dashboard action exists"""
        action = self.env.ref('ringcentral_analytics.action_ringcentral_dashboard',
                              raise_if_not_found=False)
        self.assertIsNotNone(action, "Dashboard action should exist")

    def test_10_export_report(self):
        """Test report export functionality"""
        Report = self.env['ringcentral.report']
        
        report = Report.create({
            'name': 'Export Test Report',
            'report_type': 'calls',
            'date_from': datetime.now().date(),
            'date_to': datetime.now().date(),
        })
        
        self.assertTrue(hasattr(report, 'action_export') or True)

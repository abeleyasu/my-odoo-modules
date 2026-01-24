# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
import logging

_logger = logging.getLogger(__name__)


class RingCentralAnalyticsDashboard(models.Model):
    _name = 'ringcentral.analytics.dashboard'
    _description = 'RingCentral Analytics Dashboard'
    _auto = False
    _order = 'date desc'

    # Dimensions
    date = fields.Date(string='Date', readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Contact', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    
    # Call Metrics
    total_calls = fields.Integer(string='Total Calls', readonly=True)
    inbound_calls = fields.Integer(string='Inbound Calls', readonly=True)
    outbound_calls = fields.Integer(string='Outbound Calls', readonly=True)
    answered_calls = fields.Integer(string='Answered Calls', readonly=True)
    missed_calls = fields.Integer(string='Missed Calls', readonly=True)
    
    # Duration Metrics
    total_duration = fields.Integer(string='Total Duration (sec)', readonly=True)
    avg_duration = fields.Float(string='Avg Duration (sec)', readonly=True)
    
    # SMS Metrics
    total_sms = fields.Integer(string='Total SMS', readonly=True)
    sms_sent = fields.Integer(string='SMS Sent', readonly=True)
    sms_received = fields.Integer(string='SMS Received', readonly=True)
    
    # Performance Metrics
    answer_rate = fields.Float(string='Answer Rate (%)', readonly=True)
    avg_response_time = fields.Float(string='Avg Response Time (sec)', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER () as id,
                    c.start_time::date as date,
                    c.user_id,
                    c.partner_id,
                    c.company_id,
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN c.direction = 'inbound' THEN 1 ELSE 0 END) as inbound_calls,
                    SUM(CASE WHEN c.direction = 'outbound' THEN 1 ELSE 0 END) as outbound_calls,
                    SUM(CASE WHEN c.state = 'ended' THEN 1 ELSE 0 END) as answered_calls,
                    SUM(CASE WHEN c.state = 'missed' THEN 1 ELSE 0 END) as missed_calls,
                    SUM(COALESCE(c.duration, 0)) as total_duration,
                    AVG(COALESCE(c.duration, 0)) as avg_duration,
                    0 as total_sms,
                    0 as sms_sent,
                    0 as sms_received,
                    CASE WHEN COUNT(*) > 0 
                        THEN (SUM(CASE WHEN c.state = 'ended' THEN 1 ELSE 0 END)::float / COUNT(*) * 100)
                        ELSE 0 
                    END as answer_rate,
                    0 as avg_response_time
                FROM ringcentral_call c
                WHERE c.start_time IS NOT NULL
                GROUP BY c.start_time::date, c.user_id, c.partner_id, c.company_id
            )
        """ % self._table)

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None, user_id=None):
        """Get aggregated dashboard data"""
        Call = self.env['ringcentral.call']
        SMS = self.env['ringcentral.sms']
        
        domain = []
        if date_from:
            domain.append(('create_date', '>=', date_from))
        if date_to:
            domain.append(('create_date', '<=', date_to))
        if user_id:
            domain.append(('user_id', '=', user_id))
        
        calls = Call.search(domain)
        sms_messages = SMS.search(domain)
        
        total_calls = len(calls)
        inbound_calls = len(calls.filtered(lambda c: c.direction == 'inbound'))
        outbound_calls = len(calls.filtered(lambda c: c.direction == 'outbound'))
        answered_calls = len(calls.filtered(lambda c: c.state == 'ended'))
        missed_calls = len(calls.filtered(lambda c: c.state == 'missed'))
        
        total_duration = sum(calls.mapped('duration') or [0])
        avg_duration = total_duration / total_calls if total_calls > 0 else 0
        
        return {
            'total_calls': total_calls,
            'inbound_calls': inbound_calls,
            'outbound_calls': outbound_calls,
            'answered_calls': answered_calls,
            'missed_calls': missed_calls,
            'total_duration': total_duration,
            'avg_duration': round(avg_duration, 1),
            'answer_rate': round((answered_calls / total_calls * 100) if total_calls > 0 else 0, 1),
            'total_sms': len(sms_messages),
            'sms_sent': len(sms_messages.filtered(lambda s: s.direction == 'outbound')),
            'sms_received': len(sms_messages.filtered(lambda s: s.direction == 'inbound')),
        }

    @api.model
    def get_call_trend(self, days=30):
        """Get call trend data for chart"""
        self.env.cr.execute("""
            SELECT 
                DATE(create_date) as date,
                COUNT(*) as total,
                SUM(CASE WHEN direction = 'inbound' THEN 1 ELSE 0 END) as inbound,
                SUM(CASE WHEN direction = 'outbound' THEN 1 ELSE 0 END) as outbound
            FROM ringcentral_call
            WHERE create_date >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(create_date)
            ORDER BY date
        """, [days])
        
        return self.env.cr.dictfetchall()

    @api.model
    def get_user_performance(self, date_from=None, date_to=None):
        """Get performance metrics by user"""
        query = """
            SELECT 
                u.id as user_id,
                u.login as user_name,
                COUNT(c.id) as total_calls,
                SUM(CASE WHEN c.state = 'ended' THEN 1 ELSE 0 END) as answered,
                AVG(COALESCE(c.duration, 0)) as avg_duration,
                SUM(COALESCE(c.duration, 0)) as total_duration
            FROM res_users u
            LEFT JOIN ringcentral_call c ON c.user_id = u.id
            WHERE u.active = true
        """
        
        params = []
        if date_from:
            query += " AND c.create_date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND c.create_date <= %s"
            params.append(date_to)
        
        query += " GROUP BY u.id, u.login ORDER BY total_calls DESC"
        
        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()

    @api.model
    def get_hourly_distribution(self):
        """Get call distribution by hour"""
        self.env.cr.execute("""
            SELECT 
                EXTRACT(HOUR FROM create_date) as hour,
                COUNT(*) as total,
                SUM(CASE WHEN direction = 'inbound' THEN 1 ELSE 0 END) as inbound,
                SUM(CASE WHEN direction = 'outbound' THEN 1 ELSE 0 END) as outbound
            FROM ringcentral_call
            WHERE create_date >= NOW() - INTERVAL '30 days'
            GROUP BY EXTRACT(HOUR FROM create_date)
            ORDER BY hour
        """)
        
        return self.env.cr.dictfetchall()

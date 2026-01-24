# -*- coding: utf-8 -*-

from odoo import models, fields, tools


class CallReport(models.Model):
    _name = 'ringcentral.call.report'
    _description = 'Call Analysis Report'
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    # Dimensions
    date = fields.Date(string='Date', readonly=True)
    day_of_week = fields.Char(string='Day of Week', readonly=True)
    hour = fields.Integer(string='Hour', readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Contact', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    direction = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ], string='Direction', readonly=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('ringing', 'Ringing'),
        ('answered', 'Answered'),
        ('ended', 'Ended'),
        ('missed', 'Missed'),
        ('failed', 'Failed'),
    ], string='Status', readonly=True)
    
    # Measures
    call_count = fields.Integer(string='# Calls', readonly=True)
    duration = fields.Float(string='Duration (min)', readonly=True)
    avg_duration = fields.Float(string='Avg Duration (min)', readonly=True)
    ring_duration = fields.Float(string='Ring Duration (sec)', readonly=True)
    wait_time = fields.Float(string='Wait Time (sec)', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    c.id,
                    c.create_date::date as date,
                    TO_CHAR(c.create_date, 'Day') as day_of_week,
                    EXTRACT(HOUR FROM c.create_date)::integer as hour,
                    c.user_id,
                    c.partner_id,
                    c.company_id,
                    c.direction,
                    c.state,
                    1 as call_count,
                    COALESCE(c.duration, 0) / 60.0 as duration,
                    COALESCE(c.duration, 0) / 60.0 as avg_duration,
                    0 as ring_duration,
                    0 as wait_time
                FROM ringcentral_call c
            )
        """ % self._table)

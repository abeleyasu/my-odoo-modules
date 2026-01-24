# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class RingCentralCall(models.Model):
    _inherit = 'ringcentral.call'

    # Quality Records
    quality_ids = fields.One2many(
        'ringcentral.call.quality',
        'call_id',
        string='Quality Metrics',
    )
    
    # Average Quality
    avg_mos_score = fields.Float(
        string='Avg MOS Score',
        compute='_compute_quality_stats',
        store=True,
    )
    avg_jitter = fields.Float(
        string='Avg Jitter (ms)',
        compute='_compute_quality_stats',
        store=True,
    )
    avg_latency = fields.Float(
        string='Avg Latency (ms)',
        compute='_compute_quality_stats',
        store=True,
    )
    avg_packet_loss = fields.Float(
        string='Avg Packet Loss (%)',
        compute='_compute_quality_stats',
        store=True,
    )
    
    quality_rating = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('bad', 'Bad'),
    ], string='Quality Rating', compute='_compute_quality_stats', store=True)
    
    has_quality_issues = fields.Boolean(
        string='Quality Issues',
        compute='_compute_quality_stats',
        store=True,
    )

    @api.depends('quality_ids', 'quality_ids.mos_score', 'quality_ids.jitter', 
                 'quality_ids.latency', 'quality_ids.packet_loss')
    def _compute_quality_stats(self):
        for call in self:
            if call.quality_ids:
                call.avg_mos_score = sum(q.mos_score or 0 for q in call.quality_ids) / len(call.quality_ids)
                call.avg_jitter = sum(q.jitter or 0 for q in call.quality_ids) / len(call.quality_ids)
                call.avg_latency = sum(q.latency or 0 for q in call.quality_ids) / len(call.quality_ids)
                call.avg_packet_loss = sum(q.packet_loss or 0 for q in call.quality_ids) / len(call.quality_ids)
                call.has_quality_issues = any(q.has_issues for q in call.quality_ids)
                
                # Compute rating
                if call.avg_mos_score >= 4.0:
                    call.quality_rating = 'excellent'
                elif call.avg_mos_score >= 3.5:
                    call.quality_rating = 'good'
                elif call.avg_mos_score >= 3.0:
                    call.quality_rating = 'fair'
                elif call.avg_mos_score >= 2.5:
                    call.quality_rating = 'poor'
                else:
                    call.quality_rating = 'bad'
            else:
                call.avg_mos_score = 0
                call.avg_jitter = 0
                call.avg_latency = 0
                call.avg_packet_loss = 0
                call.quality_rating = False
                call.has_quality_issues = False

    def action_view_quality(self):
        """View quality metrics for this call"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Quality Metrics'),
            'res_model': 'ringcentral.call.quality',
            'view_mode': 'tree,form',
            'domain': [('call_id', '=', self.id)],
            'context': {'default_call_id': self.id},
        }

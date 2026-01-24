# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class CallQuality(models.Model):
    _name = 'ringcentral.call.quality'
    _description = 'Call Quality Metrics'
    _order = 'measurement_time desc'

    # ===========================
    # Constraints
    # ===========================
    
    @api.constrains('mos_score')
    def _check_mos_score_range(self):
        """Ensure MOS score is in valid range (1.0-5.0)"""
        for record in self:
            if record.mos_score is not None:
                if record.mos_score < 1.0 or record.mos_score > 5.0:
                    raise ValidationError(
                        _("MOS score must be between 1.0 and 5.0.")
                    )
    
    @api.constrains('packet_loss')
    def _check_packet_loss_range(self):
        """Ensure packet loss is a valid percentage (0-100)"""
        for record in self:
            if record.packet_loss is not None:
                if record.packet_loss < 0 or record.packet_loss > 100:
                    raise ValidationError(
                        _("Packet loss must be between 0 and 100 percent.")
                    )
    
    # ===========================
    # Fields
    # ===========================

    call_id = fields.Many2one(
        'ringcentral.call',
        string='Call',
        required=True,
        ondelete='cascade',
        index=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        related='call_id.user_id',
        store=True,
    )
    
    measurement_time = fields.Datetime(
        string='Measurement Time',
        default=fields.Datetime.now,
    )
    
    # Voice Quality - MOS (Mean Opinion Score)
    mos_score = fields.Float(
        string='MOS Score',
        help='Mean Opinion Score (1-5). 4.0+ is excellent.',
    )
    mos_rating = fields.Selection([
        ('excellent', 'Excellent (4.0+)'),
        ('good', 'Good (3.5-4.0)'),
        ('fair', 'Fair (3.0-3.5)'),
        ('poor', 'Poor (2.5-3.0)'),
        ('bad', 'Bad (<2.5)'),
    ], string='Quality Rating', compute='_compute_mos_rating', store=True)
    
    # Network Metrics
    jitter = fields.Float(
        string='Jitter (ms)',
        help='Variation in packet arrival time',
    )
    latency = fields.Float(
        string='Latency (ms)',
        help='Round-trip time for packets',
    )
    packet_loss = fields.Float(
        string='Packet Loss (%)',
        help='Percentage of packets lost',
    )
    
    # Bandwidth
    bitrate = fields.Integer(
        string='Bitrate (kbps)',
        help='Audio bitrate used',
    )
    
    # Codec
    codec = fields.Char(string='Codec')
    
    # Network Type
    network_type = fields.Selection([
        ('wifi', 'WiFi'),
        ('ethernet', 'Ethernet'),
        ('cellular', 'Cellular'),
        ('unknown', 'Unknown'),
    ], string='Network Type', default='unknown')
    
    # Issues
    has_issues = fields.Boolean(
        string='Has Issues',
        compute='_compute_has_issues',
        store=True,
    )
    issue_description = fields.Char(
        string='Issue Description',
        compute='_compute_has_issues',
        store=True,
    )

    @api.depends('mos_score')
    def _compute_mos_rating(self):
        for record in self:
            if record.mos_score >= 4.0:
                record.mos_rating = 'excellent'
            elif record.mos_score >= 3.5:
                record.mos_rating = 'good'
            elif record.mos_score >= 3.0:
                record.mos_rating = 'fair'
            elif record.mos_score >= 2.5:
                record.mos_rating = 'poor'
            else:
                record.mos_rating = 'bad'

    @api.depends('jitter', 'latency', 'packet_loss', 'mos_score')
    def _compute_has_issues(self):
        for record in self:
            issues = []
            
            if record.jitter and record.jitter > 30:
                issues.append('High jitter')
            if record.latency and record.latency > 150:
                issues.append('High latency')
            if record.packet_loss and record.packet_loss > 1:
                issues.append('Packet loss')
            if record.mos_score and record.mos_score < 3.0:
                issues.append('Poor audio quality')
            
            record.has_issues = bool(issues)
            record.issue_description = ', '.join(issues) if issues else ''

    @api.model
    def create(self, vals):
        record = super().create(vals)
        
        # Check for alerts
        record._check_quality_alerts()
        
        return record

    def _check_quality_alerts(self):
        """Check if quality metrics trigger any alerts"""
        self.ensure_one()
        
        AlertRule = self.env['ringcentral.call.quality.alert.rule']
        rules = AlertRule.search([('active', '=', True)])
        
        for rule in rules:
            triggered = False
            
            if rule.metric == 'mos' and self.mos_score:
                if rule.operator == 'less_than' and self.mos_score < rule.threshold:
                    triggered = True
                elif rule.operator == 'greater_than' and self.mos_score > rule.threshold:
                    triggered = True
            
            elif rule.metric == 'jitter' and self.jitter:
                if rule.operator == 'less_than' and self.jitter < rule.threshold:
                    triggered = True
                elif rule.operator == 'greater_than' and self.jitter > rule.threshold:
                    triggered = True
            
            elif rule.metric == 'latency' and self.latency:
                if rule.operator == 'less_than' and self.latency < rule.threshold:
                    triggered = True
                elif rule.operator == 'greater_than' and self.latency > rule.threshold:
                    triggered = True
            
            elif rule.metric == 'packet_loss' and self.packet_loss:
                if rule.operator == 'less_than' and self.packet_loss < rule.threshold:
                    triggered = True
                elif rule.operator == 'greater_than' and self.packet_loss > rule.threshold:
                    triggered = True
            
            if triggered:
                rule._trigger_alert(self)


class CallQualityAlertRule(models.Model):
    _name = 'ringcentral.call.quality.alert.rule'
    _description = 'Call Quality Alert Rule'

    name = fields.Char(string='Rule Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    
    metric = fields.Selection([
        ('mos', 'MOS Score'),
        ('jitter', 'Jitter'),
        ('latency', 'Latency'),
        ('packet_loss', 'Packet Loss'),
    ], string='Metric', required=True)
    
    operator = fields.Selection([
        ('less_than', 'Less Than'),
        ('greater_than', 'Greater Than'),
    ], string='Operator', required=True, default='less_than')
    
    threshold = fields.Float(string='Threshold', required=True)
    
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Severity', default='medium')
    
    notification_user_ids = fields.Many2many(
        'res.users',
        string='Notify Users',
    )

    def _trigger_alert(self, quality_record):
        """Create alert when rule is triggered"""
        self.ensure_one()
        
        self.env['ringcentral.call.quality.alert'].create({
            'rule_id': self.id,
            'quality_id': quality_record.id,
            'call_id': quality_record.call_id.id,
            'severity': self.severity,
        })
        
        # Send notifications
        for user in self.notification_user_ids:
            self.env['bus.bus']._sendone(
                (self._cr.dbname, 'res.partner', user.partner_id.id),
                'ringcentral_quality_alert',
                {
                    'title': f'Call Quality Alert: {self.name}',
                    'message': quality_record.issue_description or 'Quality threshold exceeded',
                    'call_id': quality_record.call_id.id,
                    'severity': self.severity,
                }
            )


class CallQualityAlert(models.Model):
    _name = 'ringcentral.call.quality.alert'
    _description = 'Call Quality Alert'
    _order = 'create_date desc'

    rule_id = fields.Many2one(
        'ringcentral.call.quality.alert.rule',
        string='Alert Rule',
        required=True,
        ondelete='cascade',
    )
    quality_id = fields.Many2one(
        'ringcentral.call.quality',
        string='Quality Record',
        required=True,
        ondelete='cascade',
    )
    call_id = fields.Many2one(
        'ringcentral.call',
        string='Call',
        required=True,
        ondelete='cascade',
    )
    
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Severity')
    
    state = fields.Selection([
        ('new', 'New'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
    ], string='Status', default='new')
    
    acknowledged_by = fields.Many2one('res.users', string='Acknowledged By')
    acknowledged_date = fields.Datetime(string='Acknowledged Date')
    
    resolution_notes = fields.Text(string='Resolution Notes')

    def action_acknowledge(self):
        """Acknowledge alert"""
        self.write({
            'state': 'acknowledged',
            'acknowledged_by': self.env.user.id,
            'acknowledged_date': fields.Datetime.now(),
        })

    def action_resolve(self):
        """Resolve alert"""
        self.state = 'resolved'

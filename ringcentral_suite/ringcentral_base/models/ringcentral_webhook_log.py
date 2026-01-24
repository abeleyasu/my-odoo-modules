# -*- coding: utf-8 -*-
"""
RingCentral Webhook Log Model
=============================

Model for logging and retrying webhook events.
"""

import json
import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class RingCentralWebhookLog(models.Model):
    """Log of RingCentral webhook events for audit and retry"""
    
    _name = 'ringcentral.webhook.log'
    _description = 'RingCentral Webhook Log'
    _order = 'received_at desc'
    _rec_name = 'display_name'
    
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True,
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        index=True,
    )
    
    event_type = fields.Selection([
        ('telephony_session', 'Call'),
        ('sms', 'SMS'),
        ('voicemail', 'Voicemail'),
        ('presence', 'Presence'),
        ('meeting', 'Meeting'),
        ('fax', 'Fax'),
        ('recording', 'Recording'),
        ('message', 'Message'),
        ('unknown', 'Unknown'),
    ], string='Event Type', index=True)

    event_hash = fields.Char(
        string='Event Hash',
        index=True,
        help='SHA-256 hash of the raw webhook body for basic idempotency/deduplication.',
    )

    event_uuid = fields.Char(
        string='Event UUID',
        index=True,
        help='Best-effort unique identifier from the webhook payload (when provided by RingCentral).',
    )
    
    event_data = fields.Text(
        string='Event Data (JSON)',
    )
    
    status = fields.Selection([
        ('received', 'Received'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
        ('pending_retry', 'Pending Retry'),
        ('rejected', 'Rejected'),
        ('error', 'Error'),
    ], string='Status', default='received', index=True)
    
    error_message = fields.Text(
        string='Error Message',
    )
    
    received_at = fields.Datetime(
        string='Received At',
        default=fields.Datetime.now,
        index=True,
    )
    
    processed_at = fields.Datetime(
        string='Processed At',
    )
    
    processing_time = fields.Float(
        string='Processing Time (s)',
    )
    
    retry_count = fields.Integer(
        string='Retry Count',
        default=0,
    )
    
    max_retries = fields.Integer(
        string='Max Retries',
        default=5,
    )
    
    next_retry = fields.Datetime(
        string='Next Retry',
        index=True,
    )

    _sql_constraints = [
        ('ringcentral_webhook_log_event_hash_uniq', 'unique(event_hash)', 'Duplicate webhook event (same hash).'),
        ('ringcentral_webhook_log_company_event_uuid_uniq', 'unique(company_id, event_uuid)', 'Duplicate webhook event (same UUID).'),
    ]
    
    @api.depends('event_type', 'received_at')
    def _compute_display_name(self):
        for log in self:
            event_str = dict(self._fields['event_type'].selection).get(log.event_type, 'Unknown')
            date_str = log.received_at.strftime('%Y-%m-%d %H:%M:%S') if log.received_at else ''
            log.display_name = f"{event_str} - {date_str}"
    
    def action_retry(self):
        """Manually retry a failed webhook event"""
        self.ensure_one()
        
        if self.status not in ('failed', 'pending_retry', 'error'):
            raise UserError(_("Can only retry failed or pending events"))
        
        if self.retry_count >= self.max_retries:
            raise UserError(_("Maximum retry attempts reached"))
        
        try:
            data = json.loads(self.event_data)
            
            # Get the webhook controller and process
            from odoo.addons.ringcentral_base.controllers.webhook import RingCentralWebhookController
            controller = RingCentralWebhookController()
            
            # Process based on event type
            env = self.env
            company = self.company_id
            
            if self.event_type == 'telephony_session':
                controller._handle_telephony_event(env, data, company)
            elif self.event_type == 'sms':
                controller._handle_sms_event(env, data, company)
            elif self.event_type == 'voicemail':
                controller._handle_voicemail_event(env, data, company)
            elif self.event_type == 'presence':
                controller._handle_presence_event(env, data, company)
            elif self.event_type == 'meeting':
                controller._handle_meeting_event(env, data, company)
            elif self.event_type == 'fax':
                controller._handle_fax_event(env, data, company)
            
            self.write({
                'status': 'processed',
                'processed_at': fields.Datetime.now(),
                'error_message': False,
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Retry Successful'),
                    'message': _('Webhook event processed successfully.'),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            self.write({
                'retry_count': self.retry_count + 1,
                'error_message': str(e),
                'status': 'failed' if self.retry_count >= self.max_retries - 1 else 'pending_retry',
                'next_retry': fields.Datetime.now() + timedelta(minutes=5 * (self.retry_count + 1)),
            })
            raise UserError(_("Retry failed: %s") % str(e))
    
    @api.model
    def cron_process_retry_queue(self):
        """Process pending retry events"""
        pending = self.search([
            ('status', '=', 'pending_retry'),
            ('next_retry', '<=', fields.Datetime.now()),
            ('retry_count', '<', 5),
        ], limit=50)
        
        for event in pending:
            try:
                event.action_retry()
            except Exception as e:
                _logger.error("Failed to retry webhook event %s: %s", event.id, str(e))
    
    @api.model
    def cron_cleanup_old_logs(self):
        """Clean up old webhook logs (keep 30 days)"""
        cutoff = fields.Datetime.now() - timedelta(days=30)
        old_logs = self.search([
            ('received_at', '<', cutoff),
            ('status', 'in', ['processed', 'rejected']),
        ])
        old_logs.unlink()
        _logger.info("Cleaned up %d old webhook logs", len(old_logs))

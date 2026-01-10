# -*- coding: utf-8 -*-
"""
RingCentral SMS Model
=====================

Model for SMS/MMS messaging through RingCentral.
"""

import logging
import base64
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class RingCentralSMS(models.Model):
    """RingCentral SMS Message"""
    
    _name = 'ringcentral.sms'
    _description = 'RingCentral SMS'
    _order = 'create_date desc'
    _inherit = ['mail.thread']
    
    # ===========================
    # Basic Fields
    # ===========================
    
    name = fields.Char(
        string='Reference',
        compute='_compute_name',
        store=True
    )
    
    phone_number = fields.Char(
        string='Phone Number',
        required=True,
        index=True
    )
    
    direction = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ], string='Direction', required=True, default='outbound')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('received', 'Received'),
    ], string='Status', default='draft', required=True)
    
    message_type = fields.Selection([
        ('sms', 'SMS'),
        ('mms', 'MMS'),
    ], string='Type', default='sms', required=True)
    
    # ===========================
    # Message Content
    # ===========================
    
    body = fields.Text(
        string='Message',
        required=True
    )
    
    body_preview = fields.Char(
        string='Preview',
        compute='_compute_body_preview'
    )
    
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'ringcentral_sms_attachment_rel',
        'sms_id',
        'attachment_id',
        string='Attachments'
    )
    
    has_attachments = fields.Boolean(
        string='Has Attachments',
        compute='_compute_has_attachments',
        store=True
    )
    
    # ===========================
    # RingCentral Info
    # ===========================
    
    ringcentral_message_id = fields.Char(
        string='RingCentral Message ID',
        index=True,
        readonly=True
    )
    
    from_number = fields.Char(
        string='From Number'
    )
    
    to_number = fields.Char(
        string='To Number'
    )
    
    # ===========================
    # Related Records
    # ===========================
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        index=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
        index=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True
    )
    
    # Polymorphic link
    res_model = fields.Char(
        string='Related Model',
        index=True
    )
    
    res_id = fields.Many2oneReference(
        string='Related Record',
        model_field='res_model',
        index=True
    )
    
    # ===========================
    # Conversation Threading
    # ===========================
    
    conversation_id = fields.Char(
        string='Conversation ID',
        compute='_compute_conversation_id',
        store=True,
        index=True
    )
    
    thread_message_ids = fields.One2many(
        'ringcentral.sms',
        compute='_compute_thread_messages'
    )
    
    # ===========================
    # Timestamps
    # ===========================
    
    sent_time = fields.Datetime(
        string='Sent Time'
    )
    
    delivered_time = fields.Datetime(
        string='Delivered Time'
    )
    
    read_time = fields.Datetime(
        string='Read Time'
    )
    
    # ===========================
    # Error Handling
    # ===========================
    
    error_message = fields.Text(
        string='Error Message'
    )
    
    retry_count = fields.Integer(
        string='Retry Count',
        default=0
    )
    
    # ===========================
    # Computed Fields
    # ===========================
    
    @api.depends('phone_number', 'direction', 'create_date')
    def _compute_name(self):
        for sms in self:
            direction_str = '→' if sms.direction == 'outbound' else '←'
            sms.name = f"SMS {direction_str} {sms.phone_number}"
    
    @api.depends('body')
    def _compute_body_preview(self):
        for sms in self:
            if sms.body:
                sms.body_preview = sms.body[:50] + ('...' if len(sms.body) > 50 else '')
            else:
                sms.body_preview = ''
    
    @api.depends('attachment_ids')
    def _compute_has_attachments(self):
        for sms in self:
            sms.has_attachments = bool(sms.attachment_ids)
    
    @api.depends('phone_number', 'from_number', 'to_number')
    def _compute_conversation_id(self):
        """Generate conversation ID for threading"""
        for sms in self:
            # Normalize numbers for conversation grouping
            numbers = sorted([
                sms.from_number or '',
                sms.to_number or sms.phone_number or ''
            ])
            sms.conversation_id = '_'.join(numbers)
    
    def _compute_thread_messages(self):
        """Get all messages in the same conversation"""
        for sms in self:
            if sms.conversation_id:
                sms.thread_message_ids = self.search([
                    ('conversation_id', '=', sms.conversation_id)
                ])
            else:
                sms.thread_message_ids = sms
    
    # ===========================
    # CRUD Methods
    # ===========================
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto-detect partner
            if not vals.get('partner_id') and vals.get('phone_number'):
                partner = self._find_partner_by_phone(vals['phone_number'])
                if partner:
                    vals['partner_id'] = partner.id
        
        return super().create(vals_list)
    
    @api.model
    def _find_partner_by_phone(self, phone_number):
        """Find partner by phone number"""
        if not phone_number:
            return None
        
        # Clean phone number for search
        clean_number = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        
        # Search in partner phone fields
        partner = self.env['res.partner'].search([
            '|', '|', '|',
            ('phone', 'ilike', clean_number),
            ('mobile', 'ilike', clean_number),
            ('phone', 'ilike', phone_number),
            ('mobile', 'ilike', phone_number),
        ], limit=1)
        
        return partner if partner else None
    
    # ===========================
    # Send SMS
    # ===========================
    
    @api.model
    def action_send_sms(self, phone_number, message, partner_id=None, res_model=None, res_id=None, attachments=None):
        """
        Send an SMS message
        
        :param phone_number: Recipient number
        :param message: Message text
        :param partner_id: Optional partner ID
        :param res_model: Optional related model
        :param res_id: Optional related record ID
        :param attachments: Optional list of attachment IDs
        :return: SMS record
        """
        company = self.env.company
        api = self.env['ringcentral.api']
        
        # Get sender number
        from_number = self.env.user.ringcentral_direct_number or company.ringcentral_default_caller_id
        if not from_number:
            raise UserError(_("No sender phone number configured."))
        
        # Determine message type
        message_type = 'mms' if attachments else 'sms'
        
        # Create SMS record
        sms = self.create({
            'phone_number': phone_number,
            'direction': 'outbound',
            'state': 'sending',
            'message_type': message_type,
            'body': message,
            'from_number': from_number,
            'to_number': phone_number,
            'partner_id': partner_id,
            'res_model': res_model,
            'res_id': res_id,
            'attachment_ids': [(6, 0, attachments)] if attachments else False,
        })
        
        try:
            # Send via API
            if message_type == 'mms' and attachments:
                result = api.send_mms(
                    from_number=from_number,
                    to_number=phone_number,
                    text=message,
                    attachments=sms._prepare_attachments(),
                    company=company
                )
            else:
                result = api.send_sms(
                    from_number=from_number,
                    to_number=phone_number,
                    text=message,
                    company=company
                )
            
            sms.write({
                'state': 'sent',
                'ringcentral_message_id': result.get('id'),
                'sent_time': fields.Datetime.now(),
            })
            
            # Post to related record's chatter
            sms._post_to_chatter()
            
            return {
                'id': sms.id,
                'state': 'sent',
                'message_id': result.get('id'),
            }
            
        except Exception as e:
            sms.write({
                'state': 'failed',
                'error_message': str(e),
            })
            raise UserError(_("Failed to send SMS: %s") % str(e))
    
    def action_retry_send(self):
        """Retry failed SMS"""
        self.ensure_one()
        
        if self.state != 'failed':
            return
        
        if self.retry_count >= 3:
            raise UserError(_("Maximum retry attempts reached."))
        
        self.write({
            'state': 'sending',
            'retry_count': self.retry_count + 1,
            'error_message': False,
        })
        
        return self.action_send_sms(
            phone_number=self.phone_number,
            message=self.body,
            partner_id=self.partner_id.id if self.partner_id else None,
            res_model=self.res_model,
            res_id=self.res_id,
        )
    
    def _prepare_attachments(self):
        """Prepare attachments for MMS"""
        self.ensure_one()
        
        result = []
        for attachment in self.attachment_ids:
            result.append({
                'filename': attachment.name,
                'content': base64.b64decode(attachment.datas),
                'content_type': attachment.mimetype,
            })
        
        return result
    
    def _post_to_chatter(self):
        """Post SMS to related record's chatter"""
        self.ensure_one()
        
        if not self.res_model or not self.res_id:
            if self.partner_id:
                self.res_model = 'res.partner'
                self.res_id = self.partner_id.id
            else:
                return
        
        try:
            record = self.env[self.res_model].browse(self.res_id)
            if hasattr(record, 'message_post'):
                body = f"""
                <p><strong>SMS {'Sent' if self.direction == 'outbound' else 'Received'}</strong></p>
                <p>{self.body}</p>
                <small>{'To' if self.direction == 'outbound' else 'From'}: {self.phone_number}</small>
                """
                record.message_post(
                    body=body,
                    message_type='sms',
                    subtype_xmlid='mail.mt_note',
                )
        except Exception as e:
            _logger.warning("Failed to post SMS to chatter: %s", str(e))
    
    # ===========================
    # Webhook Processing
    # ===========================
    
    @api.model
    def process_sms_event(self, data, company):
        """
        Process SMS webhook event
        
        :param data: Webhook event data
        :param company: Company record
        """
        body = data.get('body', {})
        message_id = body.get('id')
        direction = body.get('direction', '').lower()
        
        # Check for existing message
        existing = self.search([
            ('ringcentral_message_id', '=', message_id)
        ], limit=1)
        
        if existing:
            # Update delivery status
            if body.get('messageStatus') == 'Delivered':
                existing.write({
                    'state': 'delivered',
                    'delivered_time': fields.Datetime.now(),
                })
            return
        
        # New inbound message
        if direction == 'inbound':
            from_number = body.get('from', {}).get('phoneNumber', '')
            to_number = body.get('to', [{}])[0].get('phoneNumber', '') if body.get('to') else ''
            
            # Get message content
            message_text = ''
            attachments = body.get('attachments', [])
            for att in attachments:
                if att.get('type') == 'Text':
                    # Would need to fetch content URL
                    pass
            
            # Try to get from subject/body
            message_text = body.get('subject', '') or body.get('text', '')
            
            # Create inbound SMS record
            sms = self.create({
                'phone_number': from_number,
                'direction': 'inbound',
                'state': 'received',
                'message_type': 'mms' if len(attachments) > 1 else 'sms',
                'body': message_text,
                'ringcentral_message_id': message_id,
                'from_number': from_number,
                'to_number': to_number,
                'company_id': company.id,
            })
            
            # Post to chatter
            sms._post_to_chatter()
            
            # Send bus notification
            self._send_sms_notification(sms)
    
    @classmethod
    def _send_sms_notification(cls, sms):
        """Send notification for received SMS"""
        # Could notify specific user based on phone number routing
        sms.env['bus.bus']._sendone(
            'ringcentral_sms',
            'sms_received',
            {
                'id': sms.id,
                'phone_number': sms.phone_number,
                'body': sms.body_preview,
                'partner_id': sms.partner_id.id if sms.partner_id else None,
                'partner_name': sms.partner_id.name if sms.partner_id else None,
            }
        )
    
    # ===========================
    # Reply Action
    # ===========================
    
    def action_reply(self):
        """Open reply wizard"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reply'),
            'res_model': 'ringcentral.sms.compose',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_phone_number': self.phone_number,
                'default_partner_id': self.partner_id.id if self.partner_id else False,
                'default_res_model': self.res_model,
                'default_res_id': self.res_id,
            },
        }
    
    # ===========================
    # View Conversation
    # ===========================
    
    def action_view_conversation(self):
        """View full conversation thread"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Conversation - %s') % self.phone_number,
            'res_model': 'ringcentral.sms',
            'view_mode': 'tree,form',
            'domain': [('conversation_id', '=', self.conversation_id)],
            'context': {
                'default_phone_number': self.phone_number,
                'default_partner_id': self.partner_id.id if self.partner_id else False,
            },
        }
    
    # ===========================
    # Batch Send and Retry
    # ===========================
    
    @api.model
    def action_batch_send(self, messages):
        """
        Send multiple SMS messages in batch with rate limiting.
        
        :param messages: List of dicts with keys:
            - phone_number: Recipient number
            - message: Message text
            - partner_id: Optional partner ID
        :return: List of results
        """
        import time
        
        results = []
        rate_limit_delay = 0.5  # 500ms between sends to avoid rate limits
        
        for msg in messages:
            try:
                result = self.action_send_sms(
                    phone_number=msg.get('phone_number'),
                    message=msg.get('message'),
                    partner_id=msg.get('partner_id'),
                    res_model=msg.get('res_model'),
                    res_id=msg.get('res_id'),
                )
                results.append({
                    'phone_number': msg.get('phone_number'),
                    'success': True,
                    'sms_id': result.get('id'),
                })
            except Exception as e:
                results.append({
                    'phone_number': msg.get('phone_number'),
                    'success': False,
                    'error': str(e),
                })
            
            # Rate limiting delay
            time.sleep(rate_limit_delay)
        
        return results
    
    def action_retry_send(self):
        """Retry sending failed SMS"""
        for sms in self.filtered(lambda s: s.state == 'failed' and s.direction == 'outbound'):
            sms.retry_count = (sms.retry_count or 0) + 1
            sms.state = 'pending'
            sms.error_message = False
        
        # Process pending SMS
        self._process_pending_sms()
    
    def _process_pending_sms(self):
        """Process pending SMS in queue"""
        import time
        
        pending = self.search([
            ('state', '=', 'pending'),
            ('direction', '=', 'outbound'),
        ], limit=50, order='create_date asc')
        
        api = self.env['ringcentral.api']
        
        for sms in pending:
            company = sms.company_id or self.env.company
            
            try:
                sms.write({'state': 'sending'})
                
                if sms.message_type == 'mms' and sms.attachment_ids:
                    result = api.send_mms(
                        from_number=sms.from_number,
                        to_number=sms.to_number,
                        text=sms.body,
                        attachments=sms._prepare_attachments(),
                        company=company
                    )
                else:
                    result = api.send_sms(
                        from_number=sms.from_number,
                        to_number=sms.to_number,
                        text=sms.body,
                        company=company
                    )
                
                sms.write({
                    'state': 'sent',
                    'ringcentral_message_id': result.get('id'),
                    'sent_time': fields.Datetime.now(),
                    'error_message': False,
                })
                
            except Exception as e:
                sms.write({
                    'state': 'failed',
                    'error_message': str(e),
                })
            
            # Rate limiting
            time.sleep(0.5)
    
    @api.model
    def cron_process_sms_queue(self):
        """Cron job to process pending SMS queue"""
        self._process_pending_sms()
    
    @api.model
    def cron_retry_failed_sms(self):
        """Cron job to retry failed SMS (with backoff)"""
        from datetime import timedelta
        
        # Only retry SMS that are:
        # - Failed
        # - Haven't exceeded max retries
        # - Enough time has passed since last attempt
        max_retries = 3
        retry_delay_minutes = 30
        
        cutoff_time = fields.Datetime.now() - timedelta(minutes=retry_delay_minutes)
        
        failed = self.search([
            ('state', '=', 'failed'),
            ('direction', '=', 'outbound'),
            ('retry_count', '<', max_retries),
            ('write_date', '<', cutoff_time),
        ], limit=20)
        
        for sms in failed:
            sms.action_retry_send()
    
    # Add retry_count field
    retry_count = fields.Integer(string='Retry Count', default=0)

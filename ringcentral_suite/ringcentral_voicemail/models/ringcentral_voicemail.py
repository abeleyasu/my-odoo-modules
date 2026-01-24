# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class RingCentralVoicemail(models.Model):
    _name = 'ringcentral.voicemail'
    _description = 'RingCentral Voicemail'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'received_at desc'

    # RingCentral Info
    ringcentral_message_id = fields.Char(
        string='RingCentral Message ID',
        index=True,
        readonly=True,
    )
    
    # Basic Info
    name = fields.Char(compute='_compute_name', store=True)
    received_at = fields.Datetime(
        string='Received',
        default=fields.Datetime.now,
        index=True,
    )
    
    # Caller Info
    caller_number = fields.Char(string='Caller Number')
    caller_name = fields.Char(string='Caller Name')
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        index=True,
    )
    
    # Recipient
    extension_id = fields.Char(string='Extension ID')
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    
    # Message Details
    duration = fields.Integer(string='Duration (seconds)')
    duration_display = fields.Char(
        compute='_compute_duration_display',
        string='Duration',
    )
    
    # Status
    state = fields.Selection([
        ('new', 'New'),
        ('read', 'Read'),
        ('callback', 'Callback Scheduled'),
        ('archived', 'Archived'),
        ('deleted', 'Deleted'),
    ], string='Status', default='new', tracking=True)
    
    read_at = fields.Datetime(string='Read At')
    
    # Priority
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
    ], string='Priority', default='0')
    is_urgent = fields.Boolean(
        compute='_compute_is_urgent',
        store=True,
    )
    
    # Audio
    audio_content = fields.Binary(
        string='Audio',
        attachment=True,
    )
    audio_filename = fields.Char(string='Audio Filename')
    content_uri = fields.Char(string='Content URI')
    
    # Transcription
    transcription = fields.Text(string='Transcription')
    transcription_state = fields.Selection([
        ('none', 'None'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], string='Transcription Status', default='none')
    
    # Notes
    notes = fields.Text(string='Notes')
    
    # Follow-up
    callback_scheduled = fields.Boolean(string='Callback Scheduled')
    callback_activity_id = fields.Many2one(
        'mail.activity',
        string='Callback Activity',
    )

    @api.depends('caller_name', 'caller_number', 'received_at')
    def _compute_name(self):
        for vm in self:
            caller = vm.caller_name or vm.caller_number or 'Unknown'
            date_str = vm.received_at.strftime('%Y-%m-%d %H:%M') if vm.received_at else ''
            vm.name = f'{caller} - {date_str}'

    @api.depends('duration')
    def _compute_duration_display(self):
        for vm in self:
            if vm.duration:
                minutes, seconds = divmod(vm.duration, 60)
                vm.duration_display = f'{minutes}:{seconds:02d}'
            else:
                vm.duration_display = '0:00'

    @api.depends('priority')
    def _compute_is_urgent(self):
        for vm in self:
            vm.is_urgent = vm.priority == '1'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto-detect partner from phone number
            if vals.get('caller_number') and not vals.get('partner_id'):
                partner = self._find_partner_by_phone(vals['caller_number'])
                if partner:
                    vals['partner_id'] = partner.id
                    if not vals.get('caller_name'):
                        vals['caller_name'] = partner.name
        
        records = super().create(vals_list)
        
        # Notify users of new voicemails
        for record in records:
            record._notify_new_voicemail()
        
        return records

    def _find_partner_by_phone(self, phone):
        """Find partner by phone number"""
        if not phone:
            return self.env['res.partner']
        
        # Clean phone number for search
        clean_number = phone.replace('+', '').replace(' ', '').replace('-', '')
        
        # Search for partner
        return self.env['res.partner'].search([
            '|', '|', '|',
            ('phone', 'ilike', clean_number),
            ('mobile', 'ilike', clean_number),
            ('phone', 'ilike', phone),
            ('mobile', 'ilike', phone),
        ], limit=1)

    def _notify_new_voicemail(self):
        """Send notification for new voicemail"""
        self.ensure_one()
        
        if self.user_id:
            # Bus notification
            self.env['bus.bus']._sendone(
                self.user_id.partner_id,
                'ringcentral_voicemail',
                {
                    'type': 'new_voicemail',
                    'voicemail_id': self.id,
                    'caller': self.caller_name or self.caller_number,
                    'duration': self.duration_display,
                    'transcription': self.transcription[:100] if self.transcription else None,
                }
            )

    def action_mark_read(self):
        """Mark voicemail as read"""
        self.write({
            'state': 'read',
            'read_at': fields.Datetime.now(),
        })
        
        # Update read status in RingCentral
        for vm in self:
            if vm.ringcentral_message_id:
                try:
                    rc_api = self.env['ringcentral.api'].sudo()
                    rc_api.mark_message_read(vm.ringcentral_message_id)
                except Exception as e:
                    _logger.error(f'Failed to mark voicemail read in RC: {e}')

    def action_mark_unread(self):
        """Mark voicemail as unread"""
        self.write({
            'state': 'new',
            'read_at': False,
        })

    def action_play(self):
        """Play voicemail audio"""
        self.ensure_one()
        
        # Mark as read
        if self.state == 'new':
            self.action_mark_read()
        
        if self.audio_content:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/ringcentral.voicemail/{self.id}/audio_content/{self.audio_filename}?download=false',
                'target': 'new',
            }
        elif self.content_uri:
            # Download audio first
            self.action_download_audio()
            if self.audio_content:
                return self.action_play()
        
        raise UserError(_('Audio not available'))

    def action_download_audio(self):
        """Download audio from RingCentral"""
        self.ensure_one()
        
        if not self.content_uri:
            return
        
        try:
            rc_api = self.env['ringcentral.api'].sudo()
            content, content_type = rc_api.download_recording(self.content_uri)
            
            if content:
                self.audio_content = base64.b64encode(content)
                self.audio_filename = f'voicemail_{self.ringcentral_message_id}.mp3'
                
        except Exception as e:
            _logger.error(f'Failed to download voicemail audio: {e}')

    def action_callback(self):
        """Initiate callback to caller using RingCentral Embeddable widget"""
        self.ensure_one()
        
        if not self.caller_number:
            raise UserError(_('No caller number available'))
        
        # Use the RingCentral Embeddable widget for consistent call experience
        return {
            'type': 'ir.actions.client',
            'tag': 'ringcentral_embeddable_call',
            'params': {
                'phone_number': self.caller_number,
                'partner_name': self.caller_name or self.caller_number,
                'res_model': 'ringcentral.voicemail',
                'res_id': self.id,
            },
        }

    def action_schedule_callback(self):
        """Schedule a callback activity"""
        self.ensure_one()
        
        # Create callback activity
        activity = self.env['mail.activity'].create({
            'activity_type_id': self.env.ref('mail.mail_activity_data_call').id,
            'summary': f'Callback: {self.caller_name or self.caller_number}',
            'note': f'Return call for voicemail received {self.received_at}',
            'user_id': self.user_id.id,
            'res_model_id': self.env['ir.model']._get('res.partner').id,
            'res_id': self.partner_id.id if self.partner_id else self.env.user.partner_id.id,
        })
        
        self.write({
            'state': 'callback',
            'callback_scheduled': True,
            'callback_activity_id': activity.id,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Callback scheduled'),
                'type': 'success',
            }
        }

    def action_archive(self):
        """Archive voicemail"""
        self.write({'state': 'archived'})

    def action_delete(self):
        """Delete voicemail"""
        for vm in self:
            # Delete from RingCentral
            if vm.ringcentral_message_id:
                try:
                    rc_api = self.env['ringcentral.api'].sudo()
                    rc_api.delete_message(vm.ringcentral_message_id)
                except Exception as e:
                    _logger.error(f'Failed to delete voicemail from RC: {e}')
            
            vm.state = 'deleted'
            vm.audio_content = False

    def action_transcribe(self):
        """Request transcription"""
        self.ensure_one()
        
        self.transcription_state = 'pending'
        
        try:
            rc_api = self.env['ringcentral.api'].sudo()
            result = rc_api.request_voicemail_transcription(self.ringcentral_message_id)
            
            if result.get('text'):
                self.transcription = result['text']
                self.transcription_state = 'completed'
            
        except Exception as e:
            _logger.error(f'Transcription failed: {e}')
            self.transcription_state = 'failed'

    def action_view_partner(self):
        """Open partner form"""
        self.ensure_one()
        
        if self.partner_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Contact'),
                'res_model': 'res.partner',
                'res_id': self.partner_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def action_create_partner(self):
        """Create partner from caller info"""
        self.ensure_one()
        
        if self.partner_id:
            raise UserError(_('Contact already exists'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Contact'),
            'res_model': 'res.partner',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': self.caller_name or self.caller_number,
                'default_phone': self.caller_number,
            },
        }

    @api.model
    def process_voicemail_webhook(self, data):
        """Process voicemail webhook from RingCentral"""
        message_id = data.get('id')
        
        if not message_id:
            return
        
        existing = self.search([('ringcentral_message_id', '=', message_id)], limit=1)
        
        if existing:
            return existing
        
        # Find user by extension
        extension_id = data.get('to', [{}])[0].get('extensionId')
        user = self.env['res.users'].search([
            ('rc_extension_id', '=', extension_id)
        ], limit=1) if extension_id else self.env.user
        
        # Get caller info
        caller_info = data.get('from', {})
        
        vals = {
            'ringcentral_message_id': message_id,
            'received_at': data.get('creationTime'),
            'caller_number': caller_info.get('phoneNumber'),
            'caller_name': caller_info.get('name'),
            'duration': data.get('vmDuration'),
            'content_uri': data.get('attachments', [{}])[0].get('uri'),
            'extension_id': extension_id,
            'user_id': user.id if user else False,
            'priority': '1' if data.get('priority') == 'High' else '0',
        }
        
        voicemail = self.create(vals)
        
        # Auto-download and transcribe if enabled
        if self.env.company.rc_auto_download_voicemail:
            voicemail.action_download_audio()
        
        if self.env.company.rc_auto_transcribe_voicemail:
            voicemail.action_transcribe()
        
        return voicemail

    @api.model
    def _cron_sync_voicemail(self):
        """Sync voicemail from RingCentral"""
        rc_api = self.env['ringcentral.api'].sudo()
        
        try:
            messages = rc_api.get_voicemail_messages()
            
            for msg in messages:
                msg_id = msg.get('id')
                existing = self.search([('ringcentral_message_id', '=', msg_id)], limit=1)
                
                if not existing:
                    self.process_voicemail_webhook(msg)
                    
        except Exception as e:
            _logger.error(f'Voicemail sync failed: {e}')

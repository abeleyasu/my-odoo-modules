# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import logging
import hashlib
from datetime import timedelta

_logger = logging.getLogger(__name__)


class RingCentralRecording(models.Model):
    _name = 'ringcentral.recording'
    _description = 'RingCentral Call Recording'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'recording_date desc'
    _rec_name = 'display_name'

    # RingCentral Info
    ringcentral_recording_id = fields.Char(
        string='RingCentral Recording ID',
        index=True,
        readonly=True,
    )
    
    # Related Call
    call_id = fields.Many2one(
        'ringcentral.call',
        string='Call',
        ondelete='cascade',
        index=True,
    )
    
    # Recording Details
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True,
    )
    recording_date = fields.Datetime(
        string='Recording Date',
        default=fields.Datetime.now,
        index=True,
    )
    duration = fields.Integer(string='Duration (seconds)')
    duration_display = fields.Char(
        compute='_compute_duration_display',
        string='Duration',
    )
    
    # Recording Type
    recording_type = fields.Selection([
        ('automatic', 'Automatic'),
        ('on_demand', 'On Demand'),
        ('conference', 'Conference'),
    ], string='Type', default='automatic')
    
    # State
    state = fields.Selection([
        ('pending', 'Pending'),
        ('downloading', 'Downloading'),
        ('available', 'Available'),
        ('transcribing', 'Transcribing'),
        ('archived', 'Archived'),
        ('deleted', 'Deleted'),
        ('error', 'Error'),
    ], string='Status', default='pending', tracking=True)
    
    # File Storage
    recording_content = fields.Binary(
        string='Recording File',
        attachment=True,
    )
    recording_filename = fields.Char(string='Filename')
    file_size = fields.Integer(string='File Size (bytes)')
    file_size_display = fields.Char(
        compute='_compute_file_size_display',
    )
    content_type = fields.Char(string='Content Type', default='audio/mpeg')
    
    # Cloud Storage
    ringcentral_content_uri = fields.Char(
        string='RingCentral URI',
        help='URI to download recording from RingCentral',
    )
    download_attempts = fields.Integer(default=0)
    
    # Checksum for integrity
    file_checksum = fields.Char(string='File Checksum (MD5)')
    
    # Transcription
    transcription = fields.Text(string='Transcription')
    transcription_state = fields.Selection([
        ('none', 'None'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], string='Transcription Status', default='none')
    transcription_language = fields.Char(string='Language', default='en-US')
    
    # Parties
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        index=True,
    )
    phone_number = fields.Char(string='Phone Number')
    caller_name = fields.Char(string='Caller Name')
    
    # User/Company
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    
    # Compliance
    consent_status = fields.Selection([
        ('not_required', 'Not Required'),
        ('obtained', 'Obtained'),
        ('declined', 'Declined'),
        ('unknown', 'Unknown'),
    ], string='Consent Status', default='unknown')
    consent_date = fields.Datetime(string='Consent Date')
    consent_notes = fields.Text(string='Consent Notes')
    
    # Legal Hold
    legal_hold = fields.Boolean(
        string='Legal Hold',
        help='Recording is under legal hold and cannot be deleted',
    )
    legal_hold_reason = fields.Text(string='Legal Hold Reason')
    legal_hold_date = fields.Date(string='Legal Hold Date')
    
    # Retention
    retention_policy_id = fields.Many2one(
        'ringcentral.recording.retention',
        string='Retention Policy',
    )
    retention_expiry = fields.Date(
        string='Retention Expiry',
        help='Date when recording can be deleted per retention policy',
    )
    
    # Access Tracking
    access_count = fields.Integer(string='Access Count', default=0)
    last_accessed = fields.Datetime(string='Last Accessed')
    
    # Error handling
    error_message = fields.Text(string='Error Message')

    @api.depends('call_id', 'recording_date', 'partner_id')
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.partner_id:
                parts.append(rec.partner_id.name)
            elif rec.phone_number:
                parts.append(rec.phone_number)
            if rec.recording_date:
                parts.append(rec.recording_date.strftime('%Y-%m-%d %H:%M'))
            rec.display_name = ' - '.join(parts) if parts else f'Recording {rec.id}'

    @api.depends('duration')
    def _compute_duration_display(self):
        for rec in self:
            if rec.duration:
                minutes, seconds = divmod(rec.duration, 60)
                hours, minutes = divmod(minutes, 60)
                if hours:
                    rec.duration_display = f'{hours}:{minutes:02d}:{seconds:02d}'
                else:
                    rec.duration_display = f'{minutes}:{seconds:02d}'
            else:
                rec.duration_display = '0:00'

    @api.depends('file_size')
    def _compute_file_size_display(self):
        for rec in self:
            if rec.file_size:
                if rec.file_size >= 1024 * 1024:
                    rec.file_size_display = f'{rec.file_size / (1024 * 1024):.1f} MB'
                elif rec.file_size >= 1024:
                    rec.file_size_display = f'{rec.file_size / 1024:.1f} KB'
                else:
                    rec.file_size_display = f'{rec.file_size} B'
            else:
                rec.file_size_display = '0 B'

    def action_download_recording(self):
        """Download recording from RingCentral on-demand (does not store in Odoo)."""
        self.ensure_one()

        if not self.ringcentral_content_uri:
            raise UserError(_('No recording URI available'))

        return self.action_download_on_demand()

    def action_download_on_demand(self):
        """Download recording content through Odoo proxy (no persistence)."""
        self.ensure_one()
        if not self.ringcentral_content_uri:
            raise UserError(_('No recording URI available'))

        # Track access
        self.access_count += 1
        self.last_accessed = fields.Datetime.now()

        filename = self.recording_filename or f"recording_{self.ringcentral_recording_id or self.id}.mp3"
        return {
            'type': 'ir.actions.act_url',
            'url': f'/ringcentral/recording/{self.id}/download?filename={filename}',
            'target': 'self',
        }

    def action_play_recording(self):
        """Open recording player"""
        self.ensure_one()
        
        # Track access
        self.access_count += 1
        self.last_accessed = fields.Datetime.now()

        if self.ringcentral_content_uri:
            filename = self.recording_filename or f"recording_{self.ringcentral_recording_id or self.id}.mp3"
            return {
                'type': 'ir.actions.act_url',
                'url': f'/ringcentral/recording/{self.id}/stream?filename={filename}',
                'target': 'new',
            }

        raise UserError(_('Recording not available'))

    def action_download_file(self):
        """Download recording file"""
        self.ensure_one()
        
        self.access_count += 1
        self.last_accessed = fields.Datetime.now()

        if self.ringcentral_content_uri:
            return self.action_download_on_demand()

        raise UserError(_('Recording not available'))

    def action_request_transcription(self):
        """Request transcription from RingCentral AI"""
        self.ensure_one()
        
        if self.transcription_state == 'completed':
            raise UserError(_('Transcription already completed'))
        
        self.transcription_state = 'pending'
        
        # Request transcription (best-effort)
        try:
            rc_api = self.env['ringcentral.api'].sudo()
            result = rc_api.request_transcription(
                self.ringcentral_recording_id,
                content_uri=self.ringcentral_content_uri,
                language=self.transcription_language
            )
            
            if result.get('transcription'):
                self.transcription = result['transcription']
                self.transcription_state = 'completed'
                # Auto-post to chatter when transcription is ready
                self._post_transcription_to_chatter()
            else:
                # Will be updated by cron polling when ready
                self.transcription_state = 'pending'
                if result.get('jobId'):
                    self.message_post(body=_('Transcription job submitted (jobId: %s)') % result.get('jobId'))
                
        except Exception as e:
            _logger.error(f'Transcription request failed: {e}')
            self.transcription_state = 'failed'
            self.error_message = str(e)
    
    def _post_transcription_to_chatter(self):
        """Post transcription to the related record's chatter"""
        self.ensure_one()
        
        if not self.transcription:
            return
        
        # Find the related record through the call
        record = None
        if self.call_id and self.call_id.res_model and self.call_id.res_id:
            try:
                record = self.env[self.call_id.res_model].browse(self.call_id.res_id)
                if not record.exists():
                    record = None
            except Exception:
                record = None
        
        # Fallback to partner
        if not record and self.partner_id:
            record = self.partner_id
        
        if record and hasattr(record, 'message_post'):
            # Truncate long transcriptions for display
            transcription_preview = self.transcription
            if len(transcription_preview) > 2000:
                transcription_preview = transcription_preview[:2000] + "... [truncated]"

            body = (
                "Call transcription\n"
                f"Call: /web#id={self.id}&model=ringcentral.recording&view_type=form\n\n"
                f"{transcription_preview}"
            )

            record.message_post(
                body=body,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            _logger.info(f'Posted transcription to {self.call_id.res_model}/{self.call_id.res_id}')

    def _post_recording_link_to_chatter(self):
        """Post a plain-text link to this recording on the related record's chatter."""
        self.ensure_one()

        record = None
        if self.call_id and self.call_id.res_model and self.call_id.res_id:
            try:
                record = self.env[self.call_id.res_model].browse(self.call_id.res_id)
                if not record.exists():
                    record = None
            except Exception:
                record = None

        if not record and self.partner_id:
            record = self.partner_id

        if not (record and hasattr(record, 'message_post')):
            return

        when = self.recording_date.strftime('%Y-%m-%d %H:%M') if self.recording_date else 'N/A'
        duration = self.duration_display or ''
        link = f"/web#id={self.id}&model=ringcentral.recording&view_type=form"
        body = f"Call recording available\nDate: {when}\nDuration: {duration}\nRecording: {link}"
        record.message_post(body=body, message_type='notification', subtype_xmlid='mail.mt_note')
    
    def action_post_transcription_to_chatter(self):
        """Manually post transcription to chatter"""
        self.ensure_one()
        
        if not self.transcription:
            raise UserError(_('No transcription available'))
        
        self._post_transcription_to_chatter()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Transcription posted to chatter'),
                'type': 'success',
            }
        }

    def action_set_legal_hold(self):
        """Set legal hold on recording"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Set Legal Hold'),
            'res_model': 'ringcentral.recording.legal.hold.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_recording_ids': [(6, 0, [self.id])]},
        }

    def action_release_legal_hold(self):
        """Release legal hold"""
        self.ensure_one()
        
        if not self.env.user.has_group('ringcentral_base.group_ringcentral_compliance'):
            raise UserError(_('Only compliance officers can release legal holds'))
        
        self.legal_hold = False
        self.legal_hold_reason = False
        self.legal_hold_date = False
        
        self.message_post(body=_('Legal hold released by %s') % self.env.user.name)

    def action_archive(self):
        """Archive recording"""
        self.ensure_one()
        
        if self.legal_hold:
            raise UserError(_('Cannot archive recording under legal hold'))
        
        self.state = 'archived'

    def action_delete_recording(self):
        """Delete recording (soft delete)"""
        for rec in self:
            if rec.legal_hold:
                raise UserError(_('Cannot delete recording under legal hold: %s') % rec.display_name)
            
            # Check retention
            if rec.retention_expiry and rec.retention_expiry > fields.Date.today():
                raise UserError(_('Cannot delete recording before retention expiry'))
            
            rec.state = 'deleted'
            rec.recording_content = False  # Clear binary data

    @api.model
    def process_recording_webhook(self, data):
        """Process recording webhook from RingCentral"""
        recording_id = data.get('recordingId')
        
        if not recording_id:
            return
        
        recording = self.search([('ringcentral_recording_id', '=', recording_id)], limit=1)
        
        event_type = data.get('event', '')
        
        if 'RecordingStarted' in event_type:
            if not recording:
                recording = self.create({
                    'ringcentral_recording_id': recording_id,
                    'state': 'pending',
                })
        elif 'RecordingCompleted' in event_type:
            if recording:
                recording.write({
                    'duration': data.get('duration'),
                    'ringcentral_content_uri': data.get('contentUri'),
                    'state': 'available' if data.get('contentUri') else 'pending',
                })
                # Post link when available
                try:
                    recording._post_recording_link_to_chatter()
                except Exception:
                    pass
        elif 'TranscriptionCompleted' in event_type:
            if recording:
                recording.write({
                    'transcription': data.get('transcription', {}).get('text'),
                    'transcription_state': 'completed',
                })
                try:
                    recording._post_transcription_to_chatter()
                except Exception:
                    pass

    @api.model
    def _cron_cleanup_expired_recordings(self):
        """Cron job to clean up expired recordings"""
        today = fields.Date.today()
        
        expired = self.search([
            ('retention_expiry', '<', today),
            ('legal_hold', '=', False),
            ('state', 'not in', ['deleted']),
        ])
        
        for rec in expired:
            try:
                rec.action_delete_recording()
                _logger.info(f'Deleted expired recording: {rec.display_name}')
            except Exception as e:
                _logger.error(f'Failed to delete recording {rec.id}: {e}')

    @api.model
    def _cron_download_pending_recordings(self):
        """Cron job to download pending recordings"""
        pending = self.search([
            ('state', '=', 'pending'),
            ('ringcentral_content_uri', '!=', False),
            ('download_attempts', '<', 3),
        ], limit=50)
        
        for rec in pending:
            try:
                # Keep legacy behavior as a no-op redirect to on-demand
                rec.state = 'available'
            except Exception as e:
                _logger.error(f'Failed to download recording {rec.id}: {e}')

    @api.model
    def _cron_poll_pending_transcriptions(self):
        """Cron job to poll for pending transcriptions."""
        pending = self.search([
            ('transcription_state', '=', 'pending'),
            ('ringcentral_recording_id', '!=', False),
        ], limit=50)

        if not pending:
            return

        rc_api = self.env['ringcentral.api'].sudo()
        for rec in pending:
            try:
                result = rc_api.get_call_transcription(rec.ringcentral_recording_id, company=rec.company_id)
                text = (result or {}).get('text') or (result or {}).get('transcript')
                if not text:
                    continue
                rec.write({'transcription': text, 'transcription_state': 'completed'})
                rec._post_transcription_to_chatter()
            except Exception:
                continue

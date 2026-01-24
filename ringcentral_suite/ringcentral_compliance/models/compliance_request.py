# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import logging
import json

_logger = logging.getLogger(__name__)


class ComplianceRequest(models.Model):
    _name = 'ringcentral.compliance.request'
    _description = 'Data Subject Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        default=lambda self: _('New'),
        readonly=True,
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Data Subject',
        required=True,
        index=True,
    )
    
    # Request Type
    request_type = fields.Selection([
        ('access', 'Data Access Request'),
        ('rectification', 'Data Rectification'),
        ('erasure', 'Right to Erasure'),
        ('portability', 'Data Portability'),
        ('restriction', 'Restrict Processing'),
        ('objection', 'Object to Processing'),
    ], string='Request Type', required=True, tracking=True)
    
    # Regulation
    regulation = fields.Selection([
        ('gdpr', 'GDPR'),
        ('ccpa', 'CCPA'),
        ('hipaa', 'HIPAA'),
        ('other', 'Other'),
    ], string='Regulation', default='gdpr')
    
    # Status
    state = fields.Selection([
        ('new', 'New'),
        ('verified', 'Identity Verified'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('denied', 'Denied'),
    ], string='Status', default='new', tracking=True)
    
    # Dates
    request_date = fields.Datetime(
        string='Request Date',
        default=fields.Datetime.now,
    )
    due_date = fields.Datetime(
        string='Due Date',
        compute='_compute_due_date',
        store=True,
    )
    completed_date = fields.Datetime(string='Completed Date')
    
    # Days remaining
    days_remaining = fields.Integer(
        string='Days Remaining',
        compute='_compute_days_remaining',
    )
    is_overdue = fields.Boolean(
        string='Overdue',
        compute='_compute_days_remaining',
    )
    
    # Processing Details
    assigned_to = fields.Many2one('res.users', string='Assigned To', tracking=True)
    
    # Data Collection
    data_categories = fields.Selection([
        ('all', 'All Data'),
        ('calls', 'Call Records Only'),
        ('sms', 'SMS Records Only'),
        ('recordings', 'Recordings Only'),
        ('selected', 'Selected Categories'),
    ], string='Data Categories', default='all')
    
    include_calls = fields.Boolean(string='Include Calls', default=True)
    include_sms = fields.Boolean(string='Include SMS', default=True)
    include_recordings = fields.Boolean(string='Include Recordings', default=True)
    include_voicemails = fields.Boolean(string='Include Voicemails', default=True)
    
    # Results
    data_export = fields.Binary(string='Exported Data', attachment=True)
    data_export_filename = fields.Char(string='Export Filename')
    deletion_log = fields.Text(string='Deletion Log')
    
    # Notes
    notes = fields.Text(string='Internal Notes')
    denial_reason = fields.Text(string='Denial Reason')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ringcentral.compliance.request') or _('New')
        
        records = super().create(vals_list)
        
        for record in records:
            record._log_audit('request_created', f'{record.request_type} request created')
            record._schedule_activity()
        
        return records

    @api.depends('request_date', 'regulation')
    def _compute_due_date(self):
        for record in self:
            if record.request_date:
                # GDPR: 30 days, CCPA: 45 days
                days = 30 if record.regulation == 'gdpr' else 45
                record.due_date = record.request_date + timedelta(days=days)
            else:
                record.due_date = False

    @api.depends('due_date', 'state')
    def _compute_days_remaining(self):
        now = fields.Datetime.now()
        for record in self:
            if record.due_date and record.state not in ('completed', 'denied'):
                delta = record.due_date - now
                record.days_remaining = delta.days
                record.is_overdue = delta.days < 0
            else:
                record.days_remaining = 0
                record.is_overdue = False

    def _schedule_activity(self):
        """Schedule activity for compliance team"""
        self.ensure_one()
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=f'Process {self.request_type} request: {self.name}',
            note=f'Data subject request from {self.partner_id.name}',
        )

    def action_verify_identity(self):
        """Mark identity as verified"""
        self.ensure_one()
        self.state = 'verified'
        self._log_audit('identity_verified', 'Data subject identity verified')

    def action_process(self):
        """Start processing request"""
        self.ensure_one()
        if self.state != 'verified':
            raise UserError(_('Identity must be verified before processing'))
        
        self.write({
            'state': 'processing',
            'assigned_to': self.env.user.id,
        })
        self._log_audit('processing_started', 'Request processing started')

    def action_execute_access(self):
        """Execute data access request - export data"""
        self.ensure_one()
        
        data = self._collect_partner_data()
        
        # Create JSON export
        import base64
        json_data = json.dumps(data, indent=2, default=str)
        self.data_export = base64.b64encode(json_data.encode())
        self.data_export_filename = f'data_export_{self.partner_id.id}_{fields.Date.today()}.json'
        
        self._log_audit('data_exported', 'Data access request completed - data exported')
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=ringcentral.compliance.request&id={self.id}&field=data_export&filename_field=data_export_filename&download=true',
            'target': 'self',
        }

    def action_execute_erasure(self):
        """Execute right to erasure - delete data"""
        self.ensure_one()
        
        deletion_log = []
        partner = self.partner_id
        
        # Delete calls
        if self.include_calls:
            Call = self.env.get('ringcentral.call')
            if Call:
                calls = Call.sudo().search([('partner_id', '=', partner.id)])
                count = len(calls)
                calls.unlink()
                deletion_log.append(f'Deleted {count} call records')
        
        # Delete SMS
        if self.include_sms:
            SMS = self.env.get('ringcentral.sms')
            if SMS:
                messages = SMS.sudo().search([('partner_id', '=', partner.id)])
                count = len(messages)
                messages.unlink()
                deletion_log.append(f'Deleted {count} SMS records')
        
        # Delete recordings
        if self.include_recordings:
            Recording = self.env.get('ringcentral.recording')
            if Recording:
                recordings = Recording.sudo().search([('partner_id', '=', partner.id)])
                count = len(recordings)
                recordings.unlink()
                deletion_log.append(f'Deleted {count} recordings')
        
        # Delete voicemails
        if self.include_voicemails:
            Voicemail = self.env.get('ringcentral.voicemail')
            if Voicemail:
                voicemails = Voicemail.sudo().search([('partner_id', '=', partner.id)])
                count = len(voicemails)
                voicemails.unlink()
                deletion_log.append(f'Deleted {count} voicemails')
        
        self.deletion_log = '\n'.join(deletion_log)
        self._log_audit('data_deleted', f'Erasure request executed: {", ".join(deletion_log)}')

    def _collect_partner_data(self):
        """
        Collect all partner data for GDPR-compliant export.
        
        Returns a comprehensive data package including:
        - Personal information
        - Communication history
        - Recordings metadata
        - Processing activities
        """
        partner = self.partner_id
        
        data = {
            'metadata': {
                'export_date': str(fields.Datetime.now()),
                'request_reference': self.name,
                'regulation': self.regulation,
                'data_controller': self.env.company.name,
                'data_controller_contact': self.env.company.email or '',
            },
            'data_subject': {
                'id': partner.id,
                'name': partner.name,
                'email': partner.email,
                'phone': partner.phone,
                'mobile': partner.mobile,
                'company': partner.parent_id.name if partner.parent_id else '',
                'title': partner.title.name if partner.title else '',
                'street': partner.street or '',
                'city': partner.city or '',
                'country': partner.country_id.name if partner.country_id else '',
                'creation_date': str(partner.create_date),
            },
        }
        
        # Collect calls
        if self.include_calls:
            Call = self.env.get('ringcentral.call')
            if Call:
                calls = Call.sudo().search([('partner_id', '=', partner.id)])
                data['calls'] = {
                    'total_count': len(calls),
                    'records': [{
                        'date': str(c.start_time) if c.start_time else '',
                        'direction': c.direction,
                        'phone_number': c.phone_number,
                        'duration_seconds': c.duration,
                        'result': c.call_result or c.state,
                        'has_recording': bool(c.recording_id),
                    } for c in calls.sorted('start_time', reverse=True)]
                }
        
        # Collect SMS
        if self.include_sms:
            SMS = self.env.get('ringcentral.sms')
            if SMS:
                messages = SMS.sudo().search([('partner_id', '=', partner.id)])
                data['sms_messages'] = {
                    'total_count': len(messages),
                    'records': [{
                        'date': str(m.message_date) if hasattr(m, 'message_date') and m.message_date else str(m.create_date),
                        'direction': m.direction,
                        'from_number': m.from_number or '',
                        'to_number': m.to_number or '',
                        'body': m.body or '',
                        'status': m.state,
                    } for m in messages.sorted('create_date', reverse=True)]
                }
        
        # Collect recordings (metadata only, not content)
        if self.include_recordings:
            Recording = self.env.get('ringcentral.recording')
            if Recording:
                recordings = Recording.sudo().search([('partner_id', '=', partner.id)])
                data['recordings'] = {
                    'total_count': len(recordings),
                    'note': 'Recording content available upon separate request',
                    'records': [{
                        'date': str(r.recording_date) if hasattr(r, 'recording_date') else str(r.create_date),
                        'duration_seconds': r.duration if hasattr(r, 'duration') else 0,
                        'type': r.recording_type if hasattr(r, 'recording_type') else 'call',
                        'has_transcription': bool(r.transcription) if hasattr(r, 'transcription') else False,
                    } for r in recordings]
                }
        
        # Collect voicemails
        if self.include_voicemails:
            Voicemail = self.env.get('ringcentral.voicemail')
            if Voicemail:
                voicemails = Voicemail.sudo().search([('partner_id', '=', partner.id)])
                data['voicemails'] = {
                    'total_count': len(voicemails),
                    'records': [{
                        'date': str(v.message_date) if hasattr(v, 'message_date') else str(v.create_date),
                        'from_number': v.from_number if hasattr(v, 'from_number') else '',
                        'duration_seconds': v.duration if hasattr(v, 'duration') else 0,
                        'transcription': v.transcription if hasattr(v, 'transcription') else '',
                    } for v in voicemails]
                }
        
        # Collect consents
        Consent = self.env.get('ringcentral.compliance.consent')
        if Consent:
            consents = Consent.sudo().search([('partner_id', '=', partner.id)])
            data['consents'] = [{
                'type': c.consent_type,
                'status': c.state,
                'granted_date': str(c.consent_date) if hasattr(c, 'consent_date') else '',
                'expiry_date': str(c.expiry_date) if hasattr(c, 'expiry_date') and c.expiry_date else '',
            } for c in consents]
        
        # Include processing activities
        data['processing_activities'] = [
            {
                'purpose': 'Customer communication management',
                'legal_basis': 'Legitimate interest / Contract performance',
                'data_categories': ['Communication records', 'Contact information'],
            },
            {
                'purpose': 'Call recording for quality assurance',
                'legal_basis': 'Consent',
                'data_categories': ['Voice recordings', 'Transcriptions'],
            },
        ]
        
        return data
    
    def action_export_csv(self):
        """Export data in CSV format for portability"""
        self.ensure_one()
        import csv
        import io
        import base64
        
        data = self._collect_partner_data()
        
        # Create ZIP with multiple CSV files
        import zipfile
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Export calls
            if 'calls' in data and data['calls'].get('records'):
                calls_buffer = io.StringIO()
                if data['calls']['records']:
                    writer = csv.DictWriter(calls_buffer, fieldnames=data['calls']['records'][0].keys())
                    writer.writeheader()
                    writer.writerows(data['calls']['records'])
                zipf.writestr('calls.csv', calls_buffer.getvalue())
            
            # Export SMS
            if 'sms_messages' in data and data['sms_messages'].get('records'):
                sms_buffer = io.StringIO()
                if data['sms_messages']['records']:
                    writer = csv.DictWriter(sms_buffer, fieldnames=data['sms_messages']['records'][0].keys())
                    writer.writeheader()
                    writer.writerows(data['sms_messages']['records'])
                zipf.writestr('sms_messages.csv', sms_buffer.getvalue())
            
            # Export metadata as JSON
            meta_json = json.dumps(data['metadata'], indent=2)
            zipf.writestr('metadata.json', meta_json)
            
            # Export personal info
            personal_json = json.dumps(data['data_subject'], indent=2)
            zipf.writestr('personal_data.json', personal_json)
        
        zip_buffer.seek(0)
        self.data_export = base64.b64encode(zip_buffer.read())
        self.data_export_filename = f'data_export_{self.partner_id.id}_{fields.Date.today()}.zip'
        
        self._log_audit('data_exported_csv', 'Data portability request completed - CSV/ZIP export')
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=ringcentral.compliance.request&id={self.id}&field=data_export&filename_field=data_export_filename&download=true',
            'target': 'self',
        }

    def action_complete(self):
        """Mark request as completed"""
        self.ensure_one()
        self.write({
            'state': 'completed',
            'completed_date': fields.Datetime.now(),
        })
        self._log_audit('request_completed', 'Compliance request completed')

    def action_deny(self):
        """Deny request"""
        self.ensure_one()
        if not self.denial_reason:
            raise UserError(_('Please provide a denial reason'))
        
        self.state = 'denied'
        self._log_audit('request_denied', f'Request denied: {self.denial_reason}')

    def _log_audit(self, action, description):
        """Create audit log entry"""
        self.env['ringcentral.compliance.audit.log'].sudo().create({
            'action': action,
            'description': description,
            'partner_id': self.partner_id.id,
            'res_model': self._name,
            'res_id': self.id,
        })

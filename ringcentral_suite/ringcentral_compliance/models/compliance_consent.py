# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ComplianceConsent(models.Model):
    _name = 'ringcentral.compliance.consent'
    _description = 'Communication Consent Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        default=lambda self: _('New'),
        readonly=True,
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        required=True,
        index=True,
    )
    
    # Consent Types
    consent_type = fields.Selection([
        ('call', 'Phone Calls'),
        ('sms', 'SMS Messages'),
        ('recording', 'Call Recording'),
        ('marketing_call', 'Marketing Calls'),
        ('marketing_sms', 'Marketing SMS'),
        ('voicemail', 'Voicemail'),
        ('data_processing', 'Data Processing'),
    ], string='Consent Type', required=True, tracking=True)
    
    # Consent Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('granted', 'Granted'),
        ('denied', 'Denied'),
        ('withdrawn', 'Withdrawn'),
        ('expired', 'Expired'),
    ], string='Status', default='pending', tracking=True)
    
    # Consent Details
    consent_date = fields.Datetime(
        string='Consent Date',
        default=fields.Datetime.now,
    )
    expiry_date = fields.Datetime(string='Expiry Date')
    
    consent_method = fields.Selection([
        ('verbal', 'Verbal'),
        ('written', 'Written'),
        ('electronic', 'Electronic'),
        ('opt_in_form', 'Opt-in Form'),
        ('recorded_call', 'Recorded Call'),
    ], string='Consent Method')
    
    # Verification
    verified = fields.Boolean(string='Verified', default=False)
    verified_by = fields.Many2one('res.users', string='Verified By')
    verification_date = fields.Datetime(string='Verification Date')
    
    # Recording Evidence
    recording_id = fields.Many2one(
        'ringcentral.recording',
        string='Consent Recording',
    )
    
    # Legal Basis (GDPR)
    legal_basis = fields.Selection([
        ('consent', 'Explicit Consent'),
        ('contract', 'Contract Performance'),
        ('legal_obligation', 'Legal Obligation'),
        ('vital_interests', 'Vital Interests'),
        ('public_task', 'Public Task'),
        ('legitimate_interests', 'Legitimate Interests'),
    ], string='Legal Basis (GDPR)')
    
    # Additional Info
    notes = fields.Text(string='Notes')
    ip_address = fields.Char(string='IP Address')
    user_agent = fields.Char(string='User Agent')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ringcentral.compliance.consent') or _('New')
        
        records = super().create(vals_list)
        
        # Log consent creation
        for record in records:
            record._log_audit('consent_created', f'Consent record created for {record.consent_type}')
        
        return records

    def action_grant(self):
        """Grant consent"""
        self.ensure_one()
        self.write({
            'state': 'granted',
            'consent_date': fields.Datetime.now(),
        })
        self._log_audit('consent_granted', f'Consent granted for {self.consent_type}')

    def action_deny(self):
        """Deny consent"""
        self.ensure_one()
        self.write({
            'state': 'denied',
        })
        self._log_audit('consent_denied', f'Consent denied for {self.consent_type}')

    def action_withdraw(self):
        """Withdraw consent"""
        self.ensure_one()
        self.write({
            'state': 'withdrawn',
        })
        self._log_audit('consent_withdrawn', f'Consent withdrawn for {self.consent_type}')
        
        # Update partner preferences
        if self.consent_type == 'call':
            self.partner_id.ringcentral_do_not_call = True
        elif self.consent_type == 'sms':
            self.partner_id.ringcentral_do_not_sms = True

    def action_verify(self):
        """Verify consent record"""
        self.ensure_one()
        self.write({
            'verified': True,
            'verified_by': self.env.user.id,
            'verification_date': fields.Datetime.now(),
        })
        self._log_audit('consent_verified', f'Consent verified by {self.env.user.name}')

    def _log_audit(self, action, description):
        """Create audit log entry"""
        self.env['ringcentral.compliance.audit.log'].sudo().create({
            'action': action,
            'description': description,
            'partner_id': self.partner_id.id,
            'res_model': self._name,
            'res_id': self.id,
        })

    @api.model
    def _cron_check_expiry(self):
        """Check and expire consents"""
        expired = self.search([
            ('state', '=', 'granted'),
            ('expiry_date', '!=', False),
            ('expiry_date', '<', fields.Datetime.now()),
        ])
        
        for consent in expired:
            consent.state = 'expired'
            consent._log_audit('consent_expired', f'Consent expired for {consent.consent_type}')

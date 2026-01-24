# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Compliance Status
    ringcentral_compliance_status = fields.Selection([
        ('pending', 'Pending'),
        ('compliant', 'Compliant'),
        ('review_needed', 'Review Needed'),
        ('restricted', 'Restricted'),
    ], string='Compliance Status', default='pending')
    
    # Consent Records
    consent_ids = fields.One2many(
        'ringcentral.compliance.consent',
        'partner_id',
        string='Consent Records',
    )
    consent_count = fields.Integer(
        string='Consents',
        compute='_compute_consent_count',
    )
    
    # Data Requests
    compliance_request_ids = fields.One2many(
        'ringcentral.compliance.request',
        'partner_id',
        string='Compliance Requests',
    )
    compliance_request_count = fields.Integer(
        string='Requests',
        compute='_compute_compliance_request_count',
    )
    
    # Quick consent status
    has_call_consent = fields.Boolean(
        string='Call Consent',
        compute='_compute_consent_status',
    )
    has_sms_consent = fields.Boolean(
        string='SMS Consent',
        compute='_compute_consent_status',
    )
    has_recording_consent = fields.Boolean(
        string='Recording Consent',
        compute='_compute_consent_status',
    )

    @api.depends('consent_ids')
    def _compute_consent_count(self):
        for partner in self:
            partner.consent_count = len(partner.consent_ids)

    @api.depends('compliance_request_ids')
    def _compute_compliance_request_count(self):
        for partner in self:
            partner.compliance_request_count = len(partner.compliance_request_ids)

    @api.depends('consent_ids', 'consent_ids.state', 'consent_ids.consent_type')
    def _compute_consent_status(self):
        for partner in self:
            granted_consents = partner.consent_ids.filtered(lambda c: c.state == 'granted')
            partner.has_call_consent = any(c.consent_type == 'call' for c in granted_consents)
            partner.has_sms_consent = any(c.consent_type == 'sms' for c in granted_consents)
            partner.has_recording_consent = any(c.consent_type == 'recording' for c in granted_consents)

    def action_view_consents(self):
        """Open consent records"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Consents',
            'res_model': 'ringcentral.compliance.consent',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_view_compliance_requests(self):
        """Open compliance requests"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Compliance Requests',
            'res_model': 'ringcentral.compliance.request',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_create_data_access_request(self):
        """Create a new data access request"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Data Access Request',
            'res_model': 'ringcentral.compliance.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_request_type': 'access',
            },
        }

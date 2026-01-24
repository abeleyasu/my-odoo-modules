# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Communication Statistics
    call_count = fields.Integer(
        compute='_compute_communication_stats',
        string='Calls',
    )
    sms_count = fields.Integer(
        compute='_compute_communication_stats',
        string='SMS',
    )
    voicemail_count = fields.Integer(
        compute='_compute_communication_stats',
        string='Voicemails',
    )
    
    # Last Communication
    last_call_date = fields.Datetime(
        compute='_compute_last_communication',
        string='Last Call',
    )
    last_sms_date = fields.Datetime(
        compute='_compute_last_communication',
        string='Last SMS',
    )
    days_since_contact = fields.Integer(
        compute='_compute_days_since_contact',
        string='Days Since Contact',
    )
    
    # Communication Score
    communication_score = fields.Float(
        compute='_compute_communication_score',
        string='Engagement Score',
        help='Score based on communication activity',
    )
    
    # RingCentral Call Relations
    ringcentral_call_ids = fields.One2many(
        'ringcentral.call',
        compute='_compute_ringcentral_records',
        string='Calls',
    )
    ringcentral_sms_ids = fields.One2many(
        'ringcentral.sms',
        compute='_compute_ringcentral_records',
        string='SMS Messages',
    )

    def _compute_communication_stats(self):
        Call = self.env['ringcentral.call']
        SMS = self.env['ringcentral.sms']
        Voicemail = self.env.get('ringcentral.voicemail')
        
        for lead in self:
            domain = lead._get_communication_domain()
            lead.call_count = Call.search_count(domain)
            lead.sms_count = SMS.search_count(domain)
            lead.voicemail_count = Voicemail.search_count(domain) if Voicemail else 0

    def _compute_last_communication(self):
        Call = self.env['ringcentral.call']
        SMS = self.env['ringcentral.sms']
        
        for lead in self:
            domain = lead._get_communication_domain()
            
            last_call = Call.search(domain, order='create_date desc', limit=1)
            lead.last_call_date = last_call.create_date if last_call else False
            
            last_sms = SMS.search(domain, order='create_date desc', limit=1)
            lead.last_sms_date = last_sms.create_date if last_sms else False

    def _compute_days_since_contact(self):
        for lead in self:
            last_date = max(
                filter(None, [lead.last_call_date, lead.last_sms_date]),
                default=None
            )
            if last_date:
                delta = fields.Datetime.now() - last_date
                lead.days_since_contact = delta.days
            else:
                lead.days_since_contact = -1  # Never contacted

    def _compute_communication_score(self):
        """Calculate engagement score based on communication activity"""
        for lead in self:
            score = 0
            
            # Points for calls (more recent = more points)
            if lead.call_count > 0:
                score += min(lead.call_count * 10, 50)  # Max 50 points
            
            # Points for SMS
            if lead.sms_count > 0:
                score += min(lead.sms_count * 5, 25)  # Max 25 points
            
            # Recency bonus
            if lead.days_since_contact >= 0:
                if lead.days_since_contact <= 7:
                    score += 25
                elif lead.days_since_contact <= 30:
                    score += 10
            
            lead.communication_score = min(score, 100)

    def _compute_ringcentral_records(self):
        Call = self.env['ringcentral.call']
        SMS = self.env['ringcentral.sms']
        
        for lead in self:
            domain = lead._get_communication_domain()
            lead.ringcentral_call_ids = Call.search(domain)
            lead.ringcentral_sms_ids = SMS.search(domain)

    def _get_communication_domain(self):
        """Get domain for finding communications related to this lead"""
        self.ensure_one()
        
        domain = []
        
        # Match by partner
        if self.partner_id:
            domain = [('partner_id', '=', self.partner_id.id)]
        # Match by phone number
        elif self.phone or self.mobile:
            phones = list(filter(None, [self.phone, self.mobile]))
            domain = [('phone_number', 'in', phones)]
        else:
            # No matching criteria, return impossible domain
            domain = [('id', '=', 0)]
        
        return domain

    def action_call(self):
        """Quick call action - initiates call and shows control widget"""
        self.ensure_one()
        
        phone = self.phone or self.mobile or (self.partner_id.phone if self.partner_id else False)
        
        if not phone:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No phone number available'),
                    'type': 'warning',
                }
            }
        
        call_model = self.env['ringcentral.call']
        
        try:
            # Return client action to use RingCentral Embeddable widget
            return {
                'type': 'ir.actions.client',
                'tag': 'ringcentral_embeddable_call',
                'params': {
                    'phone_number': phone,
                    'partner_name': self.partner_id.name if self.partner_id else self.contact_name or self.name,
                    'res_model': 'crm.lead',
                    'res_id': self.id,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Call Failed'),
                    'message': str(e),
                    'type': 'danger',
                }
            }

    def action_send_sms(self):
        """Quick SMS action"""
        self.ensure_one()
        
        phone = self.mobile or self.phone or (self.partner_id.mobile if self.partner_id else False)
        
        if not phone:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No mobile number available'),
                    'type': 'warning',
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send SMS'),
            'res_model': 'ringcentral.sms.compose',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_phone_number': phone,
                'default_partner_id': self.partner_id.id if self.partner_id else False,
                'default_res_model': 'crm.lead',
                'default_res_id': self.id,
            },
        }

    def action_schedule_meeting(self):
        """Schedule RingCentral meeting"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Schedule Meeting'),
            'res_model': 'ringcentral.meeting.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': f'Meeting: {self.name}',
                'default_attendee_ids': [(6, 0, [self.partner_id.id])] if self.partner_id else [],
                'default_res_model': 'crm.lead',
                'default_res_id': self.id,
            },
        }

    def action_view_calls(self):
        """View all calls for this lead"""
        self.ensure_one()
        
        domain = self._get_communication_domain()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Calls'),
            'res_model': 'ringcentral.call',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'default_res_model': 'crm.lead',
                'default_res_id': self.id,
            },
        }

    def action_view_sms(self):
        """View all SMS for this lead"""
        self.ensure_one()
        
        domain = self._get_communication_domain()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('SMS Messages'),
            'res_model': 'ringcentral.sms',
            'view_mode': 'tree,form',
            'domain': domain,
        }

    def action_log_call(self):
        """Log a call activity"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Log Call'),
            'res_model': 'mail.activity',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model_id': self.env['ir.model']._get('crm.lead').id,
                'default_res_id': self.id,
                'default_activity_type_id': self.env.ref('mail.mail_activity_data_call').id,
                'default_summary': f'Call with {self.partner_name or self.name}',
            },
        }

    @api.model
    def create_from_incoming_call(self, call_data):
        """Create lead from incoming call if no match found"""
        phone_number = call_data.get('phone_number')
        
        if not phone_number:
            return False
        
        # Check if lead already exists
        existing = self.search([
            '|', '|',
            ('phone', 'ilike', phone_number[-10:]),
            ('mobile', 'ilike', phone_number[-10:]),
            ('partner_id.phone', 'ilike', phone_number[-10:]),
        ], limit=1)
        
        if existing:
            return existing
        
        # Create new lead
        lead_vals = {
            'name': f'Incoming Call: {phone_number}',
            'phone': phone_number,
            'type': 'lead',
            'description': f'Lead created from incoming call on {fields.Datetime.now()}',
        }
        
        return self.create(lead_vals)

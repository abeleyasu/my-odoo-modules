# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import logging

_logger = logging.getLogger(__name__)


class RingCentralFax(models.Model):
    _name = 'ringcentral.fax'
    _description = 'RingCentral Fax'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # RingCentral Info
    ringcentral_message_id = fields.Char(
        string='RingCentral ID',
        index=True,
        readonly=True,
    )
    
    # Basic Info
    name = fields.Char(
        compute='_compute_name',
        store=True,
    )
    direction = fields.Selection([
        ('outbound', 'Sent'),
        ('inbound', 'Received'),
    ], string='Direction', default='outbound', required=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('queued', 'Queued'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('received', 'Received'),
        ('failed', 'Failed'),
    ], string='Status', default='draft', tracking=True)
    
    # Fax Numbers
    fax_number = fields.Char(
        string='Fax Number',
        help='Recipient fax number for outbound, sender for inbound',
    )
    from_number = fields.Char(string='From Number')
    to_number = fields.Char(string='To Number')
    
    # Contact
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        index=True,
    )
    
    # Document
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'ringcentral_fax_attachment_rel',
        'fax_id',
        'attachment_id',
        string='Documents',
    )
    page_count = fields.Integer(string='Page Count')
    
    # Received fax content
    fax_content = fields.Binary(
        string='Fax Document',
        attachment=True,
    )
    fax_filename = fields.Char(string='Filename')
    content_uri = fields.Char(string='Content URI')
    
    # Cover Page
    cover_page_id = fields.Many2one(
        'ringcentral.fax.cover.page',
        string='Cover Page',
    )
    cover_page_text = fields.Text(string='Cover Page Text')
    
    # Timestamps
    sent_time = fields.Datetime(string='Sent Time')
    received_time = fields.Datetime(string='Received Time')
    
    # Resolution
    resolution = fields.Selection([
        ('high', 'High'),
        ('low', 'Low'),
    ], string='Resolution', default='high')
    
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
    
    # Related Record
    res_model = fields.Char(string='Related Model')
    res_id = fields.Integer(string='Related ID')
    
    # Error
    error_message = fields.Text(string='Error Message')
    retry_count = fields.Integer(string='Retry Count', default=0)

    @api.depends('direction', 'partner_id', 'fax_number', 'create_date')
    def _compute_name(self):
        for fax in self:
            direction = 'To' if fax.direction == 'outbound' else 'From'
            recipient = fax.partner_id.name if fax.partner_id else fax.fax_number
            date_str = fax.create_date.strftime('%Y-%m-%d') if fax.create_date else ''
            fax.name = f'Fax {direction} {recipient} - {date_str}'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto-detect partner
            if vals.get('fax_number') and not vals.get('partner_id'):
                partner = self._find_partner_by_fax(vals['fax_number'])
                if partner:
                    vals['partner_id'] = partner.id
        
        return super().create(vals_list)

    def _find_partner_by_fax(self, fax_number):
        """Find partner by fax number"""
        # Clean fax number for matching
        clean_number = ''.join(c for c in fax_number if c.isdigit())[-10:]
        
        return self.env['res.partner'].search([
            '|',
            ('fax', 'ilike', clean_number),
            ('phone', 'ilike', clean_number),
        ], limit=1)

    def action_send_fax(self):
        """Send the fax via RingCentral"""
        self.ensure_one()
        
        if not self.fax_number:
            raise UserError(_('Please provide a fax number'))
        
        if not self.attachment_ids:
            raise UserError(_('Please attach at least one document'))
        
        self.state = 'queued'
        
        try:
            rc_api = self.env['ringcentral.api'].sudo()
            
            # Prepare attachments
            attachments = []
            for att in self.attachment_ids:
                attachments.append({
                    'filename': att.name,
                    'content': base64.b64decode(att.datas),
                    'contentType': att.mimetype,
                })
            
            result = rc_api.send_fax(
                to=self.fax_number,
                attachments=attachments,
                cover_page_text=self.cover_page_text,
                resolution=self.resolution,
            )
            
            self.write({
                'ringcentral_message_id': result.get('id'),
                'state': 'sending',
                'sent_time': fields.Datetime.now(),
                'from_number': result.get('from', {}).get('phoneNumber'),
            })
            
            _logger.info(f'Fax sent: {self.ringcentral_message_id}')
            
        except Exception as e:
            _logger.error(f'Failed to send fax: {e}')
            self.write({
                'state': 'failed',
                'error_message': str(e),
            })
            raise UserError(_('Failed to send fax: %s') % str(e))

    def action_retry_send(self):
        """Retry sending failed fax"""
        self.ensure_one()
        
        if self.state != 'failed':
            return
        
        self.retry_count += 1
        self.error_message = False
        self.action_send_fax()

    def action_download_fax(self):
        """Download received fax content"""
        self.ensure_one()
        
        if not self.content_uri:
            raise UserError(_('No fax content available'))
        
        try:
            rc_api = self.env['ringcentral.api'].sudo()
            content, content_type = rc_api.download_recording(self.content_uri)
            
            if content:
                self.fax_content = base64.b64encode(content)
                self.fax_filename = f'fax_{self.ringcentral_message_id}.pdf'
                
        except Exception as e:
            _logger.error(f'Failed to download fax: {e}')
            raise UserError(_('Failed to download fax: %s') % str(e))

    def action_view_fax(self):
        """View/download the fax document"""
        self.ensure_one()
        
        if self.fax_content:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/ringcentral.fax/{self.id}/fax_content/{self.fax_filename}?download=false',
                'target': 'new',
            }
        elif self.content_uri:
            self.action_download_fax()
            if self.fax_content:
                return self.action_view_fax()
        
        raise UserError(_('Fax document not available'))

    def action_create_partner(self):
        """Create partner from fax sender"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Contact'),
            'res_model': 'res.partner',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_fax': self.fax_number,
            },
        }

    @api.model
    def process_fax_webhook(self, data):
        """Process fax webhook from RingCentral"""
        message_id = data.get('id')
        direction = data.get('direction', 'Outbound').lower()
        
        # Check existing
        existing = self.search([('ringcentral_message_id', '=', message_id)], limit=1)
        
        if existing:
            # Update status
            fax_state = data.get('faxResolution', data.get('messageStatus', 'Queued'))
            state_map = {
                'Queued': 'queued',
                'Sent': 'sent',
                'Delivered': 'delivered',
                'SendingFailed': 'failed',
                'Received': 'received',
            }
            existing.state = state_map.get(fax_state, existing.state)
            
            if 'Failed' in fax_state:
                existing.error_message = data.get('errorCode', 'Unknown error')
            
            return existing
        
        # Create new inbound fax
        if direction == 'inbound':
            from_info = data.get('from', {})
            vals = {
                'ringcentral_message_id': message_id,
                'direction': 'inbound',
                'state': 'received',
                'fax_number': from_info.get('phoneNumber'),
                'from_number': from_info.get('phoneNumber'),
                'to_number': data.get('to', [{}])[0].get('phoneNumber'),
                'page_count': data.get('faxPageCount'),
                'received_time': data.get('creationTime'),
                'content_uri': data.get('attachments', [{}])[0].get('uri'),
            }
            
            fax = self.create(vals)
            
            # Auto-download if enabled
            if self.env.company.rc_auto_download_fax and fax.content_uri:
                fax.action_download_fax()
            
            # Notify user
            fax._notify_new_fax()
            
            return fax

    def _notify_new_fax(self):
        """Notify about new incoming fax"""
        self.ensure_one()
        
        # Post to chatter
        self.message_post(
            body=_('New fax received from %s (%d pages)') % (
                self.fax_number,
                self.page_count or 0
            ),
            message_type='notification',
        )
        
        # Bus notification
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'ringcentral_fax',
            {
                'type': 'new_fax',
                'fax_id': self.id,
                'from': self.fax_number,
                'pages': self.page_count,
            }
        )

    @api.model
    def _cron_sync_fax_status(self):
        """Sync fax status for pending faxes"""
        pending = self.search([
            ('state', 'in', ['queued', 'sending']),
            ('ringcentral_message_id', '!=', False),
        ])
        
        rc_api = self.env['ringcentral.api'].sudo()
        
        for fax in pending:
            try:
                status = rc_api.get_message_status(fax.ringcentral_message_id)
                self.process_fax_webhook(status)
            except Exception as e:
                _logger.error(f'Failed to sync fax status {fax.id}: {e}')


class ResCompany(models.Model):
    _inherit = 'res.company'

    rc_auto_download_fax = fields.Boolean(
        string='Auto Download Fax',
        default=True,
    )

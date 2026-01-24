# -*- coding: utf-8 -*-

from odoo import models, fields


class RingCentralFaxCoverPage(models.Model):
    _name = 'ringcentral.fax.cover.page'
    _description = 'Fax Cover Page Template'
    _order = 'name'

    name = fields.Char(string='Template Name', required=True)
    active = fields.Boolean(default=True)
    
    # Template content
    header = fields.Char(string='Header', default='FAX')
    greeting = fields.Text(
        string='Greeting',
        default='Please find the attached document for your review.',
    )
    footer = fields.Text(
        string='Footer',
        default='This fax and any attachments are confidential.',
    )
    
    # Style
    include_date = fields.Boolean(string='Include Date', default=True)
    include_page_count = fields.Boolean(string='Include Page Count', default=True)
    include_from_info = fields.Boolean(string='Include From Info', default=True)
    
    # Usage count
    use_count = fields.Integer(string='Times Used', default=0)

    def increment_use_count(self):
        """Increment usage counter"""
        self.use_count += 1

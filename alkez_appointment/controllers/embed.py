# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import http
from odoo.http import request


class AppointmentEmbed(http.Controller):
    """Controller for embeddable widgets."""

    @http.route([
        '/appointment/embed/<int:type_id>',
    ], type='http', auth='public', website=True, sitemap=False)
    def embed_widget(self, type_id, **kwargs):
        """Render embeddable appointment widget."""
        appointment_type = request.env['appointment.type'].sudo().browse(type_id)
        
        if not appointment_type.exists():
            return request.not_found()
        
        embed_type = kwargs.get('embed_type', 'inline')
        
        values = {
            'appointment_type': appointment_type,
            'embed_type': embed_type,
            'is_embed': True,
        }
        
        if embed_type == 'inline':
            return request.render('alkez_appointment.embed_inline', values)
        elif embed_type == 'popup':
            return request.render('alkez_appointment.embed_popup', values)
        else:
            return request.render('alkez_appointment.embed_inline', values)

    @http.route([
        '/appointment/embed/script.js',
    ], type='http', auth='public', sitemap=False)
    def embed_script(self, **kwargs):
        """Serve the embed JavaScript file."""
        content = request.env['ir.qweb']._render('alkez_appointment.embed_script_js', {})
        
        return request.make_response(
            content,
            headers=[
                ('Content-Type', 'application/javascript'),
                ('Cache-Control', 'public, max-age=3600'),
            ]
        )

    @http.route([
        '/appointment/embed/style.css',
    ], type='http', auth='public', sitemap=False)
    def embed_style(self, **kwargs):
        """Serve the embed CSS file."""
        content = request.env['ir.qweb']._render('alkez_appointment.embed_style_css', {})
        
        return request.make_response(
            content,
            headers=[
                ('Content-Type', 'text/css'),
                ('Cache-Control', 'public, max-age=3600'),
            ]
        )

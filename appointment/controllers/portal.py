# Copyright 2024 Your Company
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import http
from odoo.http import request

from odoo.addons.portal.controllers import portal


class AppointmentPortal(portal.CustomerPortal):
    """Portal controller for appointment management."""

    def _prepare_home_portal_values(self, counters):
        """Add appointment counter to portal home."""
        values = super()._prepare_home_portal_values(counters)
        
        if 'appointment_count' in counters:
            partner = request.env.user.partner_id
            appointment_count = request.env['appointment.booking'].sudo().search_count([
                ('partner_id', '=', partner.id)
            ])
            values['appointment_count'] = appointment_count
        
        return values

    @http.route([
        '/my/appointments',
        '/my/appointments/page/<int:page>'
    ], type='http', auth='user', website=True)
    def portal_my_appointments(self, page=1, sortby='date', filterby='all', **kwargs):
        """Portal page listing user's appointments."""
        partner = request.env.user.partner_id
        Booking = request.env['appointment.booking'].sudo()
        
        # Sorting options
        searchbar_sortings = {
            'date': {'label': 'Date', 'order': 'start desc'},
            'name': {'label': 'Name', 'order': 'name'},
            'state': {'label': 'Status', 'order': 'state'},
        }
        
        # Filter options
        searchbar_filters = {
            'all': {'label': 'All', 'domain': []},
            'upcoming': {'label': 'Upcoming', 'domain': [('state', '=', 'confirmed'), ('is_upcoming', '=', True)]},
            'past': {'label': 'Past', 'domain': [('state', 'in', ['completed', 'no_show'])]},
            'cancelled': {'label': 'Cancelled', 'domain': [('state', '=', 'cancelled')]},
        }
        
        domain = [('partner_id', '=', partner.id)]
        
        if filterby in searchbar_filters:
            domain += searchbar_filters[filterby]['domain']
        
        sort_order = searchbar_sortings.get(sortby, searchbar_sortings['date'])['order']
        
        # Pagination
        appointment_count = Booking.search_count(domain)
        pager = portal.pager(
            url='/my/appointments',
            url_args={'sortby': sortby, 'filterby': filterby},
            total=appointment_count,
            page=page,
            step=10,
        )
        
        appointments = Booking.search(
            domain,
            order=sort_order,
            limit=10,
            offset=pager['offset']
        )
        
        values = {
            'appointments': appointments,
            'page_name': 'appointments',
            'pager': pager,
            'default_url': '/my/appointments',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
        }
        
        return request.render('appointment.portal_my_appointments', values)

    @http.route([
        '/my/appointments/<int:booking_id>'
    ], type='http', auth='user', website=True)
    def portal_appointment_detail(self, booking_id, **kwargs):
        """Portal page showing appointment details."""
        partner = request.env.user.partner_id
        booking = request.env['appointment.booking'].sudo().search([
            ('id', '=', booking_id),
            ('partner_id', '=', partner.id)
        ], limit=1)
        
        if not booking:
            return request.redirect('/my/appointments')
        
        values = {
            'booking': booking,
            'page_name': 'appointment_detail',
        }
        
        return request.render('appointment.portal_appointment_detail', values)

# -*- coding: utf-8 -*-

from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class RingCentralCall(models.Model):
    _inherit = 'ringcentral.call'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        index=True,
    )


class RingCentralSMS(models.Model):
    _inherit = 'ringcentral.sms'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        index=True,
    )

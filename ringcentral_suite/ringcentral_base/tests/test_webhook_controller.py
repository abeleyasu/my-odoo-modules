# -*- coding: utf-8 -*-

from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralWebhookController(HttpCase):
    def test_01_validation_token_echo_header(self):
        """Webhook validation handshake should echo Validation-Token in response header."""
        token = 'test-validation-token'
        resp = self.url_open(
            '/ringcentral/webhook',
            data=b'{}',
            headers={
                'Content-Type': 'application/json',
                'Validation-Token': token,
            },
            method='POST',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get('Validation-Token'), token)

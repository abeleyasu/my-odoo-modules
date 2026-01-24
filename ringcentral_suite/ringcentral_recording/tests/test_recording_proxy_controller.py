# -*- coding: utf-8 -*-

from unittest.mock import patch

from odoo.tests.common import HttpCase, tagged


class _FakeUpstreamResponse:
    def __init__(self, status_code=200, headers=None, body=b'test-audio'):
        self.status_code = status_code
        self.headers = headers or {'Content-Type': 'audio/mpeg', 'Content-Length': str(len(body))}
        self._body = body

    def iter_content(self, chunk_size=1024 * 256):
        yield self._body

    def close(self):
        return


@tagged('post_install', '-at_install', 'ringcentral')
class TestRingCentralRecordingProxy(HttpCase):
    def test_01_proxy_blocks_disallowed_host(self):
        self.authenticate('admin', 'admin')

        rec = self.env['ringcentral.recording'].create({
            'ringcentral_recording_id': 'rc1',
            'ringcentral_content_uri': 'https://example.com/recording.mp3',
            'state': 'available',
        })

        resp = self.url_open(f'/ringcentral/recording/{rec.id}/stream')
        self.assertEqual(resp.status_code, 404)

    def test_02_proxy_sets_no_store_headers_for_allowed_host(self):
        self.authenticate('admin', 'admin')

        rec = self.env['ringcentral.recording'].create({
            'ringcentral_recording_id': 'rc2',
            'ringcentral_content_uri': 'https://platform.ringcentral.com/restapi/v1.0/account/~/recording/2/content',
            'state': 'available',
        })

        def _fake_requests_get(url, headers=None, stream=True, timeout=60):
            return _FakeUpstreamResponse()

        with patch('requests.get', new=_fake_requests_get), \
             patch('odoo.addons.ringcentral_base.models.ringcentral_api.RingCentralAPI.get_access_token', return_value='token'):
            resp = self.url_open(f'/ringcentral/recording/{rec.id}/stream?filename=x.mp3')

        self.assertEqual(resp.status_code, 200)
        cache_control = resp.headers.get('Cache-Control')
        self.assertTrue(cache_control and 'no-store' in cache_control)
        self.assertEqual(resp.headers.get('X-Content-Type-Options'), 'nosniff')

# -*- coding: utf-8 -*-

import ipaddress
import logging
from urllib.parse import urlparse

from odoo import http
from odoo.http import Response, request
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


ALLOWED_RECORDING_HOST_SUFFIXES = (
    '.ringcentral.com',
    '.ringcentral.eu',
)


class RingCentralRecordingController(http.Controller):
    @http.route('/ringcentral/recording/<int:recording_id>/download', type='http', auth='user')
    def download_recording(self, recording_id, filename=None, **kwargs):
        rec = request.env['ringcentral.recording'].browse(recording_id)
        rec.check_access_rights('read')
        rec.check_access_rule('read')

        if not rec.exists() or not rec.ringcentral_content_uri:
            return request.not_found()

        fname = filename or rec.recording_filename or f"recording_{rec.ringcentral_recording_id or rec.id}.mp3"
        return self._proxy_recording(rec, disposition='attachment', filename=fname)

    @http.route('/ringcentral/recording/<int:recording_id>/stream', type='http', auth='user')
    def stream_recording(self, recording_id, filename=None, **kwargs):
        rec = request.env['ringcentral.recording'].browse(recording_id)
        rec.check_access_rights('read')
        rec.check_access_rule('read')

        if not rec.exists() or not rec.ringcentral_content_uri:
            return request.not_found()

        fname = filename or rec.recording_filename or f"recording_{rec.ringcentral_recording_id or rec.id}.mp3"
        return self._proxy_recording(rec, disposition='inline', filename=fname)

    def _proxy_recording(self, rec, disposition, filename):
        """Stream recording bytes from RingCentral to the browser.

        Supports HTTP Range requests to allow in-browser seeking.
        """
        rc_api = request.env['ringcentral.api'].sudo()

        try:
            import requests
        except Exception:
            raise UserError("requests package required to download recordings")

        # SSRF hardening: allow only RingCentral HTTPS endpoints
        content_uri = rec.ringcentral_content_uri or ''
        parsed = urlparse(content_uri)
        host = (parsed.hostname or '').lower()
        try:
            ipaddress.ip_address(host)
            host_is_ip = True
        except Exception:
            host_is_ip = False

        if (
            parsed.scheme != 'https'
            or not host
            or host_is_ip
            or not (host.endswith(ALLOWED_RECORDING_HOST_SUFFIXES) or host in {s.lstrip('.') for s in ALLOWED_RECORDING_HOST_SUFFIXES})
        ):
            _logger.warning("Blocked recording proxy to disallowed host: %s", content_uri)
            return request.not_found()

        token = rc_api.get_access_token(company=rec.company_id)
        headers = {
            'Authorization': f'Bearer {token}',
        }
        range_header = request.httprequest.headers.get('Range')
        if range_header:
            headers['Range'] = range_header

        upstream = requests.get(content_uri, headers=headers, stream=True, timeout=60)
        if upstream.status_code >= 400:
            _logger.warning(
                "RingCentral recording proxy failed: HTTP %s for recording %s",
                upstream.status_code,
                rec.id,
            )
            return request.not_found()

        def generate():
            try:
                for chunk in upstream.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        yield chunk
            finally:
                try:
                    upstream.close()
                except Exception:
                    pass

        response_headers = [
            ('Content-Type', upstream.headers.get('Content-Type') or 'application/octet-stream'),
            ('Content-Disposition', f'{disposition}; filename="{filename}"'),
            ('Accept-Ranges', 'bytes'),
            ('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0'),
            ('Pragma', 'no-cache'),
            ('Expires', '0'),
            ('X-Content-Type-Options', 'nosniff'),
        ]

        # Preserve Range-related headers when RingCentral returns a partial response
        status = upstream.status_code
        for key in ('Content-Range', 'Content-Length'):
            if upstream.headers.get(key):
                response_headers.append((key, upstream.headers.get(key)))

        return Response(generate(), headers=response_headers, status=status, direct_passthrough=True)

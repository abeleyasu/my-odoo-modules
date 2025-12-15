# O-Meet (Jitsi) — Odoo Module

## 💎 Commercial Module - $200 USD

**License:** OPL-1 (Odoo Proprietary License)  
**Price:** $200.00 USD (one-time payment)  
**Purchase:** Available on Odoo App Store

This is a **paid module** that requires a valid license to use. Purchase includes lifetime license, updates, and support.

## Overview

This module provides an O-Meet (Google Meet-like) experience inside Odoo using Jitsi Meet as the video backend. It includes calendar integration, JWT support for moderator authentication, and an embedded client via the Jitsi External API.

This README documents the architecture, Odoo configuration keys, Jitsi/Prosody requirements and common troubleshooting steps (what was fixed during setup).

**Module path**: `/opt/odoo/custom_addons/jitsi_meet_ui`

**Module version**: v1.1.0

**Purpose**
- Create and join Jitsi meetings from Odoo (dashboard, instant meetings, calendar links).
- Generate JWT tokens for authenticated moderators (meeting owners) so the self-hosted Jitsi accepts moderator privileges.

**High-level architecture**
- Odoo: serves the website pages and generates JWT tokens when appropriate. Controller: `controllers/main.py`. Meeting model: `models/jitsi_meeting.py`.
- Jitsi (self-hosted): Prosody (XMPP/auth), Jicofo (conference focus), Jitsi Videobridge (media). Domain: `meet.workspace.mysourcedigitalmarketing.com` in the deployed example.
- Nginx (reverse proxy): serves `external_api.js` and proxies WebSocket/BOSH endpoints for Prosody.

Key components and roles
- `prosody` — XMPP server. Configured with `authentication = "token"` on the Jitsi VirtualHost and `token_verification` on MUC component for JWT validation.
- `jicofo` — conference focus process. Must authenticate with Prosody (focus user) and be able to reach the videobridge.
- `jvb` (Jitsi Videobridge) — media router.

Odoo configuration parameters (set via `ir.config_parameter`)
- `jitsi.server.url` — full URL of the Jitsi web endpoint, e.g. `https://meet.workspace.mysourcedigitalmarketing.com` (used to load `external_api.js`).
- `jitsi.server.domain` — the Jitsi XMPP domain (Prosody `VirtualHost`), e.g. `meet.workspace.mysourcedigitalmarketing.com` (used as `sub` claim in JWT)
- `jitsi.jwt.app_id` — JWT `iss` / `aud` value configured in Prosody (app id)
- `jitsi.jwt.app_secret` — JWT secret used to sign HS256 tokens

Where the module uses these: controller `join_meeting` handles `jitsi.server.url`, token generation in `models/jitsi_meeting.py` uses `jitsi.server.domain` for the `sub` claim and `jitsi.jwt.*` for signing.

Jitsi / Prosody configuration notes (important items applied during deployment)
- Prosody must have the `websocket` and (recommended) `smacks` modules enabled for the client to use WebSocket and stream management. If not advertised, the client will fail connecting.
- The `token_verification` (Jitsi Prosody plugin) must be available (this plugin relies on Lua modules such as `inspect.lua`) and Prosody must be able to `require 'inspect'`. On some distros you may need to copy `inspect.lua` to the Lua 5.4 path or into Prosody's custom plugin paths.
- Ensure `app_id` and `app_secret` in Prosody match Odoo's `jitsi.jwt.app_id` and `jitsi.jwt.app_secret`.
- For deployments that want anonymous participants plus authenticated moderators:
  - Use `authentication = "token"` for the VirtualHost (Prosody) and set `allow_empty_token = true` so guests can join without tokens while authenticated users / tokens can be validated for moderator roles.
  - If you want EVERY participant to require tokens, set `allow_empty_token = false` and ensure Odoo generates tokens for everyone.
- Jicofo configuration must not include protocol prefixes in domain fields (`login-url` should be domain only, not `XMPP:domain`). Make sure the `focus` user is registered in Prosody and configured in `jicofo.conf`.
- Ensure JVB and Jicofo are configured with correct XMPP client credentials (username/password registered in Prosody) and `muc_jids`/`brewery` are set.

Reverse proxy / client notes
- The web client loads `external_api.js` from the configured `jitsi.server.url`. The module's template injects this dynamically; ensure `jitsi.server.url` is correct.
- The client will use `wss://<jitsi-host>/xmpp-websocket` or BOSH `https://<jitsi-host>/http-bind` based on `meet.<domain>-config.js`. Make sure your nginx or web server proxies /xmpp-websocket and /http-bind to Prosody.

Common issues and the fixes performed while deploying
- Prosody couldn't find `inspect` Lua module (error loading `token_verification`): fixed by copying `inspect.lua` into Lua 5.4 path or Prosody custom plugins path.
- Config key typos in Odoo controller vs database: `jitsi.server.url` vs `jitsi.server_url` and `jitsi.server.domain` vs `jitsi.server_domain` — the module expects the dotted keys in DB; check parameter names carefully.
- `external_api.js` loaded from wrong host (hardcoded `meet.jit.si`) — template updated to load dynamically from `jitsi_server` passed by controller.
- Prosody `allow_empty_token` set to `false` while module only generated tokens for moderators — either set `allow_empty_token = true` or generate tokens for all participants.
- Jicofo failed to start because `login-url` had an invalid prefix (`XMPP:`). Use domain-only values in `jicofo.conf`.
- Ensure focus/jvb users are registered in Prosody and passwords match the Jicofo / JVB config files.

Troubleshooting checklist (what to inspect when users see "disconnected")
1. Confirm `external_api.js` returns 200 from `https://<jitsi-host>/external_api.js`.
2. Open browser console: check the WebSocket URL used (should be `wss://<jitsi-host>/xmpp-websocket`); attempt a curl to `https://<jitsi-host>/xmpp-websocket` — Prosody displays the test page if reachable.
3. Tail Prosody logs: `sudo journalctl -u prosody -f` and watch for `No stream features to proceed with` or `inspect` module errors.
4. Tail Jicofo logs: `/var/log/jitsi/jicofo.log` — if Jicofo cannot connect to XMPP the client cannot establish conferences.
5. Tail JVB logs: `/var/log/jitsi/jvb.log` — confirm it authenticated and joined the brewery MUC.
6. Verify Odoo view rendering: the `jitsi-meet-container` should include `data-jitsi-server` set to your host and `data-jwt-token` when tokens are generated.

Useful commands (on server)
```
# Check external_api
curl -I https://meet.workspace.mysourcedigitalmarketing.com/external_api.js

# Prosody logs
sudo journalctl -u prosody -f

# Jicofo logs
sudo tail -f /var/log/jitsi/jicofo.log

# JVB logs
sudo tail -f /var/log/jitsi/jvb.log

# Restart services
sudo systemctl restart prosody jicofo jitsi-videobridge2

# Register focus/jvb users (example)
sudo prosodyctl register focus auth.meet.workspace.mysourcedigitalmarketing.com <password>
sudo prosodyctl register jvb auth.meet.workspace.mysourcedigitalmarketing.com <password>
```

Testing steps
1. Create an instant meeting from O-Meet dashboard.
2. Open the join link in a private browser window (guest) — should connect without token (if `allow_empty_token = true`).
3. Log in as the meeting owner and open the same link — owner should receive moderator privileges via JWT.
4. If disconnected, capture timestamps and room name, then review Prosody/Jicofo logs around that time.

Security notes
- Keep `jitsi.jwt.app_secret` confidential. Rotate if leaked.
- If allowing anonymous users, be aware of potential abuse; use lobby, recording/streaming restrictions, or other moderation tools.

Where to look in this module
- Controllers: `controllers/main.py` — join logic and data passed to template.
- Models: `models/jitsi_meeting.py` — meeting model and `generate_jwt_token` implementation.
- Templates: `views/templates.xml` — the client embed, dynamic script loading, data attributes.
- Calendar integration: `models/calendar_event.py` and `views/calendar_views.xml` (if present).

If you want, I can also add a short `UPGRADE.md` with specific commands we ran on this server (inspect.lua copy, prosody/jicofo/jvb registration, config snippets). Tell me if you want that included here.

---
File created: `jitsi_meet_ui/README.md` — please review and tell me if you want more detail added (e.g., full config snippets, commands to reproduce, or screenshots).
# Jitsi Meet UI for Odoo

This module provides a Google Meet-like interface inside Odoo using Jitsi as the meeting backend.

Features
- Simple Meetings dashboard (list/kanban/form)
- Create meetings with a room name (random by default)
- Join meetings using an embedded Jitsi iframe (or external Jitsi server)
- Clean uninstall hook that removes created meetings

Configuration
- Optional system parameter `jitsi.server_url` (e.g. `https://meet.jit.si` or your self-hosted Jitsi server)

Installation
1. Place `jitsi_meet_ui` in your `addons_path` (e.g. `/opt/odoo/custom_addons/`).
2. Update apps list and install the module from Apps or run as `odoo` user:
```
sudo -u odoo python3 /opt/odoo/odoo-18/odoo-bin -d <your_db> -u jitsi_meet_ui --stop-after-init
```

Uninstall
- Uninstalling via Apps will trigger the `uninstall_hook` which removes `jitsi.meeting` records created by this module.

Notes
- This module assumes a Jitsi integration is available or will use `https://meet.jit.si` by default.
- The UI is intentionally lightweight and built with OWL components. You can expand with calendar integration, recurring meetings, or recording support later.

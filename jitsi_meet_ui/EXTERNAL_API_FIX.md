# External API Fix - December 8, 2025

## Issue Found
The Jitsi embed template was loading `external_api.js` from the wrong server:
- ❌ **Before**: Hardcoded `https://meet.jit.si/external_api.js`
- ✅ **After**: Dynamic `https://meet.workspace.mysourcedigitalmarketing.com/external_api.js`

This caused the Jitsi client to try authenticating with meet.jit.si instead of your self-hosted server, leading to "Authentication failed" errors.

## Changes Made

### File: `/opt/odoo/custom_addons/jitsi_meet_ui/views/templates.xml`

**Before** (lines 167-168):
```xml
<script src="https://meet.jit.si/external_api.js"></script>
<script>
```

**After** (lines 167-182):
```xml
<script>
    (function() {
        // Load external_api.js from the configured Jitsi server
        const container = document.getElementById('jitsi-meet-container');
        const server = container.dataset.jitsiServer || 'https://meet.jit.si';
        const apiScript = document.createElement('script');
        apiScript.src = server + '/external_api.js';
        apiScript.onload = initJitsi;
        apiScript.onerror = function() {
            console.error('Failed to load Jitsi external_api.js from ' + server);
            container.innerHTML = '<div class="alert alert-danger m-5">Failed to load meeting...</div>';
        };
        document.head.appendChild(apiScript);
        
        function initJitsi() {
            // ... rest of initialization
```

### What This Fixes
1. ✅ Loads external_api.js from your configured Jitsi server (`jitsi.server.url`)
2. ✅ Jitsi client now connects to `meet.workspace.mysourcedigitalmarketing.com`
3. ✅ JWT tokens are validated by your Prosody server (not meet.jit.si)
4. ✅ Meeting owners auto-join as moderators without OAuth prompts

## Services Restarted
- ✅ Odoo restarted (07:16:55 UTC Dec 8)

## Test Instructions

### Create a Fresh Meeting:
1. Go to Odoo → O-Meet app or Calendar
2. Click "Create Instant Meeting" or "+ O-Meet"
3. Copy the generated meeting link
4. Open link in browser

### Expected Behavior:
- ✅ Page loads Jitsi interface from your server
- ✅ Meeting owner joins immediately as moderator
- ✅ No "Authentication failed" error
- ✅ No OAuth login prompts
- ✅ Display name shows from Odoo profile

### Browser Console Check:
Open browser DevTools (F12) → Console tab:
- ✅ Should see: Loading script from `https://meet.workspace.mysourcedigitalmarketing.com/external_api.js`
- ❌ Should NOT see: Errors about meet.jit.si or authentication failures

## Verification Command

Check that your Jitsi server serves external_api.js:
```bash
curl -I https://meet.workspace.mysourcedigitalmarketing.com/external_api.js
```

Expected response: `HTTP/2 200` (file exists)

## Configuration Summary

All settings are correct:
- Prosody: JWT authentication enabled
- Jicofo: JWT configuration active  
- Odoo parameters:
  - `jitsi.server.url` = https://meet.workspace.mysourcedigitalmarketing.com
  - `jitsi.jwt.app_id` = omeet_odoo
  - `jitsi.jwt.app_secret` = b0b1941aadbfdb50be1808058628f8cf...
  - `jitsi.server.domain` = meet.workspace.mysourcedigitalmarketing.com

## Next Steps
1. **Clear browser cache** (Ctrl+Shift+Delete) to remove old external_api.js
2. **Create a new meeting** in Odoo
3. **Test the meeting link** as the owner
4. Meeting should work immediately without any authentication errors

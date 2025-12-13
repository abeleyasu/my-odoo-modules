# O-Meet v1.1.0 - Major Update

## 🎉 What's New

### ✅ **Automatic Moderator Login (JWT Authentication)**
**Problem Solved**: No more Google/GitHub OAuth redirects!

- Meeting **creators automatically join as moderators** without external login
- Uses JWT token authentication (when configured)
- Seamless instant meeting creation and join

**How it works**:
1. When you create a meeting in Odoo, you're marked as the owner
2. When you click the meeting link, Odoo generates a JWT token
3. The token tells Jitsi you're the moderator
4. You join immediately - no OAuth prompt!

### ✅ **User Name Auto-Fill**
- Your **Odoo profile name** automatically appears in Jitsi
- No manual name entry needed
- Professional appearance for all participants

### ✅ **Calendar Integration**
**Create O-Meet links directly in Calendar events!**

- Open any Calendar event
- Click "+ O-Meet" button (next to "+ Odoo meeting")
- Meeting link generated automatically
- All attendees get the link in event details
- Meeting syncs with calendar date/time

**Features**:
- Auto-creates scheduled Jitsi meeting when you select O-Meet
- Meeting updates when you change calendar event
- Clean uninstall (removes extension when module uninstalled)

### ✅ **Settings UI**
Configure O-Meet from Odoo Settings:
- Go to **Settings → General Settings → O-Meet**
- Set custom Jitsi server URL
- Configure JWT authentication (app ID, secret, domain)

## 🔧 Technical Changes

### New Models
- `calendar.event` extension: adds `videocall_source='jitsi'` option
- `jitsi_meeting.jitsi_meeting_id` link field in calendar events
- `res.config.settings` extension for O-Meet configuration

### New Methods
- `generate_jwt_token(user_name, user_email, is_moderator)`: Creates JWT for moderator auth
- `action_create_jitsi_meeting()`: Calendar event → Jitsi meeting creation

### Controller Updates
- `/o-meet/join/<room>`: Now passes `user_name`, `user_email`, `jwt_token`, `is_moderator`
- Checks if current user is meeting owner (auto-moderator)
- Generates JWT token for owners

### Template Updates
- `jitsi_room_template`: 
  - Passes `userInfo` to Jitsi API
  - Includes JWT token in options (if available)
  - Sets `prejoinPageEnabled: false` for faster join
  - Auto-executes `displayName` and `email` commands

### Dependencies
- Added `PyJWT` library for token generation
- Added `calendar` module dependency

## 📋 Configuration Guide

### Option 1: Public meet.jit.si (Current Setup)
**Status**: Already working! User names display correctly.

**Limitation**: Creators see OAuth login prompt (Google/GitHub) because meet.jit.si requires moderator authentication.

**Workaround**: 
- Meeting creator opens link first and logs in via Google/GitHub
- Once creator joins, other participants can join freely
- OR: Generate a new meeting link each time (fresh rooms don't require moderator)

### Option 2: JWT Authentication (Recommended)
**For**: Instant moderator access without OAuth redirects

**Requirements**:
1. Self-hosted Jitsi server with JWT enabled, OR
2. 8x8.vc Jitsi as a Service account with JWT app ID/secret

**Setup Steps**:

#### A) If you self-host Jitsi:
1. Enable JWT auth in Prosody:
```bash
# Edit /etc/prosody/conf.d/meet.yourdomain.com.cfg.lua
VirtualHost "meet.yourdomain.com"
    authentication = "token"
    app_id = "your_app_id"
    app_secret = "your_secret_key"
    allow_empty_token = false
```

2. Configure Jicofo:
```bash
# Edit /etc/jitsi/jicofo/sip-communicator.properties
org.jitsi.jicofo.auth.URL=XMPP:meet.yourdomain.com
```

3. Restart services:
```bash
systemctl restart prosody jicofo jitsi-videobridge2
```

4. Configure in Odoo:
- Go to **Settings → General Settings → O-Meet**
- **Jitsi Server URL**: `https://meet.yourdomain.com`
- **JWT App ID**: `your_app_id`
- **JWT App Secret**: `your_secret_key`
- **Server Domain**: `meet.yourdomain.com`
- Save

#### B) If using meet.jit.si or 8x8.vc:
- Request JWT credentials from 8x8 support
- Enter credentials in Settings → O-Meet
- Server Domain: `8x8.vc` or provided domain

### Option 3: Anonymous Rooms (Easiest for self-hosted)
**For**: Everyone joins immediately, no moderator auth

**Setup** (self-hosted only):
```bash
# Edit /etc/prosody/conf.d/meet.yourdomain.com.cfg.lua
VirtualHost "meet.yourdomain.com"
    authentication = "anonymous"
    modules_enabled = {
        "bosh";
        "pubsub";
    }
```

```bash
systemctl restart prosody
```

No Odoo configuration needed - meetings open to all immediately!

## 🚀 Usage Examples

### Create Instant Meeting with Auto-Moderator
1. Go to **O-Meet → Dashboard**
2. Click **"New Meeting"**
3. Meeting opens - you're automatically moderator (if JWT configured)
4. Share URL with participants

### Create Calendar Event with O-Meet
1. Go to **Calendar**
2. Create new event
3. Click **"+ O-Meet"** button
4. Meeting link appears in "Videocall URL" field
5. Invite attendees - they get the link

### Join as Participant
1. Receive meeting URL from organizer
2. Click link
3. Your name auto-fills from Odoo profile (if logged in)
4. Join immediately (no signup needed)

## 🔍 Troubleshooting

### "Conference has not yet started" message
**Cause**: meet.jit.si requires moderator authentication for some rooms.

**Solutions**:
- **Option A**: Meeting creator opens link first, authenticates via Google/GitHub
- **Option B**: Configure JWT authentication (see Configuration Guide)
- **Option C**: Use a self-hosted Jitsi with anonymous rooms

### Name not displaying
**Cause**: User not logged into Odoo when joining.

**Solution**: Join meeting link while logged into Odoo, or enter name manually in Jitsi.

### JWT not working
**Check**:
1. App ID/Secret correct in Settings?
2. Jitsi server has JWT auth enabled?
3. Server Domain matches Jitsi server?
4. Meeting owner (creator) is the one joining?

**Debug**: Check browser console for JWT errors.

### Calendar button not showing
**Check**:
1. Calendar module installed?
2. O-Meet module upgraded to v1.1.0?
3. Browser cache cleared?

## 🎯 Best Practices

### For Meeting Creators
- Configure JWT if you create frequent meetings
- Use Calendar integration for scheduled meetings
- Share meeting links via email/chat before meeting starts

### For Administrators
- Set up self-hosted Jitsi for better control
- Configure JWT for seamless moderator experience
- Enable anonymous rooms if you trust all participants

### For Participants
- Log into Odoo before joining for auto-name fill
- No Odoo account needed - anyone with link can join
- Works on mobile and desktop browsers

## 📈 Version History
- **v1.0.0**: Initial release with basic Jitsi integration
- **v1.0.1**: Google Meet-style UI, instant/scheduled meetings
- **v1.1.0**: JWT auth, user name auto-fill, Calendar integration

## 🔮 Coming Soon
- Meeting recordings storage
- Lobby/waiting room controls
- Breakout rooms
- Meeting analytics
- Outlook/Google Calendar sync

---

**Enjoy seamless video conferencing with O-Meet!** 🎥

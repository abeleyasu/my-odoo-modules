# O-Meet: Google Meet-Style Video Conferencing

## 🎯 What's New in v1.0.1

### ✅ Google Meet-Style Dashboard
- Beautiful landing page at `/o-meet/dashboard`
- "New Meeting" button creates instant meetings
- Enter meeting code to join existing meetings
- View your recent meetings with one-click join

### ✅ Instant Meetings
- Click "New Meeting" → Opens immediately
- Auto-generated unique URLs like `https://domain.com/o-meet/join/meet-abc123def4`
- No scheduling needed
- Perfect for quick calls

### ✅ Scheduled Meetings  
- Plan meetings for later
- Set date, time, and duration
- Generate shareable link before the meeting
- Invite attendees from Odoo users

### ✅ Public Join Links
**Anyone with the link can join - no Odoo login required!**
- Share meeting links via email, chat, SMS
- Participants click link → Join directly
- No account creation needed

### ✅ Meeting Management
- **States**: Draft → Ready → Started → Ended
- **Types**: Instant vs Scheduled (with badges)
- **Views**: Kanban, List, Form with rich details
- **Actions**: Join Meeting, Copy Link buttons everywhere

## 🚀 Quick Start

### Create Instant Meeting
```
1. Go to O-Meet → Dashboard
2. Click "New Meeting"
3. Meeting opens in new tab
4. Share the URL with participants
```

### Create Scheduled Meeting
```
1. Go to O-Meet → My Meetings → Create
2. Set Meeting Type: "Scheduled"
3. Choose date/time and duration
4. Save and copy the meeting URL
5. Share with attendees
```

### Join a Meeting
```
Option 1: Dashboard → Enter code → Join
Option 2: My Meetings → Click "Join" button  
Option 3: Open shared meeting URL directly
```

## 📋 Meeting URL Format
`https://yourdomain.com/o-meet/join/meet-[10-char-code]`

Example: `https://mysource.com/o-meet/join/meet-a1b2c3d4e5`

## 🔧 Technical Features

### Backend
- Model: `jitsi.meeting` with mail.thread integration
- Public routes: `/o-meet/join/<room>` (no auth required)
- User routes: `/o-meet/dashboard`, `/o-meet/instant`
- Computed fields: `meeting_url`, `join_url`, `state`

### Frontend
- Google Meet-inspired UI with gradient backgrounds
- Responsive cards with hover effects
- One-click copy-to-clipboard for meeting links
- Real-time meeting status indicators

### Security
- Meeting creation: Authenticated users only
- Meeting joining: Public access (anyone with link)
- Jitsi server: Configurable via system parameter `jitsi.server_url`

## 🎨 UI Elements

### Dashboard
- Hero section: "Video calls and meetings for everyone"
- Primary action button: "New meeting" (Google Blue #1a73e8)
- Meeting code input with "Join" button
- Recent meetings grid with action buttons

### Meeting Cards
- Badge indicators for type (Instant/Scheduled) and state
- Quick action buttons: Join + Copy Link
- Display organizer with avatar
- Show meeting date/time

### Form View
- Status bar with workflow states
- Meeting URL prominently displayed
- Info alert box with shareable link
- Chatter integration for notes

## 🔄 Workflow

```
Draft → Ready → Started → Ended
  ↓       ↓        ↓         ↓
Create  Share   Join    Complete
```

## 📊 Views Available
1. **Dashboard**: `/o-meet/dashboard` - Google Meet-style landing
2. **Kanban**: Card-based meeting overview
3. **List**: Table with filters and badges
4. **Form**: Detailed meeting management

## 🎯 Use Cases

### Sales Team
- Instant client calls from CRM
- Schedule demo meetings
- Share links in email campaigns

### Support Team  
- Quick screen sharing sessions
- Scheduled customer onboarding
- Internal team standups

### HR Department
- Interview scheduling
- Team meetings
- Remote onboarding sessions

## 🔐 Access Control
- Create meeting: `jitsi_meet_ui.group_jitsi_user`
- Join meeting: Public (no access rules)
- Dashboard: Authenticated users

## 🌐 Multi-User Support
- Each user sees "My Meetings" by default
- Shared meetings via attendee list
- Public URLs work for external participants

## ⚙️ Configuration

### Custom Jitsi Server
Settings → Technical → System Parameters
- Key: `jitsi.server_url`  
- Value: `https://your-jitsi.com`

### Default Settings
- Server: `meet.jit.si`
- Room format: `meet-[random]`
- Duration: 1 hour default

## 📱 Browser Support
- Chrome, Firefox, Edge, Safari
- Desktop and mobile browsers
- WebRTC required for video/audio

## 🐛 Troubleshooting

### Meeting won't load
- Check browser allows camera/microphone
- Verify WebRTC is enabled
- Test with meet.jit.si directly

### Can't create meetings
- Check user has jitsi_meet_ui access rights
- Verify module is fully installed/upgraded

### Dashboard not showing
- Clear browser cache
- Check route `/o-meet/dashboard` is accessible
- Verify Odoo service is running

## 📈 Version Info
- **Current**: v1.0.1
- **Odoo**: 18.0 Community Edition
- **Dependencies**: base, web, website
- **License**: LGPL-3

---

**Ready to meet? Open O-Meet and start connecting!** 🎥

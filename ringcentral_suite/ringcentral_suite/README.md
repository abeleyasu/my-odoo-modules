# RingCentral Suite for Odoo 18

**Complete Business Communications Platform**

Transform Odoo into a full-featured cloud phone system with RingCentral integration.

## 🚀 Features

### 📞 Voice Calling
- **Click-to-Dial** - Call from anywhere in Odoo with one click
- **WebRTC Softphone** - Browser-based calling using RingCentral Embeddable
- **Call Control** - Hold, mute, transfer, conference
- **Incoming Call Popup** - See caller info before answering
- **Auto-Logging** - All calls automatically logged to Odoo

### 💬 SMS & MMS
- **Two-Way SMS** - Send and receive SMS directly
- **MMS Support** - Send images and files
- **Templates** - Pre-built message templates
- **Bulk SMS** - Mass messaging campaigns
- **Conversation Threads** - Full history per contact

### 🎙️ Recording & AI
- **Call Recording** - Automatic and on-demand
- **On-Demand Playback** - Stream without downloading (privacy-first)
- **AI Transcription** - Speech-to-text using RingCentral AI
- **Sentiment Analysis** - Understand customer mood

### 🔌 Integrations
- **CRM** - Click-to-call from leads/opportunities
- **Sales** - Call from quotations and orders
- **Helpdesk** - Voice & SMS for support tickets
- **Project** - Communicate with stakeholders
- **HR** - Employee communications

### 🔒 Enterprise Security
- **Webhook Signature Verification**
- **IP Allowlisting**
- **Encrypted Credentials (AES-256)**
- **Role-Based Access Control**
- **Audit Logging**

## 📦 Included Modules (22 total)

| Module | Description |
|--------|-------------|
| `ringcentral_base` | Core API integration, authentication, webhooks |
| `ringcentral_call` | Click-to-dial, CDR sync, call logging |
| `ringcentral_sms` | Two-way SMS/MMS, templates, bulk messaging |
| `ringcentral_webrtc` | Browser-based softphone |
| `ringcentral_recording` | Call recording management |
| `ringcentral_ai` | AI transcription, sentiment analysis |
| `ringcentral_voicemail` | Visual voicemail with transcription |
| `alkez_ringcentral_fax` | Digital fax send/receive |
| `ringcentral_presence` | User availability and presence |
| `ringcentral_meet` | Video meetings integration |
| `ringcentral_portal` | Customer portal |
| `ringcentral_website` | Callback widget for website |
| `ringcentral_analytics` | Call analytics and dashboards |
| `ringcentral_compliance` | GDPR/HIPAA compliance features |
| `ringcentral_quality` | Call quality monitoring |
| `ringcentral_crm` | Deep CRM integration |
| `ringcentral_sale` | Sales integration |
| `ringcentral_project` | Project/timesheet integration |
| `ringcentral_helpdesk` | Helpdesk ticket integration |
| `ringcentral_hr` | HR module integration |
| `ringcentral_contact_center` | Call queues and ACD |
| `ringcentral_multiline` | Multi-line/department configuration |

## 📋 Requirements

### Odoo Requirements
- Odoo 18.0 (Enterprise or Community)
- Python 3.10+
- PostgreSQL 13+

### RingCentral Requirements
- RingCentral Office / MVP account
- RingCentral Developer App (for API access)
- Admin access to configure webhooks

### Python Dependencies
```bash
pip install ringcentral requests cryptography requests_toolbelt
```

## 🔧 Installation

1. **Download the module package** from Odoo Apps
2. **Extract** to your Odoo addons directory
3. **Install Python dependencies**:
   ```bash
   pip install ringcentral requests cryptography requests_toolbelt
   ```
4. **Update Apps List** in Odoo
5. **Install** "RingCentral Suite" module

## ⚙️ Configuration

1. Go to **Settings > RingCentral**
2. Enter your RingCentral credentials:
   - Client ID
   - Client Secret
   - JWT Token or OAuth credentials
3. Configure webhooks:
   - Webhook URL: `https://yourodoo.com/ringcentral/webhook`
   - Enable webhook signature verification
4. Test connection

## 💰 Pricing

**$200 USD** - One-time purchase
- ✅ All 22 modules included
- ✅ Unlimited users - no per-seat fees
- ✅ Free updates for Odoo 18
- ✅ Full source code included
- ✅ Email support from developer

## 📞 Support

- **Website**: [https://www.alkezz.site](https://www.alkezz.site)
- **Developer**: Abel Eyasu
- **Email**: support@alkezz.site

## 📄 License

This module is licensed under the Odoo Proprietary License v1.0 (OPL-1).
See LICENSE file for full details.

## ⚠️ Disclaimer

RingCentral® is a registered trademark of RingCentral, Inc. This module is not affiliated with or endorsed by RingCentral, Inc.

---

**© 2025-2026 Abel Eyasu - Alkez ERP**

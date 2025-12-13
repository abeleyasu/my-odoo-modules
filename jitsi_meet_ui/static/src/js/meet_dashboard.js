/** @odoo-module */

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { Component, useState, onWillStart } from '@odoo/owl';

class MeetDashboard extends Component {
    setup() {
        this.orm = useService('orm');
        this.action = useService('action');
        this.notification = useService('notification');
        this.state = useState({ meetings: [], isLoading: true });
        onWillStart(() => this.loadMeetings());
    }

    async loadMeetings() {
        this.state.isLoading = true;
        try {
            const meetings = await this.orm.call('jitsi.meeting', 'search_read', [[], ['id', 'name', 'room_name', 'start_datetime']]);
            this.state.meetings = meetings;
        } catch (e) {
            console.error('Failed to load meetings', e);
            this.notification.add('Failed to load meetings', { type: 'danger' });
        }
        this.state.isLoading = false;
    }

    async join(meetingId) {
        try {
            const action = await this.orm.call('jitsi.meeting', 'action_join', [[meetingId]]);
            if (action) {
                try { await this.action.doAction(action); } catch (err) { console.error('doAction join', err); }
            }
        } catch (e) {
            console.error('Join failed', e);
            this.notification.add('Failed to join meeting', { type: 'danger' });
        }
    }
}

MeetDashboard.template = 'jitsi_meet_ui.MeetDashboard';
registry.category('actions').add('jitsi_meet_ui.meet_dashboard', MeetDashboard);

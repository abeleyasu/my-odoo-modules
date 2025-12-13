/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

export class CreateInstantMeeting extends Component {
    async onClick() {
        const result = await this.env.services.orm.call(
            'jitsi.meeting',
            'create_instant_meeting',
            []
        );
        if (result && result.url) {
            window.open(result.url, '_blank');
        }
    }
}

CreateInstantMeeting.template = "jitsi_meet_ui.CreateInstantMeetingButton";

export const createInstantMeetingItem = {
    Component: CreateInstantMeeting,
};

registry.category("systray").add("CreateInstantMeeting", createInstantMeetingItem, { sequence: 1 });

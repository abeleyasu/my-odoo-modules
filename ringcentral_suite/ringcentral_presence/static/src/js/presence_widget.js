/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class RingCentralPresenceWidget extends Component {
    static template = "ringcentral_presence.PresenceWidget";
    
    setup() {
        this.orm = useService("orm");
        this.bus = useService("bus_service");
        this.state = useState({
            presences: [],
            myStatus: 'offline',
        });
        
        onWillStart(async () => {
            await this.loadPresences();
        });
        
        // Subscribe to presence updates
        this.bus.subscribe("ringcentral_presence", (payload) => {
            this.onPresenceUpdate(payload);
        });
    }
    
    async loadPresences() {
        try {
            const presences = await this.orm.call(
                "ringcentral.presence",
                "get_all_presence",
                []
            );
            this.state.presences = presences || [];
        } catch (error) {
            // Silently handle access errors - user may not have RingCentral access
            console.debug('RingCentral presence not available:', error.message);
            this.state.presences = [];
        }
    }
    
    onPresenceUpdate(payload) {
        const index = this.state.presences.findIndex(p => p.user_id === payload.user_id);
        if (index >= 0) {
            this.state.presences[index] = { ...this.state.presences[index], ...payload };
        }
    }
    
    async onStatusChange(status) {
        try {
            await this.orm.call(
                "res.users",
                "action_set_presence",
                [[this.env.session.uid], status]
            );
            this.state.myStatus = status;
        } catch (error) {
            console.error('Failed to update presence status:', error);
        }
    }
    
    getStatusColor(status) {
        const colors = {
            available: '#28a745',
            busy: '#ffc107',
            dnd: '#dc3545',
            offline: '#6c757d',
            away: '#fd7e14',
        };
        return colors[status] || '#6c757d';
    }
}

RingCentralPresenceWidget.props = {};

registry.category("systray").add("ringcentral.presence", {
    Component: RingCentralPresenceWidget,
    sequence: 90,
});

/** @odoo-module */

import { Component, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Click-to-Call Phone Widget
 * 
 * A phone field widget that adds a call button to initiate calls
 * through the RingCentral Embeddable widget.
 */
export class ClickToCallWidget extends Component {
    static template = "ringcentral_webrtc.ClickToCallWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.notification = useService("notification");
        
        // Try to get the RingCentral Embeddable service
        try {
            this.rcService = useService("ringcentral_embeddable");
        } catch (e) {
            console.warn("RingCentral Embeddable service not available");
            this.rcService = null;
        }
    }

    get phoneNumber() {
        return this.props.record.data[this.props.name] || "";
    }
    
    get formattedPhone() {
        return this.phoneNumber;
    }
    
    get hasPhone() {
        return !!this.phoneNumber && this.phoneNumber.trim() !== "";
    }
    
    get canCall() {
        return this.hasPhone && this.rcService && this.rcService.state.widgetReady;
    }

    onCallClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        
        if (!this.hasPhone) {
            this.notification.add("No phone number available", { type: "warning" });
            return;
        }
        
        if (!this.rcService || !this.rcService.state.widgetReady) {
            this.notification.add("RingCentral widget not ready. Opening dialer...", { type: "info" });
            // Try to open dialer with the phone number
            if (this.rcService) {
                this.rcService.openDialer(this.phoneNumber);
            }
            return;
        }
        
        // Get contact name if available
        const record = this.props.record;
        let contactName = "";
        
        if (record.data.name) {
            contactName = record.data.name;
        } else if (record.data.display_name) {
            contactName = record.data.display_name;
        } else if (record.data.partner_id) {
            contactName = record.data.partner_id[1] || "";
        }
        
        // Get record context for logging
        const resModel = record.resModel || null;
        const resId = record.resId || null;
        const options = { res_model: resModel, res_id: resId };
        
        // Initiate call
        if (contactName) {
            this.rcService.makeCallWithContact(this.phoneNumber, contactName, options);
        } else {
            this.rcService.makeCall(this.phoneNumber, options);
        }
        
        this.notification.add(`Calling ${contactName || this.phoneNumber}...`, { type: "success" });
    }
    
    onSMSClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        
        if (!this.hasPhone) {
            this.notification.add("No phone number available", { type: "warning" });
            return;
        }
        
        if (this.rcService) {
            this.rcService.sendSMS(this.phoneNumber);
        }
    }
}

ClickToCallWidget.template = "ringcentral_webrtc.ClickToCallWidget";

export const clickToCallWidget = {
    component: ClickToCallWidget,
    displayName: "Click to Call",
    supportedTypes: ["char"],
};

registry.category("fields").add("click_to_call", clickToCallWidget);


/**
 * Phone with Call Button Widget
 * 
 * Enhanced phone widget with an integrated call button.
 */
export class PhoneCallWidget extends Component {
    static template = "ringcentral_webrtc.PhoneCallWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.notification = useService("notification");
        
        try {
            this.rcService = useService("ringcentral_embeddable");
        } catch (e) {
            this.rcService = null;
        }
    }

    get phoneNumber() {
        return this.props.record.data[this.props.name] || "";
    }
    
    get hasPhone() {
        return !!this.phoneNumber && this.phoneNumber.trim() !== "";
    }
    
    get canCall() {
        return this.hasPhone && this.rcService && this.rcService.state.widgetReady;
    }

    onCallClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        
        if (!this.hasPhone) {
            return;
        }
        
        if (this.rcService) {
            const record = this.props.record;
            const contactName = record.data.name || record.data.display_name || "";
            const resModel = record.resModel || null;
            const resId = record.resId || null;
            
            // Pass context for call logging
            const options = { res_model: resModel, res_id: resId };
            
            if (contactName) {
                this.rcService.makeCallWithContact(this.phoneNumber, contactName, options);
            } else {
                this.rcService.makeCall(this.phoneNumber, options);
            }
            
            // Show notification
            this.notification.add(`Calling ${contactName || this.phoneNumber}...`, { type: "success" });
        }
    }
}

export const phoneCallWidget = {
    component: PhoneCallWidget,
    displayName: "Phone with Call",
    supportedTypes: ["char"],
};

registry.category("fields").add("phone_call", phoneCallWidget);

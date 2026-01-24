/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * RingCentral Call Action
 * 
 * Client action to initiate a call using the RingCentral Embeddable widget
 */
export class RingCentralCallAction extends Component {
    setup() {
        this.notification = useService("notification");
        this.actionService = useService("action");
        
        // Try to get the RingCentral Embeddable service
        try {
            this.rcService = useService("ringcentral_embeddable");
        } catch (e) {
            this.rcService = null;
            console.warn("RingCentral Embeddable service not available:", e);
        }
        
        // Initiate call immediately
        this.initiateCall();
    }
    
    closeAction() {
        // Try multiple ways to close the action
        if (this.props.close) {
            this.props.close();
        } else if (this.env.config && this.env.config.onClose) {
            this.env.config.onClose();
        } else {
            // Fallback: use action service to go back
            try {
                this.actionService.restore();
            } catch (e) {
                console.warn("Could not restore action:", e);
            }
        }
    }
    
    initiateCall() {
        const context = this.props.action?.context || this.env.action?.context || {};
        const phoneNumber = context.phone_number;
        const contactName = context.contact_name || "";
        const resModel = context.res_model || null;
        const resId = context.res_id || null;
        
        console.log("RingCentral CallAction: initiateCall called with:", { phoneNumber, contactName, resModel, resId });
        
        if (!phoneNumber) {
            this.notification.add("No phone number provided", { type: "warning" });
            this.closeAction();
            return;
        }
        
        const tryCall = async (attempt = 0) => {
            console.log(`RingCentral CallAction: tryCall attempt ${attempt}`);
            
            // Check if RingCentral service is available
            if (!this.rcService) {
                console.warn("RingCentral CallAction: Service not available, falling back to tel: link");
                this.notification.add(
                    `Opening phone app to call ${phoneNumber}...`,
                    { type: "info" }
                );
                window.open(`tel:${phoneNumber}`, '_self');
                this.closeAction();
                return;
            }

            const state = this.rcService.state;
            console.log("RingCentral CallAction: Current state:", JSON.stringify(state));
            
            const maxAttempts = 20; // ~24 seconds total

            // Check if widget is ready
            if (!state.widgetReady) {
                // On first attempt, try to initialize the widget and show loading message
                if (attempt === 0) {
                    console.log("RingCentral CallAction: Widget not ready, triggering initialization...");
                    this.notification.add(
                        "Loading RingCentral phone. Please wait...",
                        { type: "info", sticky: false }
                    );
                    
                    // Try to initialize if the service has an initialize method
                    if (this.rcService.initialize) {
                        try {
                            await this.rcService.initialize();
                            console.log("RingCentral CallAction: Initialize returned, checking state...");
                        } catch (e) {
                            console.error("RingCentral CallAction: Initialize threw error:", e);
                        }
                    }
                }
                
                // Log progress every 5 attempts
                if (attempt > 0 && attempt % 5 === 0) {
                    console.log(`RingCentral CallAction: Still waiting for widget (attempt ${attempt})...`);
                }
                
                if (attempt < maxAttempts) {
                    setTimeout(() => tryCall(attempt + 1), 1200);
                } else {
                    console.error("RingCentral CallAction: Widget never became ready after", maxAttempts, "attempts (~24 seconds)");
                    this.notification.add(
                        "RingCentral widget failed to load. Check browser console for errors.",
                        { type: "danger" }
                    );
                    // Fallback to tel: link so user can still make the call
                    this.notification.add(
                        `Opening phone app to call ${phoneNumber}...`,
                        { type: "info" }
                    );
                    window.open(`tel:${phoneNumber}`, '_self');
                    this.closeAction();
                }
                return;
            }

            console.log("RingCentral CallAction: Widget ready, placing call...");
            
            // Attach context for logging
            if (this.rcService.setCallContext) {
                this.rcService.setCallContext({
                    res_model: resModel,
                    res_id: resId,
                    contact_name: contactName,
                });
            }
            
            // Make the call - widget will prompt for login if needed
            const callPlaced = contactName
                ? this.rcService.makeCallWithContact(phoneNumber, contactName, { res_model: resModel, res_id: resId })
                : this.rcService.makeCall(phoneNumber, { res_model: resModel, res_id: resId });
            
            console.log("RingCentral CallAction: callPlaced =", callPlaced);
            
            if (callPlaced) {
                this.notification.add(
                    `Calling ${contactName || phoneNumber}...`,
                    { type: "success", title: "Call Initiated" }
                );
            }
            
            this.closeAction();
        };

        tryCall();
    }
}

// Simple template - this component doesn't need to render anything
// It just triggers the call and closes immediately
RingCentralCallAction.template = "ringcentral_webrtc.CallActionTemplate";
RingCentralCallAction.props = {
    close: { type: Function, optional: true },
    action: { type: Object, optional: true },
};

registry.category("actions").add("ringcentral_make_call", RingCentralCallAction);

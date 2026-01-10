/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Client action to show the RingCentral call widget
 * 
 * This action is triggered when a call is initiated from any app.
 * It broadcasts an event that the CallControlWidget listens for.
 */
function showCallWidgetAction(env, action) {
    const params = action.params || {};

    // Prefer RingCentral Embeddable widget if it is available.
    // This makes click-to-call work even if some flows still return the legacy action tag.
    const rcService = env.services && env.services.ringcentral_embeddable;
    const phoneNumber = params.phone_number;
    const contactName = params.partner_name;
    const resModel = params.res_model;
    const resId = params.res_id;

    if (rcService && phoneNumber) {
        try {
            // Ensure the widget is visible / initialized.
            if (!rcService.state?.widgetReady) {
                rcService.initialize?.();
            }
            rcService.showWidget?.();

            // If we're not yet logged in, we can't place the call right now; show the widget and exit.
            if (!rcService.state?.loggedIn) {
                env.services.notification.add(
                    "RingCentral is signing in. Please try again in a moment.",
                    { type: "info" }
                );
                return;
            }

            if (contactName) {
                rcService.makeCallWithContact(phoneNumber, contactName, {
                    res_model: resModel,
                    res_id: resId,
                });
            } else {
                rcService.makeCall(phoneNumber, {
                    res_model: resModel,
                    res_id: resId,
                });
            }
            return;
        } catch (e) {
            // Fall back to legacy widget flow below.
            console.warn("RingCentral Embeddable call failed; falling back to legacy widget", e);
        }
    }
    
    // Broadcast event to show the call widget
    env.bus.trigger("RINGCENTRAL_CALL_INITIATED", {
        id: params.call_id,
        phone_number: params.phone_number,
        partner_name: params.partner_name,
        partner_id: params.partner_id,
        direction: params.direction || "outbound",
        state: params.state || "pending",
        is_muted: false,
        is_on_hold: false,
        is_recording: false,
    });
    
    // Return nothing - the widget handles the display
    return;
}

registry.category("actions").add("ringcentral_show_call_widget", showCallWidgetAction);

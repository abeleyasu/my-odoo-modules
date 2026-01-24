/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Client action to make a call using RingCentral Embeddable widget
 * 
 * This action is triggered when a call is initiated from any app (CRM, Sales, etc.)
 * It uses the RingCentral Embeddable widget instead of the custom OWL widget.
 */
function embeddableCallAction(env, action) {
    const params = action.params || {};
    const phoneNumber = params.phone_number;
    const contactName = params.partner_name || params.contact_name;
    const resModel = params.res_model;
    const resId = params.res_id;
    
    console.log("RingCentral embeddableCallAction triggered:", {phoneNumber, contactName, resModel, resId});
    
    if (!phoneNumber) {
        env.services.notification.add("No phone number provided", { type: "warning" });
        return;
    }
    
    // Get the RingCentral Embeddable service
    const rcService = env.services.ringcentral_embeddable;
    
    if (!rcService) {
        console.error("RingCentral Embeddable service not available");
        env.services.notification.add("RingCentral widget not available. Please refresh the page.", { type: "danger" });
        return;
    }
    
    // Check if widget is ready
    if (!rcService.state.widgetReady) {
        console.log("RingCentral widget not ready, initializing...");
        rcService.initialize();
        env.services.notification.add("RingCentral widget is loading. Please try again in a moment.", { type: "info" });
        return;
    }
    
    // Check if logged in
    if (!rcService.state.loggedIn) {
        console.log("RingCentral not logged in");
        env.services.notification.add("RingCentral is not signed in. Please wait for authentication.", { type: "warning" });
        return;
    }
    
    // Make the call using the embeddable widget
    console.log("RingCentral: Making call to", phoneNumber);
    
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
    
    // Return nothing - the embeddable widget handles everything
    return;
}

// Register the action
registry.category("actions").add("ringcentral_embeddable_call", embeddableCallAction);

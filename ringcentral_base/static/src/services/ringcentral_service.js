/** @odoo-module **/

import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

/**
 * RingCentral Service
 * 
 * Core service providing RingCentral functionality to the frontend.
 * Handles click-to-dial, notifications, and real-time events.
 */
export const ringcentralService = {
    dependencies: ["notification", "bus_service"],
    
    async start(env, { notification, bus_service }) {
        let isEnabled = false;
        let currentCall = null;
        let presenceStatus = "Available";
        
        // Check if RingCentral is enabled
        try {
            const result = await rpc("/web/dataset/call_kw/res.company/read", {
                model: "res.company",
                method: "read",
                args: [[user.companyId], ["ringcentral_enabled"]],
                kwargs: {},
            });
            isEnabled = result[0]?.ringcentral_enabled || false;
        } catch (e) {
            console.warn("RingCentral: Could not check if enabled", e);
        }
        
        // Subscribe to bus events for real-time updates
        if (isEnabled) {
            bus_service.subscribe(`ringcentral_presence_${user.userId}`, (payload) => {
                presenceStatus = payload.presence_status;
                // Trigger UI update
                env.bus.trigger("RINGCENTRAL_PRESENCE_UPDATE", payload);
            });
            
            bus_service.subscribe(`ringcentral_call_${user.userId}`, (payload) => {
                currentCall = payload;
                // Handle incoming call notification
                if (payload.type === "incoming") {
                    notification.add(
                        _t("Incoming call from %s", payload.caller_name || payload.phone_number),
                        {
                            type: "info",
                            sticky: true,
                            title: _t("Incoming Call"),
                            buttons: [
                                {
                                    name: _t("Answer"),
                                    onClick: () => answerCall(payload.call_id),
                                    primary: true,
                                },
                                {
                                    name: _t("Decline"),
                                    onClick: () => declineCall(payload.call_id),
                                },
                            ],
                        }
                    );
                }
                env.bus.trigger("RINGCENTRAL_CALL_UPDATE", payload);
            });
        }
        
        /**
         * Initiate a call using RingOut
         * @param {string} phoneNumber - Number to call
         * @param {Object} options - Call options
         */
        async function makeCall(phoneNumber, options = {}) {
            if (!isEnabled) {
                notification.add(_t("RingCentral is not enabled"), { type: "warning" });
                return null;
            }
            
            try {
                const result = await rpc("/web/dataset/call_kw/ringcentral.call/action_make_call", {
                    model: "ringcentral.call",
                    method: "action_make_call",
                    args: [phoneNumber],
                    kwargs: {
                        partner_id: options.partner_id,
                        res_model: options.res_model,
                        res_id: options.res_id,
                    },
                });
                
                notification.add(_t("Calling %s...", phoneNumber), { type: "info" });
                currentCall = result;
                return result;
            } catch (e) {
                notification.add(_t("Failed to make call: %s", e.message), { type: "danger" });
                return null;
            }
        }
        
        /**
         * Send SMS message
         * @param {string} phoneNumber - Recipient number
         * @param {string} message - Message text
         * @param {Object} options - Send options
         */
        async function sendSMS(phoneNumber, message, options = {}) {
            if (!isEnabled) {
                notification.add(_t("RingCentral is not enabled"), { type: "warning" });
                return null;
            }
            
            try {
                const result = await rpc("/web/dataset/call_kw/ringcentral.sms/action_send_sms", {
                    model: "ringcentral.sms",
                    method: "action_send_sms",
                    args: [phoneNumber, message],
                    kwargs: {
                        partner_id: options.partner_id,
                        res_model: options.res_model,
                        res_id: options.res_id,
                    },
                });
                
                notification.add(_t("SMS sent to %s", phoneNumber), { type: "success" });
                return result;
            } catch (e) {
                notification.add(_t("Failed to send SMS: %s", e.message), { type: "danger" });
                return null;
            }
        }
        
        /**
         * Answer incoming call
         * @param {string} callId - Call ID to answer
         */
        async function answerCall(callId) {
            try {
                await rpc("/web/dataset/call_kw/ringcentral.call/action_answer", {
                    model: "ringcentral.call",
                    method: "action_answer",
                    args: [[callId]],
                    kwargs: {},
                });
            } catch (e) {
                notification.add(_t("Failed to answer call"), { type: "danger" });
            }
        }
        
        /**
         * Decline incoming call
         * @param {string} callId - Call ID to decline
         */
        async function declineCall(callId) {
            try {
                await rpc("/web/dataset/call_kw/ringcentral.call/action_decline", {
                    model: "ringcentral.call",
                    method: "action_decline",
                    args: [[callId]],
                    kwargs: {},
                });
            } catch (e) {
                notification.add(_t("Failed to decline call"), { type: "danger" });
            }
        }
        
        /**
         * Hang up current call
         */
        async function hangUp() {
            if (!currentCall) return;
            
            try {
                await rpc("/web/dataset/call_kw/ringcentral.call/action_hangup", {
                    model: "ringcentral.call",
                    method: "action_hangup",
                    args: [[currentCall.id]],
                    kwargs: {},
                });
                currentCall = null;
            } catch (e) {
                notification.add(_t("Failed to hang up"), { type: "danger" });
            }
        }
        
        /**
         * Hold/unhold current call
         */
        async function toggleHold() {
            if (!currentCall) return;
            
            try {
                await rpc("/web/dataset/call_kw/ringcentral.call/action_toggle_hold", {
                    model: "ringcentral.call",
                    method: "action_toggle_hold",
                    args: [[currentCall.id]],
                    kwargs: {},
                });
            } catch (e) {
                notification.add(_t("Failed to toggle hold"), { type: "danger" });
            }
        }
        
        /**
         * Mute/unmute current call
         */
        async function toggleMute() {
            if (!currentCall) return;
            
            try {
                await rpc("/web/dataset/call_kw/ringcentral.call/action_toggle_mute", {
                    model: "ringcentral.call",
                    method: "action_toggle_mute",
                    args: [[currentCall.id]],
                    kwargs: {},
                });
            } catch (e) {
                notification.add(_t("Failed to toggle mute"), { type: "danger" });
            }
        }
        
        /**
         * Transfer call to another number
         * @param {string} toNumber - Number to transfer to
         */
        async function transferCall(toNumber) {
            if (!currentCall) return;
            
            try {
                await rpc("/web/dataset/call_kw/ringcentral.call/action_transfer", {
                    model: "ringcentral.call",
                    method: "action_transfer",
                    args: [[currentCall.id], toNumber],
                    kwargs: {},
                });
                notification.add(_t("Call transferred to %s", toNumber), { type: "success" });
            } catch (e) {
                notification.add(_t("Failed to transfer call"), { type: "danger" });
            }
        }
        
        /**
         * Set user presence status
         * @param {string} status - Presence status
         */
        async function setPresence(status) {
            try {
                await rpc("/web/dataset/call_kw/res.users/action_set_presence", {
                    model: "res.users",
                    method: "action_set_presence",
                    args: [[user.userId], status],
                    kwargs: {},
                });
                presenceStatus = status;
                env.bus.trigger("RINGCENTRAL_PRESENCE_UPDATE", { presence_status: status });
            } catch (e) {
                notification.add(_t("Failed to set presence"), { type: "danger" });
            }
        }
        
        return {
            // Properties
            get isEnabled() { return isEnabled; },
            get currentCall() { return currentCall; },
            get presenceStatus() { return presenceStatus; },
            
            // Methods
            makeCall,
            sendSMS,
            answerCall,
            declineCall,
            hangUp,
            toggleHold,
            toggleMute,
            transferCall,
            setPresence,
        };
    },
};

registry.category("services").add("ringcentral", ringcentralService);

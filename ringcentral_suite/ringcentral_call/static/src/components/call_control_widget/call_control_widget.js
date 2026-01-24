/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

/**
 * RingCentral Call Control Widget
 * 
 * A floating widget that appears when a call is active, providing
 * controls to manage the call (mute, hold, hang up, transfer).
 */
export class CallControlWidget extends Component {
    static template = "ringcentral_call.CallControlWidget";
    static props = {};
    
    setup() {
        this.notification = useService("notification");
        this.action = useService("action");
        this.bus = useService("bus_service");
        
        this.state = useState({
            visible: false,
            minimized: false,
            call: null,
            callState: "pending",
            callDuration: 0,
            isMuted: false,
            isOnHold: false,
            isRecording: false,
            partnerName: "",
            phoneNumber: "",
            direction: "outbound",
            showTransfer: false,
            transferNumber: "",
        });
        
        this.timerInterval = null;
        
        onWillStart(async () => {
            // Check for any active calls on load
            // If Embeddable widget is installed, do not auto-show legacy widget.
            if (!this.env.services?.ringcentral_embeddable) {
                await this.checkActiveCalls();
            }
        });
        
        onMounted(() => {
            // Subscribe to call events
            this.subscribeToCallEvents();
        });
        
        onWillUnmount(() => {
            if (this.timerInterval) {
                clearInterval(this.timerInterval);
            }
        });
    }
    
    subscribeToCallEvents() {
        // If Embeddable widget is installed, do not display the legacy widget.
        if (this.env.services?.ringcentral_embeddable) {
            return;
        }
        // Listen for call state updates from the RingCentral service
        this.env.bus.addEventListener("RINGCENTRAL_CALL_UPDATE", (ev) => {
            this.handleCallUpdate(ev.detail);
        });
        
        // Listen for call initiated event
        this.env.bus.addEventListener("RINGCENTRAL_CALL_INITIATED", (ev) => {
            this.showCall(ev.detail);
        });
        
        // Listen for call ended event
        this.env.bus.addEventListener("RINGCENTRAL_CALL_ENDED", () => {
            this.hideCall();
        });
    }
    
    async checkActiveCalls() {
        if (this.env.services?.ringcentral_embeddable) {
            return;
        }
        try {
            const result = await rpc("/web/dataset/call_kw/ringcentral.call/get_user_active_call", {
                model: "ringcentral.call",
                method: "get_user_active_call",
                args: [],
                kwargs: {},
            });
            
            if (result && result.id) {
                this.showCall(result);
            }
        } catch (e) {
            console.warn("Could not check for active calls:", e);
        }
    }
    
    handleCallUpdate(callData) {
        if (!callData) return;
        
        this.state.callState = callData.state || this.state.callState;
        this.state.isMuted = callData.is_muted || false;
        this.state.isOnHold = callData.is_on_hold || false;
        this.state.isRecording = callData.is_recording || false;
        
        if (callData.state === "ended" || callData.state === "failed") {
            this.hideCall();
        } else if (callData.state === "answered" && !this.timerInterval) {
            this.startTimer();
        }
    }
    
    showCall(callData) {
        this.state.visible = true;
        this.state.minimized = false;
        this.state.call = callData;
        this.state.callState = callData.state || "pending";
        this.state.partnerName = callData.partner_name || "";
        this.state.phoneNumber = callData.phone_number || "";
        this.state.direction = callData.direction || "outbound";
        this.state.isMuted = callData.is_muted || false;
        this.state.isOnHold = callData.is_on_hold || false;
        this.state.callDuration = 0;
        
        if (callData.state === "answered") {
            this.startTimer();
        }
    }
    
    hideCall() {
        this.state.visible = false;
        this.state.call = null;
        this.state.callDuration = 0;
        this.state.isMuted = false;
        this.state.isOnHold = false;
        this.state.showTransfer = false;
        
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }
    
    startTimer() {
        if (this.timerInterval) return;
        
        this.timerInterval = setInterval(() => {
            this.state.callDuration++;
        }, 1000);
    }
    
    formatDuration(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    
    get displayName() {
        return this.state.partnerName || this.state.phoneNumber || _t("Unknown");
    }
    
    get statusText() {
        const states = {
            pending: _t("Initiating..."),
            ringing: _t("Ringing..."),
            answered: this.formatDuration(this.state.callDuration),
            on_hold: _t("On Hold"),
            ended: _t("Call Ended"),
            failed: _t("Call Failed"),
        };
        return states[this.state.callState] || this.state.callState;
    }
    
    get directionIcon() {
        return this.state.direction === "inbound" ? "fa-arrow-down" : "fa-arrow-up";
    }
    
    toggleMinimize() {
        this.state.minimized = !this.state.minimized;
    }
    
    async onMute() {
        if (!this.state.call?.id) return;
        
        try {
            await rpc("/web/dataset/call_kw/ringcentral.call/action_toggle_mute", {
                model: "ringcentral.call",
                method: "action_toggle_mute",
                args: [[this.state.call.id]],
                kwargs: {},
            });
            this.state.isMuted = !this.state.isMuted;
        } catch (e) {
            this.notification.add(_t("Failed to toggle mute"), { type: "danger" });
        }
    }
    
    async onHold() {
        if (!this.state.call?.id) return;
        
        try {
            await rpc("/web/dataset/call_kw/ringcentral.call/action_toggle_hold", {
                model: "ringcentral.call",
                method: "action_toggle_hold",
                args: [[this.state.call.id]],
                kwargs: {},
            });
            this.state.isOnHold = !this.state.isOnHold;
            this.state.callState = this.state.isOnHold ? "on_hold" : "answered";
        } catch (e) {
            this.notification.add(_t("Failed to toggle hold"), { type: "danger" });
        }
    }
    
    async onRecord() {
        if (!this.state.call?.id) return;
        
        try {
            await rpc("/web/dataset/call_kw/ringcentral.call/action_toggle_recording", {
                model: "ringcentral.call",
                method: "action_toggle_recording",
                args: [[this.state.call.id]],
                kwargs: {},
            });
            this.state.isRecording = !this.state.isRecording;
            this.notification.add(
                this.state.isRecording ? _t("Recording started") : _t("Recording stopped"),
                { type: "info" }
            );
        } catch (e) {
            this.notification.add(_t("Failed to toggle recording"), { type: "danger" });
        }
    }
    
    onTransfer() {
        this.state.showTransfer = !this.state.showTransfer;
    }
    
    async doTransfer() {
        if (!this.state.call?.id || !this.state.transferNumber) return;
        
        try {
            await rpc("/web/dataset/call_kw/ringcentral.call/action_transfer", {
                model: "ringcentral.call",
                method: "action_transfer",
                args: [[this.state.call.id], this.state.transferNumber],
                kwargs: {},
            });
            this.notification.add(
                _t("Call transferred to %s", this.state.transferNumber),
                { type: "success" }
            );
            this.hideCall();
        } catch (e) {
            this.notification.add(_t("Failed to transfer call"), { type: "danger" });
        }
    }
    
    async onHangup() {
        if (!this.state.call?.id) return;
        
        try {
            await rpc("/web/dataset/call_kw/ringcentral.call/action_hangup", {
                model: "ringcentral.call",
                method: "action_hangup",
                args: [[this.state.call.id]],
                kwargs: {},
            });
            this.notification.add(_t("Call ended"), { type: "info" });
            this.hideCall();
        } catch (e) {
            this.notification.add(_t("Failed to hang up"), { type: "danger" });
        }
    }
    
    openCallDetails() {
        if (!this.state.call?.id) return;
        
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "ringcentral.call",
            res_id: this.state.call.id,
            views: [[false, "form"]],
            target: "new",
        });
    }
    
    onTransferInputChange(ev) {
        this.state.transferNumber = ev.target.value;
    }
}

// Register the widget as a systray component so it's always visible
registry.category("systray").add("ringcentral.call_control", {
    Component: CallControlWidget,
}, { sequence: 1 });

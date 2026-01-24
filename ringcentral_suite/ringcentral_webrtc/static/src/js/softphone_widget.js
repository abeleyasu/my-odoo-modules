/** @odoo-module */

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class SoftphoneWidget extends Component {
    static template = "ringcentral_webrtc.SoftphoneWidget";
    
    setup() {
        this.softphone = useService("softphone");
        this.state = useState({
            expanded: false,
            dialpadVisible: false,
            phoneNumber: "",
        });
    }
    
    get callState() {
        return this.softphone.state;
    }
    
    toggleExpand() {
        this.state.expanded = !this.state.expanded;
    }
    
    toggleDialpad() {
        this.state.dialpadVisible = !this.state.dialpadVisible;
    }
    
    onDialpadKey(digit) {
        this.state.phoneNumber += digit;
        if (this.callState.inCall) {
            this.softphone.sendDTMF(digit);
        }
    }
    
    onBackspace() {
        this.state.phoneNumber = this.state.phoneNumber.slice(0, -1);
    }
    
    onCall() {
        if (this.state.phoneNumber) {
            this.softphone.makeCall(this.state.phoneNumber);
        }
    }
    
    onAnswer() {
        this.softphone.answerCall();
    }
    
    onHangUp() {
        this.softphone.hangUp();
        this.state.phoneNumber = "";
    }
    
    onMute() {
        this.softphone.toggleMute();
    }
    
    onHold() {
        this.softphone.toggleHold();
    }
    
    get formattedDuration() {
        return this.softphone.formatDuration(this.callState.duration);
    }
}

SoftphoneWidget.props = {};

// Register in systray
export const softphoneSystrayItem = {
    Component: SoftphoneWidget,
    isDisplayed: (env) => true,
};

registry.category("systray").add("SoftphoneWidget", softphoneSystrayItem, { sequence: 1 });

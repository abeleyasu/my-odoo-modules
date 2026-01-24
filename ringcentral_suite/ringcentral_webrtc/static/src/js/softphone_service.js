/** @odoo-module */

import { registry } from "@web/core/registry";
import { reactive } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export const softphoneService = {
    dependencies: ["bus_service", "notification"],
    
    start(env, { bus_service, notification }) {
        const state = reactive({
            initialized: false,
            registered: false,
            inCall: false,
            callState: null, // 'ringing', 'answered', 'held'
            currentCall: null,
            muted: false,
            held: false,
            callerId: null,
            callerName: null,
            duration: 0,
            durationInterval: null,
        });
        
        let sipSession = null;
        let userAgent = null;
        let config = null;
        
        async function initialize() {
            try {
                config = await rpc("/ringcentral/webrtc/config", {});
                
                if (!config || config.error || !config.enabled) {
                    console.log("RingCentral WebRTC Softphone disabled or not configured");
                    return;
                }
                
                if (config.warning) {
                    console.warn("RingCentral WebRTC warning:", config.warning);
                }
                
                // In production, load SIP.js library here
                // and initialize WebRTC UserAgent
                state.initialized = true;
                
                console.log("RingCentral WebRTC Softphone initialized");
            } catch (error) {
                // Silently fail - softphone is optional
                console.log("RingCentral Softphone not available:", error.message || error);
            }
        }
        
        function makeCall(phoneNumber, partnerId = null) {
            if (!state.initialized) {
                notification.add("Softphone not initialized", { type: "warning" });
                return;
            }
            
            if (state.inCall) {
                notification.add("Already in a call", { type: "warning" });
                return;
            }
            
            // Log call and start
            rpc("/ringcentral/webrtc/call/start", {
                phone_number: phoneNumber,
                partner_id: partnerId,
            }).then((result) => {
                if (result.success) {
                    state.currentCall = result.call_id;
                    state.inCall = true;
                    state.callState = "ringing";
                    startDurationTimer();
                    
                    // In production: initiate actual SIP call here
                    console.log(`Calling ${phoneNumber}...`);
                }
            });
        }
        
        function answerCall() {
            if (sipSession) {
                // sipSession.answer();
                state.callState = "answered";
                startDurationTimer();
            }
        }
        
        function hangUp() {
            if (state.currentCall) {
                rpc("/ringcentral/webrtc/call/update", {
                    call_id: state.currentCall,
                    state: "ended",
                    duration: state.duration,
                });
            }
            
            // if (sipSession) sipSession.terminate();
            
            resetCallState();
        }
        
        function toggleMute() {
            state.muted = !state.muted;
            // if (sipSession) sipSession.mute/unmute
        }
        
        function toggleHold() {
            state.held = !state.held;
            // if (sipSession) sipSession.hold/unhold
        }
        
        function sendDTMF(digit) {
            // if (sipSession) sipSession.sendDTMF(digit)
            console.log(`DTMF: ${digit}`);
        }
        
        function startDurationTimer() {
            state.duration = 0;
            state.durationInterval = setInterval(() => {
                state.duration++;
            }, 1000);
        }
        
        function resetCallState() {
            if (state.durationInterval) {
                clearInterval(state.durationInterval);
            }
            state.inCall = false;
            state.callState = null;
            state.currentCall = null;
            state.muted = false;
            state.held = false;
            state.callerId = null;
            state.callerName = null;
            state.duration = 0;
        }
        
        function formatDuration(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        
        // Initialize on service start
        initialize();
        
        return {
            state,
            makeCall,
            answerCall,
            hangUp,
            toggleMute,
            toggleHold,
            sendDTMF,
            formatDuration,
        };
    },
};

registry.category("services").add("softphone", softphoneService);

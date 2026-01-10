/** @odoo-module */

import { registry } from "@web/core/registry";
import { reactive } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { Component, useState, onMounted, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * RingCentral Embeddable Service
 * 
 * This service integrates the official RingCentral Embeddable widget
 * providing a fully functional softphone directly in Odoo.
 */
export const ringcentralEmbeddableService = {
    dependencies: ["notification"],
    
    start(env, { notification }) {
        const state = reactive({
            initialized: false,
            widgetReady: false,
            loggedIn: false,
            webphoneConnected: false,
            dialerReady: false,
            inCall: false,
            callState: null,
            minimized: true,
        });
        
        // Context about the Odoo record initiating the call (for logging)
        let callContext = {
            res_model: null,
            res_id: null,
            contact_name: null,
            phone_number: null,
        };
        
        // Track session IDs we already logged to avoid duplicates
        const loggedSessions = new Set();
        const loggedStartFallback = new Map();
        
        let rcWidget = null;
        let config = null;
        let initializationAttempts = 0;
        let isLoading = false;  // Flag to prevent concurrent initialization
        const MAX_INIT_ATTEMPTS = 5;

        function getWidgetIframe() {
            return (
                document.querySelector('iframe#rc-widget-adapter-frame') ||
                document.querySelector('iframe[src*="ringcentral-embeddable"]') ||
                document.querySelector('iframe[src*="apps.ringcentral.com/integration/ringcentral-embeddable"]')
            );
        }

        function postToWidget(payload) {
            const iframe = getWidgetIframe();
            if (iframe && iframe.contentWindow) {
                iframe.contentWindow.postMessage(payload, "*");
                return true;
            }
            // Fallback: some older versions may listen on the top window.
            window.postMessage(payload, "*");
            return false;
        }
        
        /**
         * Initialize the RingCentral Embeddable widget
         * This may be called multiple times - it will only actually init once
         */
        async function initialize() {
            console.log("RingCentral: Starting initialization... (attempt", initializationAttempts + 1, ") isLoading:", isLoading);
            
            // Prevent concurrent initialization
            if (isLoading) {
                console.log("RingCentral: Already loading, skipping duplicate init");
                return true;
            }
            
            if (state.initialized && state.widgetReady) {
                console.log("RingCentral: Already initialized and ready, skipping");
                return true;
            }
            
            // If widget iframe is already loaded (e.g., from previous page), just set it up
            const existingIframe = getWidgetIframe();
            if (existingIframe || window.RCAdapter) {
                console.log("RingCentral: Widget already loaded from previous session, iframe:", !!existingIframe, "RCAdapter:", !!window.RCAdapter);
                state.initialized = true;
                state.widgetReady = true;
                rcWidget = window.RCAdapter;
                setupEventListeners();
                // Request login status after a short delay to ensure widget is ready
                setTimeout(() => {
                    requestLoginStatus();
                }, 500);
                return true;
            }
            
            isLoading = true;
            initializationAttempts++;
            
            try {
                // Fetch configuration from backend
                console.log("RingCentral: Fetching config from backend...");
                config = await rpc("/ringcentral/embeddable/config", {});
                console.log("RingCentral: Config received:", JSON.stringify(config));
                
                if (!config) {
                    console.error("RingCentral: Config is null/undefined");
                    isLoading = false;
                    return false;
                }
                
                if (config.error) {
                    console.warn("RingCentral: Config returned error:", config.error);
                    isLoading = false;
                    return false;
                }
                
                if (!config.enabled) {
                    console.log("RingCentral: Not enabled in configuration");
                    isLoading = false;
                    return false;
                }
                
                if (!config.client_id) {
                    console.error("RingCentral: No client_id in config");
                    isLoading = false;
                    return false;
                }
                
                // Load RingCentral Embeddable script
                console.log("RingCentral: Loading embeddable script with client_id:", config.client_id.substring(0, 10) + "...");
                loadEmbeddableScript(config);
                // Note: isLoading stays true until script loads or errors
                return true;
                
            } catch (error) {
                console.error("RingCentral: Failed to initialize:", error);
                isLoading = false;
                
                // Retry with exponential backoff if we haven't exceeded max attempts
                if (initializationAttempts < MAX_INIT_ATTEMPTS) {
                    const delay = Math.pow(2, initializationAttempts) * 1000; // 2s, 4s, 8s, 16s, 32s
                    console.log(`RingCentral: Will retry initialization in ${delay}ms`);
                    setTimeout(() => initialize(), delay);
                }
                return false;
            }
        }
        
        /**
         * Load the RingCentral Embeddable adapter script
         */
        function loadEmbeddableScript(config) {
            // Check if script is already being loaded or loaded
            const existingScript = document.querySelector('script[src*="ringcentral-embeddable"]');
            if (existingScript) {
                console.log("RingCentral: Adapter script already exists in DOM, waiting for it...");
                waitForWidget();
                return;
            }
            
            const script = document.createElement("script");
            
            // Build the adapter URL with configuration - use latest stable version
            let adapterUrl = "https://apps.ringcentral.com/integration/ringcentral-embeddable/latest/adapter.js";
            
            // Add query parameters for configuration
            const params = new URLSearchParams();
            
            // Client ID is required
            if (config.client_id) {
                params.append("clientId", config.client_id);
            }
            
            // Client Secret is required for JWT auth
            if (config.client_secret) {
                params.append("clientSecret", config.client_secret);
            }
            
            // JWT token for automatic login - THIS IS THE KEY!
            // According to RingCentral docs, passing jwt as URL param auto-logs in
            if (config.jwt_token) {
                params.append("jwt", config.jwt_token);
                console.log("RingCentral: Using JWT authentication (auto-login)");
            }
            
            // Server URL (production or sandbox)
            if (config.server_url) {
                params.append("appServer", config.server_url);
            }
            
            // Start minimized - user can expand when needed
            params.append("minimized", "true");
            
            // Position - bottom right to avoid overlap with Odoo elements
            params.append("defaultDirection", "right");
            
            // Log the URL for debugging (hide sensitive data)
            const debugParams = new URLSearchParams(params);
            if (debugParams.has("jwt")) debugParams.set("jwt", "[HIDDEN]");
            if (debugParams.has("clientSecret")) debugParams.set("clientSecret", "[HIDDEN]");
            console.log("Loading RingCentral Embeddable from:", adapterUrl + "?" + debugParams.toString());
            
            const fullUrl = `${adapterUrl}?${params.toString()}`;
            
            script.src = fullUrl;
            script.async = true;
            
            script.onload = function() {
                state.initialized = true;
                isLoading = false;
                console.log("RingCentral Embeddable widget script loaded successfully");
                
                // Wait for widget to be ready
                waitForWidget();
            };
            
            script.onerror = function(error) {
                console.error("Failed to load RingCentral Embeddable:", error);
                isLoading = false;
                notification.add("Failed to load RingCentral widget", { type: "danger" });
            };
            
            document.body.appendChild(script);
        }
        
        /**
         * Wait for the RingCentral widget to be ready
         */
        function waitForWidget() {
            console.log("RingCentral: Waiting for widget to be ready...");
            let checkCount = 0;
            
            const checkInterval = setInterval(() => {
                checkCount++;
                const iframe = document.querySelector('iframe#rc-widget-adapter-frame');
                console.log(`RingCentral: Check #${checkCount} - RCAdapter:`, !!window.RCAdapter, "iframe:", !!iframe);
                
                if (window.RCAdapter && iframe) {
                    clearInterval(checkInterval);
                    state.widgetReady = true;
                    rcWidget = window.RCAdapter;
                    console.log("RingCentral: Widget and iframe are ready!");
                    setupEventListeners();
                    
                    // Request current login status from widget
                    requestLoginStatus();
                    
                    // Wait a bit for widget to fully initialize, then auto-login
                    // The widget needs time to set up its message handlers
                    console.log("RingCentral: Waiting 2s for widget to initialize...");
                    setTimeout(() => {
                        console.log("RingCentral: Initiating JWT auto-login...");
                        autoLogin();
                    }, 2000);
                    
                    // Periodically sync login status to keep systray in sync
                    setInterval(() => {
                        if (state.widgetReady) {
                            requestLoginStatus();
                        }
                    }, 10000); // Every 10 seconds
                }
            }, 500);
            
            // Timeout after 30 seconds
            setTimeout(() => {
                clearInterval(checkInterval);
                if (!state.widgetReady) {
                    console.warn("RingCentral widget initialization timeout after 30 seconds");
                }
            }, 30000);
        }
        
        /**
         * Request current login status from the widget
         * This is useful to sync state when the widget was already logged in
         */
        function requestLoginStatus() {
            // The widget will respond with rc-login-status-notify event
            postToWidget({
                type: "rc-adapter-login-status-request",
            });
        }
        
        /**
         * Auto-login using server-side JWT authentication
         */
        async function autoLogin() {
            try {
                console.log("RingCentral: Fetching access token from server...");
                const authResult = await rpc("/ringcentral/embeddable/auth", {});
                
                if (authResult.success && authResult.access_token) {
                    console.log("RingCentral: Got access token, sending to widget iframe...");
                    
                    // Find the RingCentral widget iframe
                    const rcIframe = document.querySelector('iframe#rc-widget-adapter-frame');
                    
                    if (rcIframe && rcIframe.contentWindow) {
                        // Send login message to the iframe
                        rcIframe.contentWindow.postMessage({
                            type: "rc-adapter-login",
                            accessToken: authResult.access_token,
                            refreshToken: authResult.refresh_token,
                            tokenType: authResult.token_type || "Bearer",
                            expiresIn: authResult.expires_in || 3600,
                            ownerId: authResult.owner_id,
                        }, "*");
                        console.log("RingCentral: Auto-login sent to iframe");
                        notification.add("RingCentral: Signing in...", { type: "info" });
                    } else {
                        // Fallback: try window.postMessage (older widget versions)
                        console.log("RingCentral: iframe not found, using window.postMessage");
                        window.postMessage({
                            type: "rc-adapter-login",
                            accessToken: authResult.access_token,
                            refreshToken: authResult.refresh_token,
                            tokenType: authResult.token_type || "Bearer",
                            expiresIn: authResult.expires_in || 3600,
                            ownerId: authResult.owner_id,
                        }, "*");
                        notification.add("RingCentral: Connecting...", { type: "info" });
                    }
                    state.loggedIn = true;
                } else {
                    console.error("RingCentral auto-login failed:", authResult.error);
                    notification.add("RingCentral: Login failed - " + (authResult.error || "Unknown error"), { type: "danger" });
                }
            } catch (error) {
                console.error("RingCentral auto-login error:", error);
                notification.add("RingCentral: Connection error", { type: "danger" });
            }
        }
        
        /**
         * Setup event listeners for widget communication
         */
        function setupEventListeners() {
            window.addEventListener("message", handleWidgetMessage);
        }
        
        /**
         * Handle messages from the RingCentral widget
         */
        function handleWidgetMessage(event) {
            if (!event.data || !event.data.type) return;
            
            const type = event.data.type;
            
            // Log all RingCentral events for debugging
            if (type && type.startsWith('rc-')) {
                console.log("RingCentral event:", type, event.data);
            }
            
            switch (type) {
                // IMPORTANT: Intercept OAuth popup request and provide our access token instead
                case "rc-login-popup-notify":
                    console.log("RingCentral: Widget requesting login - providing access token...");
                    // The widget is asking for OAuth login - we intercept and provide our JWT-based token
                    autoLogin();
                    break;
                
                // Login status event - this fires when user logs in/out
                case "rc-login-status-notify":
                    // The loggedIn property is directly on event.data
                    const isLoggedIn = event.data.loggedIn === true;
                    console.log("RingCentral login status changed:", isLoggedIn, "loginNumber:", event.data.loginNumber);
                    state.loggedIn = isLoggedIn;
                    if (isLoggedIn && event.data.loginNumber) {
                        notification.add(`RingCentral: Signed in as ${event.data.loginNumber}`, { type: "success" });
                    }
                    break;
                
                // Web phone connection status
                case "rc-webphone-connection-status-notify":
                    console.log("WebPhone connection:", event.data.connectionStatus);
                    state.webphoneConnected = event.data.connectionStatus === 'connectionStatus-connected';
                    // If webphone is connected, we're effectively logged in and ready
                    if (state.webphoneConnected) {
                        state.loggedIn = true;
                    }
                    break;
                
                // Dialer ready status - if dialer is ready, user must be logged in
                case "rc-dialer-status-notify":
                    console.log("Dialer ready:", event.data.ready);
                    state.dialerReady = event.data.ready || false;
                    if (state.dialerReady) {
                        state.loggedIn = true;
                    }
                    break;

                // Route change: if navigating to active call screen, force expand
                case "rc-route-changed-notify": {
                    const path = event.data?.path || event.data?.currentPath || event.data?.route;
                    if (typeof path === "string" && path.startsWith("/calls/active")) {
                        showWidget();
                    }
                    break;
                }
                    
                case "rc-call-ring-notify":
                case "rc-call-init-notify":
                    state.inCall = true;
                    state.callState = "initializing";
                    showWidget();
                    if (event.data.call) {
                        logCallStart(event.data.call);
                    }
                    break;
                    
                case "rc-call-start-notify":
                    state.inCall = true;
                    state.callState = "connected";
                    showWidget();
                    logCallStart(event.data.call);
                    break;
                    
                case "rc-call-end-notify":
                    state.inCall = false;
                    state.callState = null;
                    logCallEnd(event.data.call);
                    break;
                    
                case "rc-ringout-call-notify":
                    console.log("RingOut call event:", event.data.call);
                    state.inCall = true;
                    showWidget();
                    if (event.data.call) {
                        logCallStart(event.data.call);
                    }
                    break;
                    
                case "rc-active-call-notify":
                    if (event.data.call) {
                        state.inCall = true;
                        if (event.data.call.telephonyStatus === "CallConnected") {
                            showWidget();
                        }
                        if (event.data.call.telephonyStatus === "CallConnected") {
                            state.callState = "connected";
                        }
                    }
                    break;
                    
                case "rc-minimized-status-changed":
                    state.minimized = event.data.minimized;
                    break;
            }
        }
        
        /**
         * Log call start to Odoo
         */
        async function logCallStart(callData) {
            try {
                // Extract all possible RingCentral IDs from the call data
                const sessionId = callData?.sessionId || callData?.telephonySessionId || callData?.telephonySession?.id;
                const callId = callData?.id || callData?.callId;
                const partyId = callData?.partyId || callData?.party?.id;
                const ringoutId = callData?.ringOutId || callData?.ringoutId;
                
                // Log all call data for debugging
                console.log("RingCentral logCallStart - Full callData:", JSON.stringify(callData));
                console.log("RingCentral logCallStart - Extracted IDs:", { sessionId, callId, partyId, ringoutId });
                
                if (sessionId && loggedSessions.has(sessionId)) {
                    return;
                }
                if (sessionId) {
                    loggedSessions.add(sessionId);
                }

                const phoneNumber = callData?.to?.phoneNumber || callData?.from?.phoneNumber || callContext.phone_number;

                // Fallback dedupe when sessionId isn't available (some RC events omit it).
                // Prevent multiple rapid log-start calls for the same user action.
                if (!sessionId) {
                    const key = `${phoneNumber || ""}|${callContext.res_model || ""}|${callContext.res_id || ""}`;
                    const now = Date.now();
                    const last = loggedStartFallback.get(key);
                    if (last && now - last < 120000) {
                        return;
                    }
                    loggedStartFallback.set(key, now);
                }

                await rpc("/ringcentral/call/log-start", {
                    phone_number: phoneNumber,
                    direction: callData?.direction || "outbound",
                    session_id: sessionId,
                    call_id: callId,
                    party_id: partyId,
                    ringout_id: ringoutId,
                    res_model: callContext.res_model,
                    res_id: callContext.res_id,
                    contact_name: callContext.contact_name,
                });
            } catch (error) {
                console.error("Failed to log call start:", error);
            }
        }
        
        /**
         * Log call end to Odoo
         */
        async function logCallEnd(callData) {
            try {
                // Extract all possible RingCentral IDs
                const sessionId = callData?.sessionId || callData?.telephonySessionId || callData?.telephonySession?.id;
                const callId = callData?.id || callData?.callId;
                const partyId = callData?.partyId || callData?.party?.id;
                const recordingId = callData?.recordingId || callData?.recording?.id;
                
                console.log("RingCentral logCallEnd - Full callData:", JSON.stringify(callData));
                console.log("RingCentral logCallEnd - Extracted:", { sessionId, callId, partyId, recordingId, duration: callData?.duration, result: callData?.result });
                
                await rpc("/ringcentral/call/log-end", {
                    session_id: sessionId,
                    call_id: callId,
                    party_id: partyId,
                    recording_id: recordingId,
                    duration: callData?.duration,
                    result: callData?.result || callData?.terminationType,
                    res_model: callContext.res_model,
                    res_id: callContext.res_id,
                });
            } catch (error) {
                console.error("Failed to log call end:", error);
            }
        }

        /**
         * Normalize phone numbers into dialable format
         */
        function normalizePhoneNumber(phoneNumber) {
            if (!phoneNumber) return null;
            let normalized = String(phoneNumber).trim();
            // Keep leading +, strip other non-digit characters
            normalized = normalized.replace(/(?!^\+)[^0-9]/g, "");
            // Convert leading 00 to +
            if (normalized.startsWith("00")) {
                normalized = "+" + normalized.slice(2);
            }
            return normalized;
        }

        /**
         * Store context for the next call (used for logging/resolution)
         */
        function setCallContext(context = {}) {
            callContext = {
                res_model: null,
                res_id: null,
                contact_name: null,
                phone_number: null,
                ...context,
            };
        }
        
        /**
         * Log call attempt to Odoo chatter immediately
         */
        async function logCallAttempt(phoneNumber, options) {
            if (!options.res_model || !options.res_id) return;
            
            try {
                await rpc("/ringcentral/call/log-attempt", {
                    phone_number: phoneNumber,
                    res_model: options.res_model,
                    res_id: options.res_id,
                    contact_name: options.contact_name,
                });
            } catch (error) {
                console.error("Failed to log call attempt:", error);
            }
        }

        /**
         * Make a call using the RingCentral Embeddable widget
         */
        function makeCall(phoneNumber, options = {}) {
            console.log("RingCentral makeCall:", phoneNumber, "state:", JSON.stringify({
                widgetReady: state.widgetReady,
                loggedIn: state.loggedIn,
                initialized: state.initialized,
            }));
            
            // If widget not ready, try to initialize
            if (!state.widgetReady) {
                console.log("RingCentral: Widget not ready, trying to initialize...");
                if (!state.initialized) {
                    initialize();
                }
                notification.add("RingCentral widget is loading. Please try again in a moment.", { type: "warning" });
                return false;
            }
            
            const normalizedNumber = normalizePhoneNumber(phoneNumber);
            if (!normalizedNumber) {
                notification.add("Invalid phone number", { type: "warning" });
                return false;
            }
            
            // Store context for logging
            setCallContext({
                phone_number: normalizedNumber,
                ...options,
            });
            
            // Log attempt immediately
            logCallAttempt(normalizedNumber, options);
            
            // 1) Ensure widget is visible and on dialer screen (handles collapsed/minimized cases)
            postToWidget({
                type: "rc-adapter-minimize",
                minimize: false,
            });
            postToWidget({
                type: "rc-adapter-navigate-to",
                path: "/dialer",
                phoneNumber: normalizedNumber,
            });
            
            // 2) Send call command with a slight delay; re-send unminimize right before dialing
            setTimeout(() => {
                postToWidget({
                    type: "rc-adapter-minimize",
                    minimize: false,
                });
                postToWidget({
                    type: "rc-adapter-new-call",
                    phoneNumber: normalizedNumber,
                    toCall: true,
                });
                console.log("RingCentral: dialing", normalizedNumber, "context", callContext);
            }, 350);
            
            return true;
        }
        
        /**
         * Make a call with contact name displayed
         */
        function makeCallWithContact(phoneNumber, contactName, options = {}) {
            console.log("RingCentral makeCallWithContact:", phoneNumber, contactName, "state:", JSON.stringify({
                widgetReady: state.widgetReady,
                loggedIn: state.loggedIn,
                initialized: state.initialized,
            }));
            
            // If widget not ready, try to initialize
            if (!state.widgetReady) {
                console.log("RingCentral: Widget not ready, trying to initialize...");
                if (!state.initialized) {
                    initialize();
                }
                notification.add("RingCentral widget is loading. Please try again in a moment.", { type: "warning" });
                return false;
            }
            
            const normalizedNumber = normalizePhoneNumber(phoneNumber);
            if (!normalizedNumber) {
                notification.add("Invalid phone number", { type: "warning" });
                return false;
            }
            
            setCallContext({
                phone_number: normalizedNumber,
                contact_name: contactName,
                ...options,
            });
            
            // Log attempt immediately
            logCallAttempt(normalizedNumber, { ...options, contact_name: contactName });
            
            // 1) Ensure widget is visible and on dialer screen (handles collapsed/minimized cases)
            postToWidget({
                type: "rc-adapter-minimize",
                minimize: false,
            });
            postToWidget({
                type: "rc-adapter-navigate-to",
                path: "/dialer",
                phoneNumber: normalizedNumber,
            });
            
            // 2) Send call command with a slight delay; re-send unminimize right before dialing
            setTimeout(() => {
                postToWidget({
                    type: "rc-adapter-minimize",
                    minimize: false,
                });
                postToWidget({
                    type: "rc-adapter-new-call",
                    phoneNumber: normalizedNumber,
                    // Note: calleeContactName is not standard but some versions support it
                    // If ignored, it just dials the number
                    calleeContactName: contactName,
                    toCall: true,
                });
                console.log("RingCentral: dialing", normalizedNumber, "contact", contactName, "context", callContext);
            }, 350);
            
            return true;
        }
        
        /**
         * Send SMS using the widget
         */
        function sendSMS(phoneNumber, message = "") {
            if (!state.widgetReady) {
                notification.add("RingCentral widget not ready", { type: "warning" });
                return;
            }
            
            postToWidget({
                type: "rc-adapter-new-sms",
                phoneNumber: phoneNumber,
                text: message,
            });
            
            if (state.minimized) {
                toggleWidget();
            }
        }
        
        /**
         * Toggle widget visibility (minimize/expand)
         */
        function toggleWidget() {
            if (!state.widgetReady) return;
            
            postToWidget({
                type: "rc-adapter-minimize",
                minimize: !state.minimized,
            });
        }
        
        /**
         * Show the widget
         */
        function showWidget() {
            // If widget not ready, try to initialize it first
            if (!state.widgetReady) {
                console.log("RingCentral: Widget not ready, attempting to initialize...");
                if (!state.initialized) {
                    initialize();
                }
                return;
            }
            
            postToWidget({
                type: "rc-adapter-minimize",
                minimize: false,
            });
        }
        
        /**
         * Hide the widget
         */
        function hideWidget() {
            if (!state.widgetReady) return;
            
            postToWidget({
                type: "rc-adapter-minimize",
                minimize: true,
            });
        }
        
        /**
         * Open dialer with a phone number
         */
        function openDialer(phoneNumber = "") {
            if (!state.widgetReady) return;
            
            postToWidget({
                type: "rc-adapter-navigate-to",
                path: "/dialer",
                phoneNumber: phoneNumber,
            });
            
            showWidget();
        }
        
        /**
         * Logout from RingCentral
         */
        function logout() {
            if (!state.widgetReady) return;
            
            postToWidget({
                type: "rc-adapter-logout",
            });
        }
        
        /**
         * Cleanup on service destroy
         */
        function cleanup() {
            window.removeEventListener("message", handleWidgetMessage);
        }
        
        // Defer initialization slightly to ensure the session is ready
        // This prevents RPC failures during early page load
        setTimeout(() => {
            console.log("RingCentral: Deferred initialization starting...");
            initialize();
        }, 500);
        
        return {
            state,
            initialize,  // Export for manual re-init
            makeCall,
            makeCallWithContact,
            sendSMS,
            toggleWidget,
            showWidget,
            hideWidget,
            openDialer,
            logout,
            cleanup,
            requestLoginStatus,
            setCallContext,
        };
    },
};

registry.category("services").add("ringcentral_embeddable", ringcentralEmbeddableService);
/**
 * RingCentral Embeddable Toggle Button Component
 * 
 * A simple systray button to toggle the RingCentral widget
 */
export class RingCentralEmbeddableToggle extends Component {
    static template = "ringcentral_webrtc.EmbeddableToggle";
    
    setup() {
        this.rcService = useService("ringcentral_embeddable");
        this.notification = useService("notification");
        this.state = useState({});
        
        // Check widget status on mount and periodically
        onMounted(() => {
            this.checkWidgetStatus();
            // Check every 5 seconds
            this.statusInterval = setInterval(() => this.checkWidgetStatus(), 5000);
        });
        
        onWillDestroy(() => {
            if (this.statusInterval) {
                clearInterval(this.statusInterval);
            }
        });
    }
    
    /**
     * Check if widget iframe exists and update state accordingly
     */
    checkWidgetStatus() {
        const iframe = document.querySelector('iframe#rc-widget-adapter-frame') ||
                       document.querySelector('iframe[src*="ringcentral-embeddable"]');
        
        if (iframe && !this.rcService.state.widgetReady) {
            console.log("RingCentral Systray: Widget iframe found but state not synced, requesting status...");
            this.rcService.state.widgetReady = true;
            this.rcService.state.initialized = true;
            this.rcService.requestLoginStatus();
        }
    }
    
    get rcState() {
        return this.rcService.state;
    }
    
    onToggle() {
        if (!this.rcService.state.widgetReady) {
            this.notification.add("RingCentral widget is not connected. Click 'Reconnect' to try again.", { 
                type: "warning",
                title: "Phone Not Ready"
            });
            return;
        }
        this.rcService.toggleWidget();
    }
    
    onDialerClick() {
        if (!this.rcService.state.widgetReady) {
            this.notification.add("RingCentral widget is not connected. Click 'Reconnect' to try again.", { 
                type: "warning",
                title: "Phone Not Ready"
            });
            return;
        }
        this.rcService.openDialer();
    }
    
    onReconnect() {
        this.notification.add("Attempting to reconnect to RingCentral...", { 
            type: "info",
            title: "Reconnecting"
        });
        this.rcService.initialize();
    }
}

RingCentralEmbeddableToggle.props = {};

// Register in systray
export const ringcentralEmbeddableSystrayItem = {
    Component: RingCentralEmbeddableToggle,
    isDisplayed: (env) => true,
};

registry.category("systray").add("RingCentralEmbeddableToggle", ringcentralEmbeddableSystrayItem, { sequence: 2 });

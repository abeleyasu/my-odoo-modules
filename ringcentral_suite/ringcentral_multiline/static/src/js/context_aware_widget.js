/** @odoo-module **/
/**
 * RingCentral Context-Aware Widget Integration
 * =============================================
 * 
 * This module enhances the RingCentral Embeddable widget with context awareness.
 * It automatically selects the appropriate caller ID based on the current Odoo app.
 * 
 * Industry Standard Implementation:
 * - Uses RingCentral Embeddable postMessage API
 * - Detects current Odoo app from URL/action
 * - Fetches contextual config from backend
 * - Updates widget fromNumber dynamically
 */

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * RingCentral Context Manager
 * 
 * Manages context-aware phone number selection for the RC widget.
 */
class RingCentralContextManager {
    constructor(rpc, notification) {
        this.rpc = rpc;
        this.notification = notification;
        this.currentAppType = 'general';
        this.currentFromNumber = null;
        this.availableNumbers = [];
        this.initialized = false;
        this.widgetFrame = null;
    }
    
    /**
     * Initialize the context manager
     */
    async init() {
        if (this.initialized) return;
        
        // Find the RingCentral widget iframe
        this.widgetFrame = document.querySelector('#rc-widget-adapter-frame') ||
                          document.querySelector('iframe[src*="ringcentral"]');
        
        if (!this.widgetFrame) {
            console.log('[RC MultiLine] Widget iframe not found, will retry...');
            setTimeout(() => this.init(), 2000);
            return;
        }
        
        // Listen for navigation events to update context
        this._setupNavigationListener();
        
        // Listen for messages from the widget
        window.addEventListener('message', this._handleWidgetMessage.bind(this));
        
        // Initial context update
        await this.updateContext();
        
        this.initialized = true;
        console.log('[RC MultiLine] Context manager initialized');
    }
    
    /**
     * Setup listener for Odoo navigation changes
     */
    _setupNavigationListener() {
        // Listen for hash changes (Odoo navigation)
        window.addEventListener('hashchange', () => {
            this.updateContext();
        });
        
        // Also listen for pushState/popState (modern navigation)
        const originalPushState = history.pushState;
        history.pushState = (...args) => {
            originalPushState.apply(history, args);
            setTimeout(() => this.updateContext(), 100);
        };
        
        window.addEventListener('popstate', () => {
            this.updateContext();
        });
    }
    
    /**
     * Detect the current app type from the URL/DOM
     */
    _detectAppType() {
        const hash = window.location.hash.toLowerCase();
        const pathname = window.location.pathname.toLowerCase();
        
        // Check for specific app patterns
        if (hash.includes('crm') || hash.includes('lead') || hash.includes('opportunity')) {
            return 'crm';
        }
        if (hash.includes('sale') || hash.includes('quotation')) {
            return 'sale';
        }
        if (hash.includes('purchase')) {
            return 'purchase';
        }
        if (hash.includes('hr.') || hash.includes('employee') || hash.includes('recruitment') || hash.includes('applicant')) {
            return 'hr';
        }
        if (hash.includes('helpdesk') || hash.includes('ticket')) {
            return 'helpdesk';
        }
        if (hash.includes('project') || hash.includes('task')) {
            return 'project';
        }
        if (hash.includes('account') || hash.includes('invoice')) {
            return 'account';
        }
        if (hash.includes('calendar')) {
            return 'calendar';
        }
        if (hash.includes('contact') || hash.includes('partner')) {
            return 'contacts';
        }
        
        // Try to get model from URL params
        const modelMatch = hash.match(/model=([^&]+)/);
        if (modelMatch) {
            const model = modelMatch[1].toLowerCase();
            if (model.startsWith('crm.')) return 'crm';
            if (model.startsWith('sale.')) return 'sale';
            if (model.startsWith('purchase.')) return 'purchase';
            if (model.startsWith('hr.')) return 'hr';
            if (model.startsWith('helpdesk.')) return 'helpdesk';
            if (model.startsWith('project.')) return 'project';
            if (model.startsWith('account.')) return 'account';
        }
        
        return 'general';
    }
    
    /**
     * Update context and fetch appropriate caller ID
     */
    async updateContext() {
        const newAppType = this._detectAppType();
        
        // Only update if app type changed
        if (newAppType === this.currentAppType && this.currentFromNumber) {
            return;
        }
        
        this.currentAppType = newAppType;
        console.log(`[RC MultiLine] App context changed to: ${newAppType}`);
        
        try {
            // Get model and action from URL if available
            const hash = window.location.hash;
            const modelMatch = hash.match(/model=([^&]+)/);
            const actionMatch = hash.match(/action=(\d+)/);
            const idMatch = hash.match(/id=(\d+)/);
            
            const config = await this.rpc('/ringcentral/widget/contextual-config', {
                model: modelMatch ? modelMatch[1] : null,
                action_id: actionMatch ? actionMatch[1] : null,
                record_id: idMatch ? idMatch[1] : null,
                referrer: window.location.href,
            });
            
            if (config.success && config.config) {
                this.currentFromNumber = config.config.fromNumber;
                this.availableNumbers = config.config.availableNumbers || [];
                
                // Update the widget
                this._updateWidget(config.config);
                
                console.log(`[RC MultiLine] Updated from number to: ${this.currentFromNumber} (source: ${config.config.source})`);
            }
        } catch (error) {
            console.error('[RC MultiLine] Failed to get contextual config:', error);
        }
    }
    
    /**
     * Send configuration to the RingCentral widget
     */
    _updateWidget(config) {
        if (!this.widgetFrame || !this.widgetFrame.contentWindow) {
            console.warn('[RC MultiLine] Widget frame not available');
            return;
        }
        
        // Use RingCentral Embeddable postMessage API
        // Reference: https://ringcentral.github.io/ringcentral-embeddable/docs/widget-event-based-api
        
        if (config.fromNumber) {
            // Update calling settings with new from number
            this.widgetFrame.contentWindow.postMessage({
                type: 'rc-calling-settings-update',
                callWith: 'browser', // or 'softphone', 'jupiter'
                fromNumber: config.fromNumber,
            }, '*');
            
            console.log(`[RC MultiLine] Sent fromNumber update: ${config.fromNumber}`);
        }
        
        // Enable/disable from number selection in widget
        if (typeof config.enableFromNumberSetting !== 'undefined') {
            // This would require widget reinitialization or adapter support
            // Store for when widget reinitializes
            window.RCMultiLineConfig = window.RCMultiLineConfig || {};
            window.RCMultiLineConfig.enableFromNumberSetting = config.enableFromNumberSetting ? 1 : 0;
        }
    }
    
    /**
     * Handle messages from the RingCentral widget
     */
    _handleWidgetMessage(event) {
        if (!event.data || !event.data.type) return;
        
        // Handle various widget events
        switch (event.data.type) {
            case 'rc-call-ring-event':
            case 'rc-call-start-event':
                // Call starting - could log the from number used
                console.log('[RC MultiLine] Call event:', event.data.type, event.data.call);
                break;
                
            case 'rc-calling-settings-updated':
                // Widget settings were updated
                console.log('[RC MultiLine] Widget settings updated:', event.data);
                break;
                
            case 'rc-login-status':
                // User logged in/out - refresh context
                if (event.data.loginStatus === 'logged-in') {
                    setTimeout(() => this.updateContext(), 1000);
                }
                break;
                
            case 'rc-adapter-init':
                // Widget initialized - apply our settings
                console.log('[RC MultiLine] Widget adapter initialized');
                setTimeout(() => this.updateContext(), 500);
                break;
        }
    }
    
    /**
     * Manually set the caller ID (for user selection)
     */
    async setFromNumber(phoneNumber) {
        try {
            const result = await this.rpc('/ringcentral/widget/update-caller-id', {
                phone_number: phoneNumber,
            });
            
            if (result.success) {
                this.currentFromNumber = phoneNumber;
                this._updateWidget({ fromNumber: phoneNumber });
                
                this.notification.add(`Caller ID updated to ${result.formattedNumber || phoneNumber}`, {
                    type: 'success',
                    sticky: false,
                });
            } else {
                this.notification.add(`Failed to update caller ID: ${result.error}`, {
                    type: 'warning',
                    sticky: false,
                });
            }
        } catch (error) {
            console.error('[RC MultiLine] Failed to set from number:', error);
        }
    }
    
    /**
     * Get current configuration
     */
    getConfig() {
        return {
            appType: this.currentAppType,
            fromNumber: this.currentFromNumber,
            availableNumbers: this.availableNumbers,
        };
    }
}

/**
 * OWL Component for context-aware caller ID display/selection
 */
export class RingCentralCallerIdWidget extends Component {
    static template = "ringcentral_multiline.CallerIdWidget";
    static props = {};
    
    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        
        this.state = useState({
            currentNumber: null,
            formattedNumber: null,
            availableNumbers: [],
            showDropdown: false,
            appType: 'general',
        });
        
        onMounted(() => {
            this.initContextManager();
        });
        
        onWillUnmount(() => {
            // Cleanup if needed
        });
    }
    
    async initContextManager() {
        // Initialize or get existing context manager
        if (!window.rcContextManager) {
            window.rcContextManager = new RingCentralContextManager(this.rpc, this.notification);
            await window.rcContextManager.init();
        }
        
        // Update state from manager
        this.updateState();
        
        // Listen for updates
        setInterval(() => this.updateState(), 5000);
    }
    
    updateState() {
        if (window.rcContextManager) {
            const config = window.rcContextManager.getConfig();
            this.state.currentNumber = config.fromNumber;
            this.state.availableNumbers = config.availableNumbers;
            this.state.appType = config.appType;
        }
    }
    
    toggleDropdown() {
        this.state.showDropdown = !this.state.showDropdown;
    }
    
    async selectNumber(number) {
        if (window.rcContextManager) {
            await window.rcContextManager.setFromNumber(number.phoneNumber);
            this.state.currentNumber = number.phoneNumber;
            this.state.formattedNumber = number.formattedNumber;
        }
        this.state.showDropdown = false;
    }
}

/**
 * Auto-initialize context manager when page loads
 */
document.addEventListener('DOMContentLoaded', () => {
    // Wait for Odoo and widget to be ready
    setTimeout(() => {
        const rpcService = odoo.__DEBUG__?.services?.['web.rpc'] || null;
        if (rpcService) {
            // Create a simple RPC wrapper if services are available
            window.rcContextManager = new RingCentralContextManager(
                (route, params) => fetch(route, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params, id: 1 }),
                }).then(r => r.json()).then(r => r.result),
                { add: (msg, opts) => console.log(`[Notification] ${msg}`) }
            );
            window.rcContextManager.init();
        }
    }, 3000);
});

// Register the widget component
// registry.category("systray").add("RingCentralCallerId", {
//     Component: RingCentralCallerIdWidget,
// });

export { RingCentralContextManager };

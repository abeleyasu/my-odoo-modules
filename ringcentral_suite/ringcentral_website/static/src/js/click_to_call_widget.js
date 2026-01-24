/**
 * RingCentral Click-to-Call Website Widget
 */
(function() {
    'use strict';
    
    document.addEventListener('DOMContentLoaded', async function() {
        // Load widget configuration
        const config = await loadConfig();
        
        if (!config.enabled) {
            return;
        }
        
        // Create widget
        createWidget(config);
    });
    
    async function loadConfig() {
        try {
            const response = await fetch('/ringcentral/widget/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({}),
            });
            const result = await response.json();
            return result.result || {};
        } catch (error) {
            console.error('Failed to load widget config:', error);
            return { enabled: false };
        }
    }
    
    function createWidget(config) {
        const widget = document.createElement('div');
        widget.id = 'rc-click-to-call-widget';
        widget.className = 'rc-widget rc-widget-' + config.position;
        widget.style.setProperty('--rc-widget-color', config.color);
        
        widget.innerHTML = `
            <div class="rc-widget-button" onclick="toggleRCWidget()">
                <i class="fa fa-phone"></i>
            </div>
            <div class="rc-widget-popup" id="rc-widget-popup">
                <div class="rc-widget-header">
                    <span>Contact Us</span>
                    <button class="rc-widget-close" onclick="toggleRCWidget()">&times;</button>
                </div>
                <div class="rc-widget-body">
                    ${config.show_phone && config.phone_number ? `
                    <div class="rc-widget-phone">
                        <i class="fa fa-phone"></i>
                        <a href="tel:${config.phone_number}">${config.phone_number}</a>
                    </div>
                    ` : ''}
                    ${config.callback_enabled ? `
                    <div class="rc-widget-callback">
                        <a href="/ringcentral/callback" class="rc-widget-callback-btn">
                            <i class="fa fa-phone-square"></i>
                            Request a Callback
                        </a>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
        
        document.body.appendChild(widget);
    }
    
    // Global toggle function
    window.toggleRCWidget = function() {
        const popup = document.getElementById('rc-widget-popup');
        if (popup) {
            popup.classList.toggle('active');
        }
    };
    
    // Handle callback form submission
    document.addEventListener('submit', async function(e) {
        if (e.target.id === 'rc_callback_form') {
            e.preventDefault();
            
            const form = e.target;
            const submitBtn = form.querySelector('button[type="submit"]');
            const successDiv = document.getElementById('callback_success');
            const errorDiv = document.getElementById('callback_error');
            
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Submitting...';
            
            try {
                const formData = new FormData(form);
                const data = {};
                formData.forEach((value, key) => data[key] = value);
                data.source_url = window.location.href;
                
                const response = await fetch('/ringcentral/callback/request', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: data,
                    }),
                });
                
                const result = await response.json();
                
                if (result.result && result.result.success) {
                    form.classList.add('d-none');
                    successDiv.classList.remove('d-none');
                    errorDiv.classList.add('d-none');
                } else {
                    throw new Error(result.result?.message || 'Unknown error');
                }
            } catch (error) {
                errorDiv.classList.remove('d-none');
                document.getElementById('callback_error_message').textContent = error.message;
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fa fa-phone me-2"></i>Request Callback';
            }
        }
    });
})();

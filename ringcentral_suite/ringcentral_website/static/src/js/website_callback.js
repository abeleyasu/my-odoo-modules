/** @odoo-module */

document.addEventListener('DOMContentLoaded', function() {
    const widget = document.getElementById('rc-callback-widget');
    if (!widget) return;
    
    const toggle = widget.querySelector('.rc-callback-toggle');
    const form = widget.querySelector('.rc-callback-form');
    const formEl = widget.querySelector('#rc-callback-form');
    const success = widget.querySelector('.rc-callback-success');
    
    // Toggle form visibility
    toggle.addEventListener('click', function() {
        if (form.style.display === 'none') {
            form.style.display = 'block';
            toggle.style.display = 'none';
        } else {
            form.style.display = 'none';
            toggle.style.display = 'block';
        }
    });
    
    // Handle form submission
    if (formEl) {
        formEl.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(formEl);
            const data = Object.fromEntries(formData.entries());
            data.source_url = window.location.href;
            
            try {
                const response = await fetch('/ringcentral/callback/request', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: data,
                        id: Math.floor(Math.random() * 1000000000),
                    }),
                });
                
                const result = await response.json();
                
                if (result.result && result.result.success) {
                    formEl.style.display = 'none';
                    success.style.display = 'block';
                    
                    // Hide after 5 seconds
                    setTimeout(() => {
                        form.style.display = 'none';
                        toggle.style.display = 'block';
                        formEl.style.display = 'block';
                        success.style.display = 'none';
                        formEl.reset();
                    }, 5000);
                } else {
                    alert(result.result?.message || 'Something went wrong. Please try again.');
                }
            } catch (error) {
                console.error('Callback request error:', error);
                alert('Something went wrong. Please try again.');
            }
        });
    }
});

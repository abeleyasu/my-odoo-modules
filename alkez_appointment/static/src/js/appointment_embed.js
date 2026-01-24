/**
 * Appointment Embed Script
 * External JavaScript for embedding appointment widgets on third-party websites
 * Similar to Calendly's embed functionality
 */

(function() {
    'use strict';

    // Configuration
    const WIDGET_STYLES = `
        .appointment-embed-inline {
            min-height: 580px;
            width: 100%;
        }
        .appointment-embed-inline iframe {
            width: 100%;
            height: 100%;
            min-height: 580px;
            border: none;
        }
        .appointment-embed-popup-button {
            display: inline-flex;
            align-items: center;
            padding: 14px 28px;
            background: #0069ff;
            color: #ffffff;
            border: none;
            border-radius: 40px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            box-shadow: 0 4px 16px rgba(0, 105, 255, 0.35);
            transition: all 0.2s ease;
        }
        .appointment-embed-popup-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 105, 255, 0.4);
        }
        .appointment-embed-popup-button svg {
            margin-right: 8px;
        }
        .appointment-embed-modal {
            position: fixed;
            inset: 0;
            z-index: 999999;
            display: flex;
            align-items: center;
            justify-content: center;
            visibility: hidden;
            opacity: 0;
            transition: all 0.3s ease;
        }
        .appointment-embed-modal.active {
            visibility: visible;
            opacity: 1;
        }
        .appointment-embed-modal-overlay {
            position: absolute;
            inset: 0;
            background: rgba(0, 0, 0, 0.5);
        }
        .appointment-embed-modal-content {
            position: relative;
            background: #ffffff;
            border-radius: 12px;
            max-width: 1000px;
            width: 95%;
            max-height: 90vh;
            overflow: hidden;
            transform: translateY(20px);
            transition: transform 0.3s ease;
        }
        .appointment-embed-modal.active .appointment-embed-modal-content {
            transform: translateY(0);
        }
        .appointment-embed-modal-close {
            position: absolute;
            top: 16px;
            right: 16px;
            width: 36px;
            height: 36px;
            border: none;
            border-radius: 50%;
            background: rgba(0, 0, 0, 0.05);
            color: #666;
            font-size: 24px;
            cursor: pointer;
            z-index: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }
        .appointment-embed-modal-close:hover {
            background: rgba(0, 0, 0, 0.1);
            color: #333;
        }
        .appointment-embed-modal iframe {
            width: 100%;
            height: 80vh;
            border: none;
        }
        .appointment-embed-text-link {
            color: #0069ff;
            text-decoration: none;
            font-weight: 500;
            cursor: pointer;
        }
        .appointment-embed-text-link:hover {
            text-decoration: underline;
        }
    `;

    // Inject styles
    function injectStyles() {
        if (document.getElementById('appointment-embed-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'appointment-embed-styles';
        style.textContent = WIDGET_STYLES;
        document.head.appendChild(style);
    }

    // Create modal
    function createModal(url) {
        let modal = document.getElementById('appointment-embed-modal');
        if (modal) {
            modal.querySelector('iframe').src = url + '?embed=1';
            return modal;
        }

        modal = document.createElement('div');
        modal.id = 'appointment-embed-modal';
        modal.className = 'appointment-embed-modal';
        modal.innerHTML = `
            <div class="appointment-embed-modal-overlay"></div>
            <div class="appointment-embed-modal-content">
                <button class="appointment-embed-modal-close">&times;</button>
                <iframe src="${url}?embed=1" loading="lazy"></iframe>
            </div>
        `;
        document.body.appendChild(modal);

        // Event listeners
        modal.querySelector('.appointment-embed-modal-overlay').addEventListener('click', closeModal);
        modal.querySelector('.appointment-embed-modal-close').addEventListener('click', closeModal);
        
        // Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') closeModal();
        });

        return modal;
    }

    function openModal(url) {
        const modal = createModal(url);
        requestAnimationFrame(() => {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        });
    }

    function closeModal() {
        const modal = document.getElementById('appointment-embed-modal');
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    // Initialize inline widgets
    function initInlineWidgets() {
        const containers = document.querySelectorAll('.appointment-inline-widget:not([data-initialized])');
        containers.forEach(container => {
            const url = container.dataset.url;
            if (url) {
                const iframe = document.createElement('iframe');
                iframe.src = url + '?embed=1';
                iframe.loading = 'lazy';
                container.appendChild(iframe);
                container.classList.add('appointment-embed-inline');
                container.setAttribute('data-initialized', 'true');
            }
        });
    }

    // Initialize popup buttons
    function initPopupButtons() {
        const buttons = document.querySelectorAll('.appointment-popup-widget:not([data-initialized])');
        buttons.forEach(container => {
            const url = container.dataset.url;
            const text = container.dataset.text || 'Schedule time with me';
            const color = container.dataset.color || '#0069ff';
            const textColor = container.dataset.textColor || '#ffffff';
            
            const button = document.createElement('button');
            button.className = 'appointment-embed-popup-button';
            button.style.background = color;
            button.style.color = textColor;
            button.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                    <line x1="16" y1="2" x2="16" y2="6"></line>
                    <line x1="8" y1="2" x2="8" y2="6"></line>
                    <line x1="3" y1="10" x2="21" y2="10"></line>
                </svg>
                ${text}
            `;
            button.addEventListener('click', () => openModal(url));
            
            container.appendChild(button);
            container.setAttribute('data-initialized', 'true');
        });
    }

    // Initialize text links
    function initTextLinks() {
        const links = document.querySelectorAll('.appointment-popup-text:not([data-initialized])');
        links.forEach(container => {
            const url = container.dataset.url;
            const text = container.dataset.text || 'Schedule a meeting';
            
            const link = document.createElement('a');
            link.className = 'appointment-embed-text-link';
            link.href = '#';
            link.textContent = text;
            link.addEventListener('click', (e) => {
                e.preventDefault();
                openModal(url);
            });
            
            container.appendChild(link);
            container.setAttribute('data-initialized', 'true');
        });
    }

    // Initialize all widgets
    function initWidgets() {
        injectStyles();
        initInlineWidgets();
        initPopupButtons();
        initTextLinks();
    }

    // Public API
    window.Appointment = {
        initInlineWidget: function(element, url, options = {}) {
            element.dataset.url = url;
            element.classList.add('appointment-inline-widget');
            initInlineWidgets();
        },

        initPopupWidget: function(element, url, options = {}) {
            element.dataset.url = url;
            element.dataset.text = options.text || 'Schedule time with me';
            element.dataset.color = options.color || '#0069ff';
            element.dataset.textColor = options.textColor || '#ffffff';
            element.classList.add('appointment-popup-widget');
            initPopupButtons();
        },

        initPopupText: function(element, url, options = {}) {
            element.dataset.url = url;
            element.dataset.text = options.text || 'Schedule a meeting';
            element.classList.add('appointment-popup-text');
            initTextLinks();
        },

        openPopup: function(url) {
            injectStyles();
            openModal(url);
        },

        closePopup: function() {
            closeModal();
        },
    };

    // Auto-initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWidgets);
    } else {
        initWidgets();
    }

    // Re-initialize on dynamic content
    const observer = new MutationObserver(function(mutations) {
        let shouldInit = false;
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length) {
                shouldInit = true;
            }
        });
        if (shouldInit) {
            initWidgets();
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });

})();

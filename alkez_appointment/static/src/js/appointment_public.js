/**
 * Calendly Clone - Appointment Booking JavaScript
 * Handles calendar rendering, time slot selection, and form submission
 */

(function() {
    'use strict';

    // Main initialization - runs when DOM is ready or immediately if already loaded
    function initCalendar() {
        // Find the booking wrapper
        const wrapper = document.querySelector('.calendly-booking-wrapper');
        if (!wrapper) {
            return;
        }

        // Check if already initialized
        if (wrapper.dataset.initialized === 'true') {
            return;
        }
        wrapper.dataset.initialized = 'true';

        console.log('[Appointment] Initializing calendar...');

        // Initialize the booking calendar
        const calendar = new AppointmentCalendar();
        calendar.init();
    }

    // Main Calendar Class
    function AppointmentCalendar() {
        this.config = window.appointmentConfig || {};
        this.currentDate = new Date();
        this.selectedDate = null;
        this.selectedSlot = null;
        this.availableSlots = {};
        this.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
        
        // Calculate min/max dates
        var minDays = Math.ceil((this.config.minScheduleNotice || 4) / 24);
        this.minDate = new Date();
        this.minDate.setDate(this.minDate.getDate() + minDays);
        this.minDate.setHours(0, 0, 0, 0);
        
        this.maxDate = new Date();
        this.maxDate.setDate(this.maxDate.getDate() + (this.config.maxScheduleDays || 60));
    }

    AppointmentCalendar.prototype.init = function() {
        console.log('[Appointment] Config:', this.config);
        
        // Bind events
        this.bindEvents();
        
        // Update timezone display
        this.updateTimezoneDisplay();
        
        // Render initial calendar
        this.renderCalendar();
        
        // Fetch available slots
        this.fetchSlots();
    };

    AppointmentCalendar.prototype.bindEvents = function() {
        var self = this;
        
        // Month navigation
        var prevBtn = document.getElementById('prev-month');
        var nextBtn = document.getElementById('next-month');
        if (prevBtn) {
            prevBtn.onclick = function(e) { 
                e.preventDefault();
                self.onPrevMonth(); 
            };
        }
        if (nextBtn) {
            nextBtn.onclick = function(e) { 
                e.preventDefault();
                self.onNextMonth(); 
            };
        }
        
        // Back to calendar
        var backBtn = document.getElementById('back-to-calendar');
        if (backBtn) {
            backBtn.onclick = function(e) { 
                e.preventDefault();
                self.onBackToCalendar(); 
            };
        }
        
        // Add guests
        var addGuestsBtn = document.getElementById('add-guests-btn');
        if (addGuestsBtn) {
            addGuestsBtn.onclick = function(e) { 
                e.preventDefault();
                self.onAddGuests(); 
            };
        }
        
        // Form submission
        var form = document.getElementById('booking-form');
        if (form) {
            form.onsubmit = function(e) { self.onFormSubmit(e); };
        }
        
        // Timezone selector
        this.initTimezoneSelector();
    };

    AppointmentCalendar.prototype.initTimezoneSelector = function() {
        var self = this;
        var trigger = document.getElementById('timezone-selector-trigger');
        var modal = document.getElementById('timezone-modal');
        var closeBtn = document.getElementById('timezone-close-btn');
        var searchInput = document.getElementById('timezone-search');
        var listContainer = document.getElementById('timezone-list');
        
        if (!trigger || !modal || !listContainer) {
            console.log('[Appointment] Timezone selector elements not found');
            return;
        }
        
        // Populate timezone list
        this.populateTimezoneList('');
        
        // Open modal
        trigger.onclick = function(e) {
            e.preventDefault();
            modal.style.display = 'flex';
            if (searchInput) {
                searchInput.value = '';
                searchInput.focus();
            }
            self.populateTimezoneList('');
        };
        
        // Close modal
        if (closeBtn) {
            closeBtn.onclick = function(e) {
                e.preventDefault();
                modal.style.display = 'none';
            };
        }
        
        // Close on backdrop click
        modal.onclick = function(e) {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        };
        
        // Search functionality
        if (searchInput) {
            searchInput.oninput = function() {
                self.populateTimezoneList(searchInput.value);
            };
        }
        
        // Close on Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && modal.style.display === 'flex') {
                modal.style.display = 'none';
            }
        });
    };

    AppointmentCalendar.prototype.populateTimezoneList = function(filter) {
        var self = this;
        var listContainer = document.getElementById('timezone-list');
        var modal = document.getElementById('timezone-modal');
        
        if (!listContainer) return;
        
        var allTimezones = this.getAllTimezones();
        var filteredTimezones = allTimezones;
        
        // Filter by search term
        if (filter && filter.trim()) {
            var searchTerm = filter.toLowerCase().trim();
            filteredTimezones = allTimezones.filter(function(tz) {
                return tz.label.toLowerCase().indexOf(searchTerm) !== -1 ||
                       tz.value.toLowerCase().indexOf(searchTerm) !== -1 ||
                       tz.region.toLowerCase().indexOf(searchTerm) !== -1;
            });
        }
        
        // Group by region
        var grouped = {};
        filteredTimezones.forEach(function(tz) {
            if (!grouped[tz.region]) {
                grouped[tz.region] = [];
            }
            grouped[tz.region].push(tz);
        });
        
        // Build HTML
        var html = '';
        var regions = Object.keys(grouped).sort();
        
        regions.forEach(function(region) {
            html += '<div class="timezone-region">';
            html += '<div class="timezone-region-header">' + region + '</div>';
            
            grouped[region].forEach(function(tz) {
                var isSelected = tz.value === self.timezone;
                var offset = self.getTimezoneOffset(tz.value);
                html += '<div class="timezone-option' + (isSelected ? ' selected' : '') + '" data-value="' + tz.value + '">';
                html += '<span class="timezone-option-label">' + tz.label + '</span>';
                html += '<span class="timezone-option-offset">' + offset + '</span>';
                if (isSelected) {
                    html += '<i class="fa fa-check timezone-check"></i>';
                }
                html += '</div>';
            });
            
            html += '</div>';
        });
        
        if (filteredTimezones.length === 0) {
            html = '<div class="timezone-no-results">No time zones found matching "' + filter + '"</div>';
        }
        
        listContainer.innerHTML = html;
        
        // Add click handlers
        var options = listContainer.querySelectorAll('.timezone-option');
        options.forEach(function(option) {
            option.onclick = function() {
                var value = option.getAttribute('data-value');
                self.timezone = value;
                self.updateTimezoneDisplay();
                self.fetchSlots(); // Refresh slots for new timezone
                if (modal) {
                    modal.style.display = 'none';
                }
            };
        });
    };

    AppointmentCalendar.prototype.getTimezoneOffset = function(tz) {
        try {
            var now = new Date();
            var options = { timeZone: tz, timeZoneName: 'shortOffset' };
            var formatter = new Intl.DateTimeFormat('en-US', options);
            var parts = formatter.formatToParts(now);
            var offsetPart = parts.find(function(p) { return p.type === 'timeZoneName'; });
            if (offsetPart) {
                return offsetPart.value;
            }
            // Fallback: calculate offset manually
            var utcDate = new Date(now.toLocaleString('en-US', { timeZone: 'UTC' }));
            var tzDate = new Date(now.toLocaleString('en-US', { timeZone: tz }));
            var diff = (tzDate - utcDate) / 60000; // minutes
            var hours = Math.floor(Math.abs(diff) / 60);
            var minutes = Math.abs(diff) % 60;
            var sign = diff >= 0 ? '+' : '-';
            return 'GMT' + sign + String(hours).padStart(2, '0') + ':' + String(minutes).padStart(2, '0');
        } catch(e) {
            return '';
        }
    };

    AppointmentCalendar.prototype.updateTimezoneDisplay = function() {
        var tzEl = document.getElementById('current-timezone');
        if (tzEl) {
            tzEl.textContent = this.getTimezoneName(this.timezone);
        }
    };

    // Complete list of all IANA timezones grouped by region
    AppointmentCalendar.prototype.getAllTimezones = function() {
        return [
            // UTC
            { value: 'UTC', label: 'UTC', region: 'UTC' },
            
            // Africa
            { value: 'Africa/Abidjan', label: 'Abidjan', region: 'Africa' },
            { value: 'Africa/Accra', label: 'Accra', region: 'Africa' },
            { value: 'Africa/Addis_Ababa', label: 'Addis Ababa', region: 'Africa' },
            { value: 'Africa/Algiers', label: 'Algiers', region: 'Africa' },
            { value: 'Africa/Asmara', label: 'Asmara', region: 'Africa' },
            { value: 'Africa/Bamako', label: 'Bamako', region: 'Africa' },
            { value: 'Africa/Bangui', label: 'Bangui', region: 'Africa' },
            { value: 'Africa/Banjul', label: 'Banjul', region: 'Africa' },
            { value: 'Africa/Bissau', label: 'Bissau', region: 'Africa' },
            { value: 'Africa/Blantyre', label: 'Blantyre', region: 'Africa' },
            { value: 'Africa/Brazzaville', label: 'Brazzaville', region: 'Africa' },
            { value: 'Africa/Bujumbura', label: 'Bujumbura', region: 'Africa' },
            { value: 'Africa/Cairo', label: 'Cairo', region: 'Africa' },
            { value: 'Africa/Casablanca', label: 'Casablanca', region: 'Africa' },
            { value: 'Africa/Ceuta', label: 'Ceuta', region: 'Africa' },
            { value: 'Africa/Conakry', label: 'Conakry', region: 'Africa' },
            { value: 'Africa/Dakar', label: 'Dakar', region: 'Africa' },
            { value: 'Africa/Dar_es_Salaam', label: 'Dar es Salaam', region: 'Africa' },
            { value: 'Africa/Djibouti', label: 'Djibouti', region: 'Africa' },
            { value: 'Africa/Douala', label: 'Douala', region: 'Africa' },
            { value: 'Africa/El_Aaiun', label: 'El Aaiun', region: 'Africa' },
            { value: 'Africa/Freetown', label: 'Freetown', region: 'Africa' },
            { value: 'Africa/Gaborone', label: 'Gaborone', region: 'Africa' },
            { value: 'Africa/Harare', label: 'Harare', region: 'Africa' },
            { value: 'Africa/Johannesburg', label: 'Johannesburg', region: 'Africa' },
            { value: 'Africa/Juba', label: 'Juba', region: 'Africa' },
            { value: 'Africa/Kampala', label: 'Kampala', region: 'Africa' },
            { value: 'Africa/Khartoum', label: 'Khartoum', region: 'Africa' },
            { value: 'Africa/Kigali', label: 'Kigali', region: 'Africa' },
            { value: 'Africa/Kinshasa', label: 'Kinshasa', region: 'Africa' },
            { value: 'Africa/Lagos', label: 'Lagos', region: 'Africa' },
            { value: 'Africa/Libreville', label: 'Libreville', region: 'Africa' },
            { value: 'Africa/Lome', label: 'Lome', region: 'Africa' },
            { value: 'Africa/Luanda', label: 'Luanda', region: 'Africa' },
            { value: 'Africa/Lubumbashi', label: 'Lubumbashi', region: 'Africa' },
            { value: 'Africa/Lusaka', label: 'Lusaka', region: 'Africa' },
            { value: 'Africa/Malabo', label: 'Malabo', region: 'Africa' },
            { value: 'Africa/Maputo', label: 'Maputo', region: 'Africa' },
            { value: 'Africa/Maseru', label: 'Maseru', region: 'Africa' },
            { value: 'Africa/Mbabane', label: 'Mbabane', region: 'Africa' },
            { value: 'Africa/Mogadishu', label: 'Mogadishu', region: 'Africa' },
            { value: 'Africa/Monrovia', label: 'Monrovia', region: 'Africa' },
            { value: 'Africa/Nairobi', label: 'Nairobi', region: 'Africa' },
            { value: 'Africa/Ndjamena', label: 'Ndjamena', region: 'Africa' },
            { value: 'Africa/Niamey', label: 'Niamey', region: 'Africa' },
            { value: 'Africa/Nouakchott', label: 'Nouakchott', region: 'Africa' },
            { value: 'Africa/Ouagadougou', label: 'Ouagadougou', region: 'Africa' },
            { value: 'Africa/Porto-Novo', label: 'Porto-Novo', region: 'Africa' },
            { value: 'Africa/Sao_Tome', label: 'Sao Tome', region: 'Africa' },
            { value: 'Africa/Tripoli', label: 'Tripoli', region: 'Africa' },
            { value: 'Africa/Tunis', label: 'Tunis', region: 'Africa' },
            { value: 'Africa/Windhoek', label: 'Windhoek', region: 'Africa' },
            
            // America
            { value: 'America/Adak', label: 'Adak', region: 'America' },
            { value: 'America/Anchorage', label: 'Anchorage', region: 'America' },
            { value: 'America/Anguilla', label: 'Anguilla', region: 'America' },
            { value: 'America/Antigua', label: 'Antigua', region: 'America' },
            { value: 'America/Araguaina', label: 'Araguaina', region: 'America' },
            { value: 'America/Argentina/Buenos_Aires', label: 'Buenos Aires', region: 'America' },
            { value: 'America/Argentina/Catamarca', label: 'Catamarca', region: 'America' },
            { value: 'America/Argentina/Cordoba', label: 'Cordoba', region: 'America' },
            { value: 'America/Argentina/Jujuy', label: 'Jujuy', region: 'America' },
            { value: 'America/Argentina/La_Rioja', label: 'La Rioja', region: 'America' },
            { value: 'America/Argentina/Mendoza', label: 'Mendoza', region: 'America' },
            { value: 'America/Argentina/Rio_Gallegos', label: 'Rio Gallegos', region: 'America' },
            { value: 'America/Argentina/Salta', label: 'Salta', region: 'America' },
            { value: 'America/Argentina/San_Juan', label: 'San Juan', region: 'America' },
            { value: 'America/Argentina/San_Luis', label: 'San Luis', region: 'America' },
            { value: 'America/Argentina/Tucuman', label: 'Tucuman', region: 'America' },
            { value: 'America/Argentina/Ushuaia', label: 'Ushuaia', region: 'America' },
            { value: 'America/Aruba', label: 'Aruba', region: 'America' },
            { value: 'America/Asuncion', label: 'Asuncion', region: 'America' },
            { value: 'America/Atikokan', label: 'Atikokan', region: 'America' },
            { value: 'America/Bahia', label: 'Bahia', region: 'America' },
            { value: 'America/Bahia_Banderas', label: 'Bahia Banderas', region: 'America' },
            { value: 'America/Barbados', label: 'Barbados', region: 'America' },
            { value: 'America/Belem', label: 'Belem', region: 'America' },
            { value: 'America/Belize', label: 'Belize', region: 'America' },
            { value: 'America/Blanc-Sablon', label: 'Blanc-Sablon', region: 'America' },
            { value: 'America/Boa_Vista', label: 'Boa Vista', region: 'America' },
            { value: 'America/Bogota', label: 'Bogota', region: 'America' },
            { value: 'America/Boise', label: 'Boise', region: 'America' },
            { value: 'America/Cambridge_Bay', label: 'Cambridge Bay', region: 'America' },
            { value: 'America/Campo_Grande', label: 'Campo Grande', region: 'America' },
            { value: 'America/Cancun', label: 'Cancun', region: 'America' },
            { value: 'America/Caracas', label: 'Caracas', region: 'America' },
            { value: 'America/Cayenne', label: 'Cayenne', region: 'America' },
            { value: 'America/Cayman', label: 'Cayman', region: 'America' },
            { value: 'America/Chicago', label: 'Chicago (Central Time)', region: 'America' },
            { value: 'America/Chihuahua', label: 'Chihuahua', region: 'America' },
            { value: 'America/Costa_Rica', label: 'Costa Rica', region: 'America' },
            { value: 'America/Creston', label: 'Creston', region: 'America' },
            { value: 'America/Cuiaba', label: 'Cuiaba', region: 'America' },
            { value: 'America/Curacao', label: 'Curacao', region: 'America' },
            { value: 'America/Danmarkshavn', label: 'Danmarkshavn', region: 'America' },
            { value: 'America/Dawson', label: 'Dawson', region: 'America' },
            { value: 'America/Dawson_Creek', label: 'Dawson Creek', region: 'America' },
            { value: 'America/Denver', label: 'Denver (Mountain Time)', region: 'America' },
            { value: 'America/Detroit', label: 'Detroit', region: 'America' },
            { value: 'America/Dominica', label: 'Dominica', region: 'America' },
            { value: 'America/Edmonton', label: 'Edmonton', region: 'America' },
            { value: 'America/Eirunepe', label: 'Eirunepe', region: 'America' },
            { value: 'America/El_Salvador', label: 'El Salvador', region: 'America' },
            { value: 'America/Fort_Nelson', label: 'Fort Nelson', region: 'America' },
            { value: 'America/Fortaleza', label: 'Fortaleza', region: 'America' },
            { value: 'America/Glace_Bay', label: 'Glace Bay', region: 'America' },
            { value: 'America/Goose_Bay', label: 'Goose Bay', region: 'America' },
            { value: 'America/Grand_Turk', label: 'Grand Turk', region: 'America' },
            { value: 'America/Grenada', label: 'Grenada', region: 'America' },
            { value: 'America/Guadeloupe', label: 'Guadeloupe', region: 'America' },
            { value: 'America/Guatemala', label: 'Guatemala', region: 'America' },
            { value: 'America/Guayaquil', label: 'Guayaquil', region: 'America' },
            { value: 'America/Guyana', label: 'Guyana', region: 'America' },
            { value: 'America/Halifax', label: 'Halifax', region: 'America' },
            { value: 'America/Havana', label: 'Havana', region: 'America' },
            { value: 'America/Hermosillo', label: 'Hermosillo', region: 'America' },
            { value: 'America/Indiana/Indianapolis', label: 'Indianapolis', region: 'America' },
            { value: 'America/Indiana/Knox', label: 'Knox', region: 'America' },
            { value: 'America/Indiana/Marengo', label: 'Marengo', region: 'America' },
            { value: 'America/Indiana/Petersburg', label: 'Petersburg', region: 'America' },
            { value: 'America/Indiana/Tell_City', label: 'Tell City', region: 'America' },
            { value: 'America/Indiana/Vevay', label: 'Vevay', region: 'America' },
            { value: 'America/Indiana/Vincennes', label: 'Vincennes', region: 'America' },
            { value: 'America/Indiana/Winamac', label: 'Winamac', region: 'America' },
            { value: 'America/Inuvik', label: 'Inuvik', region: 'America' },
            { value: 'America/Iqaluit', label: 'Iqaluit', region: 'America' },
            { value: 'America/Jamaica', label: 'Jamaica', region: 'America' },
            { value: 'America/Juneau', label: 'Juneau', region: 'America' },
            { value: 'America/Kentucky/Louisville', label: 'Louisville', region: 'America' },
            { value: 'America/Kentucky/Monticello', label: 'Monticello', region: 'America' },
            { value: 'America/Kralendijk', label: 'Kralendijk', region: 'America' },
            { value: 'America/La_Paz', label: 'La Paz', region: 'America' },
            { value: 'America/Lima', label: 'Lima', region: 'America' },
            { value: 'America/Los_Angeles', label: 'Los Angeles (Pacific Time)', region: 'America' },
            { value: 'America/Lower_Princes', label: 'Lower Princes', region: 'America' },
            { value: 'America/Maceio', label: 'Maceio', region: 'America' },
            { value: 'America/Managua', label: 'Managua', region: 'America' },
            { value: 'America/Manaus', label: 'Manaus', region: 'America' },
            { value: 'America/Marigot', label: 'Marigot', region: 'America' },
            { value: 'America/Martinique', label: 'Martinique', region: 'America' },
            { value: 'America/Matamoros', label: 'Matamoros', region: 'America' },
            { value: 'America/Mazatlan', label: 'Mazatlan', region: 'America' },
            { value: 'America/Menominee', label: 'Menominee', region: 'America' },
            { value: 'America/Merida', label: 'Merida', region: 'America' },
            { value: 'America/Metlakatla', label: 'Metlakatla', region: 'America' },
            { value: 'America/Mexico_City', label: 'Mexico City', region: 'America' },
            { value: 'America/Miquelon', label: 'Miquelon', region: 'America' },
            { value: 'America/Moncton', label: 'Moncton', region: 'America' },
            { value: 'America/Monterrey', label: 'Monterrey', region: 'America' },
            { value: 'America/Montevideo', label: 'Montevideo', region: 'America' },
            { value: 'America/Montserrat', label: 'Montserrat', region: 'America' },
            { value: 'America/Nassau', label: 'Nassau', region: 'America' },
            { value: 'America/New_York', label: 'New York (Eastern Time)', region: 'America' },
            { value: 'America/Nipigon', label: 'Nipigon', region: 'America' },
            { value: 'America/Nome', label: 'Nome', region: 'America' },
            { value: 'America/Noronha', label: 'Noronha', region: 'America' },
            { value: 'America/North_Dakota/Beulah', label: 'Beulah', region: 'America' },
            { value: 'America/North_Dakota/Center', label: 'Center', region: 'America' },
            { value: 'America/North_Dakota/New_Salem', label: 'New Salem', region: 'America' },
            { value: 'America/Nuuk', label: 'Nuuk', region: 'America' },
            { value: 'America/Ojinaga', label: 'Ojinaga', region: 'America' },
            { value: 'America/Panama', label: 'Panama', region: 'America' },
            { value: 'America/Pangnirtung', label: 'Pangnirtung', region: 'America' },
            { value: 'America/Paramaribo', label: 'Paramaribo', region: 'America' },
            { value: 'America/Phoenix', label: 'Phoenix', region: 'America' },
            { value: 'America/Port-au-Prince', label: 'Port-au-Prince', region: 'America' },
            { value: 'America/Port_of_Spain', label: 'Port of Spain', region: 'America' },
            { value: 'America/Porto_Velho', label: 'Porto Velho', region: 'America' },
            { value: 'America/Puerto_Rico', label: 'Puerto Rico', region: 'America' },
            { value: 'America/Punta_Arenas', label: 'Punta Arenas', region: 'America' },
            { value: 'America/Rainy_River', label: 'Rainy River', region: 'America' },
            { value: 'America/Rankin_Inlet', label: 'Rankin Inlet', region: 'America' },
            { value: 'America/Recife', label: 'Recife', region: 'America' },
            { value: 'America/Regina', label: 'Regina', region: 'America' },
            { value: 'America/Resolute', label: 'Resolute', region: 'America' },
            { value: 'America/Rio_Branco', label: 'Rio Branco', region: 'America' },
            { value: 'America/Santarem', label: 'Santarem', region: 'America' },
            { value: 'America/Santiago', label: 'Santiago', region: 'America' },
            { value: 'America/Santo_Domingo', label: 'Santo Domingo', region: 'America' },
            { value: 'America/Sao_Paulo', label: 'Sao Paulo', region: 'America' },
            { value: 'America/Scoresbysund', label: 'Scoresbysund', region: 'America' },
            { value: 'America/Sitka', label: 'Sitka', region: 'America' },
            { value: 'America/St_Barthelemy', label: 'St Barthelemy', region: 'America' },
            { value: 'America/St_Johns', label: 'St Johns', region: 'America' },
            { value: 'America/St_Kitts', label: 'St Kitts', region: 'America' },
            { value: 'America/St_Lucia', label: 'St Lucia', region: 'America' },
            { value: 'America/St_Thomas', label: 'St Thomas', region: 'America' },
            { value: 'America/St_Vincent', label: 'St Vincent', region: 'America' },
            { value: 'America/Swift_Current', label: 'Swift Current', region: 'America' },
            { value: 'America/Tegucigalpa', label: 'Tegucigalpa', region: 'America' },
            { value: 'America/Thule', label: 'Thule', region: 'America' },
            { value: 'America/Thunder_Bay', label: 'Thunder Bay', region: 'America' },
            { value: 'America/Tijuana', label: 'Tijuana', region: 'America' },
            { value: 'America/Toronto', label: 'Toronto', region: 'America' },
            { value: 'America/Tortola', label: 'Tortola', region: 'America' },
            { value: 'America/Vancouver', label: 'Vancouver', region: 'America' },
            { value: 'America/Whitehorse', label: 'Whitehorse', region: 'America' },
            { value: 'America/Winnipeg', label: 'Winnipeg', region: 'America' },
            { value: 'America/Yakutat', label: 'Yakutat', region: 'America' },
            { value: 'America/Yellowknife', label: 'Yellowknife', region: 'America' },
            
            // Antarctica
            { value: 'Antarctica/Casey', label: 'Casey', region: 'Antarctica' },
            { value: 'Antarctica/Davis', label: 'Davis', region: 'Antarctica' },
            { value: 'Antarctica/DumontDUrville', label: 'Dumont d\'Urville', region: 'Antarctica' },
            { value: 'Antarctica/Macquarie', label: 'Macquarie', region: 'Antarctica' },
            { value: 'Antarctica/Mawson', label: 'Mawson', region: 'Antarctica' },
            { value: 'Antarctica/McMurdo', label: 'McMurdo', region: 'Antarctica' },
            { value: 'Antarctica/Palmer', label: 'Palmer', region: 'Antarctica' },
            { value: 'Antarctica/Rothera', label: 'Rothera', region: 'Antarctica' },
            { value: 'Antarctica/Syowa', label: 'Syowa', region: 'Antarctica' },
            { value: 'Antarctica/Troll', label: 'Troll', region: 'Antarctica' },
            { value: 'Antarctica/Vostok', label: 'Vostok', region: 'Antarctica' },
            
            // Asia
            { value: 'Asia/Aden', label: 'Aden', region: 'Asia' },
            { value: 'Asia/Almaty', label: 'Almaty', region: 'Asia' },
            { value: 'Asia/Amman', label: 'Amman', region: 'Asia' },
            { value: 'Asia/Anadyr', label: 'Anadyr', region: 'Asia' },
            { value: 'Asia/Aqtau', label: 'Aqtau', region: 'Asia' },
            { value: 'Asia/Aqtobe', label: 'Aqtobe', region: 'Asia' },
            { value: 'Asia/Ashgabat', label: 'Ashgabat', region: 'Asia' },
            { value: 'Asia/Atyrau', label: 'Atyrau', region: 'Asia' },
            { value: 'Asia/Baghdad', label: 'Baghdad', region: 'Asia' },
            { value: 'Asia/Bahrain', label: 'Bahrain', region: 'Asia' },
            { value: 'Asia/Baku', label: 'Baku', region: 'Asia' },
            { value: 'Asia/Bangkok', label: 'Bangkok', region: 'Asia' },
            { value: 'Asia/Barnaul', label: 'Barnaul', region: 'Asia' },
            { value: 'Asia/Beirut', label: 'Beirut', region: 'Asia' },
            { value: 'Asia/Bishkek', label: 'Bishkek', region: 'Asia' },
            { value: 'Asia/Brunei', label: 'Brunei', region: 'Asia' },
            { value: 'Asia/Chita', label: 'Chita', region: 'Asia' },
            { value: 'Asia/Choibalsan', label: 'Choibalsan', region: 'Asia' },
            { value: 'Asia/Colombo', label: 'Colombo', region: 'Asia' },
            { value: 'Asia/Damascus', label: 'Damascus', region: 'Asia' },
            { value: 'Asia/Dhaka', label: 'Dhaka', region: 'Asia' },
            { value: 'Asia/Dili', label: 'Dili', region: 'Asia' },
            { value: 'Asia/Dubai', label: 'Dubai', region: 'Asia' },
            { value: 'Asia/Dushanbe', label: 'Dushanbe', region: 'Asia' },
            { value: 'Asia/Famagusta', label: 'Famagusta', region: 'Asia' },
            { value: 'Asia/Gaza', label: 'Gaza', region: 'Asia' },
            { value: 'Asia/Hebron', label: 'Hebron', region: 'Asia' },
            { value: 'Asia/Ho_Chi_Minh', label: 'Ho Chi Minh', region: 'Asia' },
            { value: 'Asia/Hong_Kong', label: 'Hong Kong', region: 'Asia' },
            { value: 'Asia/Hovd', label: 'Hovd', region: 'Asia' },
            { value: 'Asia/Irkutsk', label: 'Irkutsk', region: 'Asia' },
            { value: 'Asia/Jakarta', label: 'Jakarta', region: 'Asia' },
            { value: 'Asia/Jayapura', label: 'Jayapura', region: 'Asia' },
            { value: 'Asia/Jerusalem', label: 'Jerusalem', region: 'Asia' },
            { value: 'Asia/Kabul', label: 'Kabul', region: 'Asia' },
            { value: 'Asia/Kamchatka', label: 'Kamchatka', region: 'Asia' },
            { value: 'Asia/Karachi', label: 'Karachi', region: 'Asia' },
            { value: 'Asia/Kathmandu', label: 'Kathmandu', region: 'Asia' },
            { value: 'Asia/Khandyga', label: 'Khandyga', region: 'Asia' },
            { value: 'Asia/Kolkata', label: 'Kolkata (India)', region: 'Asia' },
            { value: 'Asia/Krasnoyarsk', label: 'Krasnoyarsk', region: 'Asia' },
            { value: 'Asia/Kuala_Lumpur', label: 'Kuala Lumpur', region: 'Asia' },
            { value: 'Asia/Kuching', label: 'Kuching', region: 'Asia' },
            { value: 'Asia/Kuwait', label: 'Kuwait', region: 'Asia' },
            { value: 'Asia/Macau', label: 'Macau', region: 'Asia' },
            { value: 'Asia/Magadan', label: 'Magadan', region: 'Asia' },
            { value: 'Asia/Makassar', label: 'Makassar', region: 'Asia' },
            { value: 'Asia/Manila', label: 'Manila', region: 'Asia' },
            { value: 'Asia/Muscat', label: 'Muscat', region: 'Asia' },
            { value: 'Asia/Nicosia', label: 'Nicosia', region: 'Asia' },
            { value: 'Asia/Novokuznetsk', label: 'Novokuznetsk', region: 'Asia' },
            { value: 'Asia/Novosibirsk', label: 'Novosibirsk', region: 'Asia' },
            { value: 'Asia/Omsk', label: 'Omsk', region: 'Asia' },
            { value: 'Asia/Oral', label: 'Oral', region: 'Asia' },
            { value: 'Asia/Phnom_Penh', label: 'Phnom Penh', region: 'Asia' },
            { value: 'Asia/Pontianak', label: 'Pontianak', region: 'Asia' },
            { value: 'Asia/Pyongyang', label: 'Pyongyang', region: 'Asia' },
            { value: 'Asia/Qatar', label: 'Qatar', region: 'Asia' },
            { value: 'Asia/Qostanay', label: 'Qostanay', region: 'Asia' },
            { value: 'Asia/Qyzylorda', label: 'Qyzylorda', region: 'Asia' },
            { value: 'Asia/Riyadh', label: 'Riyadh', region: 'Asia' },
            { value: 'Asia/Sakhalin', label: 'Sakhalin', region: 'Asia' },
            { value: 'Asia/Samarkand', label: 'Samarkand', region: 'Asia' },
            { value: 'Asia/Seoul', label: 'Seoul', region: 'Asia' },
            { value: 'Asia/Shanghai', label: 'Shanghai (China)', region: 'Asia' },
            { value: 'Asia/Singapore', label: 'Singapore', region: 'Asia' },
            { value: 'Asia/Srednekolymsk', label: 'Srednekolymsk', region: 'Asia' },
            { value: 'Asia/Taipei', label: 'Taipei', region: 'Asia' },
            { value: 'Asia/Tashkent', label: 'Tashkent', region: 'Asia' },
            { value: 'Asia/Tbilisi', label: 'Tbilisi', region: 'Asia' },
            { value: 'Asia/Tehran', label: 'Tehran', region: 'Asia' },
            { value: 'Asia/Thimphu', label: 'Thimphu', region: 'Asia' },
            { value: 'Asia/Tokyo', label: 'Tokyo', region: 'Asia' },
            { value: 'Asia/Tomsk', label: 'Tomsk', region: 'Asia' },
            { value: 'Asia/Ulaanbaatar', label: 'Ulaanbaatar', region: 'Asia' },
            { value: 'Asia/Urumqi', label: 'Urumqi', region: 'Asia' },
            { value: 'Asia/Ust-Nera', label: 'Ust-Nera', region: 'Asia' },
            { value: 'Asia/Vientiane', label: 'Vientiane', region: 'Asia' },
            { value: 'Asia/Vladivostok', label: 'Vladivostok', region: 'Asia' },
            { value: 'Asia/Yakutsk', label: 'Yakutsk', region: 'Asia' },
            { value: 'Asia/Yangon', label: 'Yangon', region: 'Asia' },
            { value: 'Asia/Yekaterinburg', label: 'Yekaterinburg', region: 'Asia' },
            { value: 'Asia/Yerevan', label: 'Yerevan', region: 'Asia' },
            
            // Atlantic
            { value: 'Atlantic/Azores', label: 'Azores', region: 'Atlantic' },
            { value: 'Atlantic/Bermuda', label: 'Bermuda', region: 'Atlantic' },
            { value: 'Atlantic/Canary', label: 'Canary', region: 'Atlantic' },
            { value: 'Atlantic/Cape_Verde', label: 'Cape Verde', region: 'Atlantic' },
            { value: 'Atlantic/Faroe', label: 'Faroe', region: 'Atlantic' },
            { value: 'Atlantic/Madeira', label: 'Madeira', region: 'Atlantic' },
            { value: 'Atlantic/Reykjavik', label: 'Reykjavik', region: 'Atlantic' },
            { value: 'Atlantic/South_Georgia', label: 'South Georgia', region: 'Atlantic' },
            { value: 'Atlantic/St_Helena', label: 'St Helena', region: 'Atlantic' },
            { value: 'Atlantic/Stanley', label: 'Stanley', region: 'Atlantic' },
            
            // Australia
            { value: 'Australia/Adelaide', label: 'Adelaide', region: 'Australia' },
            { value: 'Australia/Brisbane', label: 'Brisbane', region: 'Australia' },
            { value: 'Australia/Broken_Hill', label: 'Broken Hill', region: 'Australia' },
            { value: 'Australia/Darwin', label: 'Darwin', region: 'Australia' },
            { value: 'Australia/Eucla', label: 'Eucla', region: 'Australia' },
            { value: 'Australia/Hobart', label: 'Hobart', region: 'Australia' },
            { value: 'Australia/Lindeman', label: 'Lindeman', region: 'Australia' },
            { value: 'Australia/Lord_Howe', label: 'Lord Howe', region: 'Australia' },
            { value: 'Australia/Melbourne', label: 'Melbourne', region: 'Australia' },
            { value: 'Australia/Perth', label: 'Perth', region: 'Australia' },
            { value: 'Australia/Sydney', label: 'Sydney', region: 'Australia' },
            
            // Europe
            { value: 'Europe/Amsterdam', label: 'Amsterdam', region: 'Europe' },
            { value: 'Europe/Andorra', label: 'Andorra', region: 'Europe' },
            { value: 'Europe/Astrakhan', label: 'Astrakhan', region: 'Europe' },
            { value: 'Europe/Athens', label: 'Athens', region: 'Europe' },
            { value: 'Europe/Belgrade', label: 'Belgrade', region: 'Europe' },
            { value: 'Europe/Berlin', label: 'Berlin', region: 'Europe' },
            { value: 'Europe/Bratislava', label: 'Bratislava', region: 'Europe' },
            { value: 'Europe/Brussels', label: 'Brussels', region: 'Europe' },
            { value: 'Europe/Bucharest', label: 'Bucharest', region: 'Europe' },
            { value: 'Europe/Budapest', label: 'Budapest', region: 'Europe' },
            { value: 'Europe/Busingen', label: 'Busingen', region: 'Europe' },
            { value: 'Europe/Chisinau', label: 'Chisinau', region: 'Europe' },
            { value: 'Europe/Copenhagen', label: 'Copenhagen', region: 'Europe' },
            { value: 'Europe/Dublin', label: 'Dublin', region: 'Europe' },
            { value: 'Europe/Gibraltar', label: 'Gibraltar', region: 'Europe' },
            { value: 'Europe/Guernsey', label: 'Guernsey', region: 'Europe' },
            { value: 'Europe/Helsinki', label: 'Helsinki', region: 'Europe' },
            { value: 'Europe/Isle_of_Man', label: 'Isle of Man', region: 'Europe' },
            { value: 'Europe/Istanbul', label: 'Istanbul', region: 'Europe' },
            { value: 'Europe/Jersey', label: 'Jersey', region: 'Europe' },
            { value: 'Europe/Kaliningrad', label: 'Kaliningrad', region: 'Europe' },
            { value: 'Europe/Kiev', label: 'Kiev', region: 'Europe' },
            { value: 'Europe/Kirov', label: 'Kirov', region: 'Europe' },
            { value: 'Europe/Lisbon', label: 'Lisbon', region: 'Europe' },
            { value: 'Europe/Ljubljana', label: 'Ljubljana', region: 'Europe' },
            { value: 'Europe/London', label: 'London (GMT)', region: 'Europe' },
            { value: 'Europe/Luxembourg', label: 'Luxembourg', region: 'Europe' },
            { value: 'Europe/Madrid', label: 'Madrid', region: 'Europe' },
            { value: 'Europe/Malta', label: 'Malta', region: 'Europe' },
            { value: 'Europe/Mariehamn', label: 'Mariehamn', region: 'Europe' },
            { value: 'Europe/Minsk', label: 'Minsk', region: 'Europe' },
            { value: 'Europe/Monaco', label: 'Monaco', region: 'Europe' },
            { value: 'Europe/Moscow', label: 'Moscow', region: 'Europe' },
            { value: 'Europe/Oslo', label: 'Oslo', region: 'Europe' },
            { value: 'Europe/Paris', label: 'Paris', region: 'Europe' },
            { value: 'Europe/Podgorica', label: 'Podgorica', region: 'Europe' },
            { value: 'Europe/Prague', label: 'Prague', region: 'Europe' },
            { value: 'Europe/Riga', label: 'Riga', region: 'Europe' },
            { value: 'Europe/Rome', label: 'Rome', region: 'Europe' },
            { value: 'Europe/Samara', label: 'Samara', region: 'Europe' },
            { value: 'Europe/San_Marino', label: 'San Marino', region: 'Europe' },
            { value: 'Europe/Sarajevo', label: 'Sarajevo', region: 'Europe' },
            { value: 'Europe/Saratov', label: 'Saratov', region: 'Europe' },
            { value: 'Europe/Simferopol', label: 'Simferopol', region: 'Europe' },
            { value: 'Europe/Skopje', label: 'Skopje', region: 'Europe' },
            { value: 'Europe/Sofia', label: 'Sofia', region: 'Europe' },
            { value: 'Europe/Stockholm', label: 'Stockholm', region: 'Europe' },
            { value: 'Europe/Tallinn', label: 'Tallinn', region: 'Europe' },
            { value: 'Europe/Tirane', label: 'Tirane', region: 'Europe' },
            { value: 'Europe/Ulyanovsk', label: 'Ulyanovsk', region: 'Europe' },
            { value: 'Europe/Uzhgorod', label: 'Uzhgorod', region: 'Europe' },
            { value: 'Europe/Vaduz', label: 'Vaduz', region: 'Europe' },
            { value: 'Europe/Vatican', label: 'Vatican', region: 'Europe' },
            { value: 'Europe/Vienna', label: 'Vienna', region: 'Europe' },
            { value: 'Europe/Vilnius', label: 'Vilnius', region: 'Europe' },
            { value: 'Europe/Volgograd', label: 'Volgograd', region: 'Europe' },
            { value: 'Europe/Warsaw', label: 'Warsaw', region: 'Europe' },
            { value: 'Europe/Zagreb', label: 'Zagreb', region: 'Europe' },
            { value: 'Europe/Zaporozhye', label: 'Zaporozhye', region: 'Europe' },
            { value: 'Europe/Zurich', label: 'Zurich', region: 'Europe' },
            
            // Indian
            { value: 'Indian/Antananarivo', label: 'Antananarivo', region: 'Indian' },
            { value: 'Indian/Chagos', label: 'Chagos', region: 'Indian' },
            { value: 'Indian/Christmas', label: 'Christmas', region: 'Indian' },
            { value: 'Indian/Cocos', label: 'Cocos', region: 'Indian' },
            { value: 'Indian/Comoro', label: 'Comoro', region: 'Indian' },
            { value: 'Indian/Kerguelen', label: 'Kerguelen', region: 'Indian' },
            { value: 'Indian/Mahe', label: 'Mahe', region: 'Indian' },
            { value: 'Indian/Maldives', label: 'Maldives', region: 'Indian' },
            { value: 'Indian/Mauritius', label: 'Mauritius', region: 'Indian' },
            { value: 'Indian/Mayotte', label: 'Mayotte', region: 'Indian' },
            { value: 'Indian/Reunion', label: 'Reunion', region: 'Indian' },
            
            // Pacific
            { value: 'Pacific/Apia', label: 'Apia', region: 'Pacific' },
            { value: 'Pacific/Auckland', label: 'Auckland', region: 'Pacific' },
            { value: 'Pacific/Bougainville', label: 'Bougainville', region: 'Pacific' },
            { value: 'Pacific/Chatham', label: 'Chatham', region: 'Pacific' },
            { value: 'Pacific/Chuuk', label: 'Chuuk', region: 'Pacific' },
            { value: 'Pacific/Easter', label: 'Easter', region: 'Pacific' },
            { value: 'Pacific/Efate', label: 'Efate', region: 'Pacific' },
            { value: 'Pacific/Enderbury', label: 'Enderbury', region: 'Pacific' },
            { value: 'Pacific/Fakaofo', label: 'Fakaofo', region: 'Pacific' },
            { value: 'Pacific/Fiji', label: 'Fiji', region: 'Pacific' },
            { value: 'Pacific/Funafuti', label: 'Funafuti', region: 'Pacific' },
            { value: 'Pacific/Galapagos', label: 'Galapagos', region: 'Pacific' },
            { value: 'Pacific/Gambier', label: 'Gambier', region: 'Pacific' },
            { value: 'Pacific/Guadalcanal', label: 'Guadalcanal', region: 'Pacific' },
            { value: 'Pacific/Guam', label: 'Guam', region: 'Pacific' },
            { value: 'Pacific/Honolulu', label: 'Honolulu (Hawaii)', region: 'Pacific' },
            { value: 'Pacific/Kiritimati', label: 'Kiritimati', region: 'Pacific' },
            { value: 'Pacific/Kosrae', label: 'Kosrae', region: 'Pacific' },
            { value: 'Pacific/Kwajalein', label: 'Kwajalein', region: 'Pacific' },
            { value: 'Pacific/Majuro', label: 'Majuro', region: 'Pacific' },
            { value: 'Pacific/Marquesas', label: 'Marquesas', region: 'Pacific' },
            { value: 'Pacific/Midway', label: 'Midway', region: 'Pacific' },
            { value: 'Pacific/Nauru', label: 'Nauru', region: 'Pacific' },
            { value: 'Pacific/Niue', label: 'Niue', region: 'Pacific' },
            { value: 'Pacific/Norfolk', label: 'Norfolk', region: 'Pacific' },
            { value: 'Pacific/Noumea', label: 'Noumea', region: 'Pacific' },
            { value: 'Pacific/Pago_Pago', label: 'Pago Pago', region: 'Pacific' },
            { value: 'Pacific/Palau', label: 'Palau', region: 'Pacific' },
            { value: 'Pacific/Pitcairn', label: 'Pitcairn', region: 'Pacific' },
            { value: 'Pacific/Pohnpei', label: 'Pohnpei', region: 'Pacific' },
            { value: 'Pacific/Port_Moresby', label: 'Port Moresby', region: 'Pacific' },
            { value: 'Pacific/Rarotonga', label: 'Rarotonga', region: 'Pacific' },
            { value: 'Pacific/Saipan', label: 'Saipan', region: 'Pacific' },
            { value: 'Pacific/Tahiti', label: 'Tahiti', region: 'Pacific' },
            { value: 'Pacific/Tarawa', label: 'Tarawa', region: 'Pacific' },
            { value: 'Pacific/Tongatapu', label: 'Tongatapu', region: 'Pacific' },
            { value: 'Pacific/Wake', label: 'Wake', region: 'Pacific' },
            { value: 'Pacific/Wallis', label: 'Wallis', region: 'Pacific' }
        ];
    };

    AppointmentCalendar.prototype.getTimezoneName = function(tz) {
        var allTimezones = this.getAllTimezones();
        var found = allTimezones.find(function(t) { return t.value === tz; });
        var name = found ? found.label : tz.replace(/_/g, ' ').split('/').pop();
        
        try {
            var now = new Date();
            var timeStr = now.toLocaleTimeString('en-US', { 
                timeZone: tz, 
                hour: '2-digit', 
                minute: '2-digit',
                hour12: false 
            });
            return name + ' (' + timeStr + ')';
        } catch(e) {
            return name;
        }
    };

    AppointmentCalendar.prototype.renderCalendar = function() {
        var container = document.getElementById('calendar-days');
        var monthDisplay = document.getElementById('month-year-display');
        
        if (!container || !monthDisplay) {
            console.error('[Appointment] Calendar containers not found');
            return;
        }
        
        // Update month/year display
        var monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December'];
        monthDisplay.textContent = monthNames[this.currentDate.getMonth()] + ' ' + this.currentDate.getFullYear();
        
        // Update navigation buttons
        this.updateNavButtons();
        
        // Calculate calendar grid
        var year = this.currentDate.getFullYear();
        var month = this.currentDate.getMonth();
        
        var firstDay = new Date(year, month, 1);
        var lastDay = new Date(year, month + 1, 0);
        
        // Monday = 0, Sunday = 6 (Calendly style)
        var startOffset = firstDay.getDay() - 1;
        if (startOffset < 0) startOffset = 6;
        
        var today = new Date();
        today.setHours(0, 0, 0, 0);
        
        var html = '';
        var self = this;
        
        // Previous month trailing days
        var prevMonthLast = new Date(year, month, 0);
        for (var i = startOffset - 1; i >= 0; i--) {
            var day = prevMonthLast.getDate() - i;
            html += '<div class="calendar-day other-month">' + day + '</div>';
        }
        
        // Current month days
        for (var day = 1; day <= lastDay.getDate(); day++) {
            var date = new Date(year, month, day);
            var dateStr = this.formatDate(date);
            var classes = ['calendar-day'];
            
            // Check if today
            if (date.getTime() === today.getTime()) {
                classes.push('today');
            }
            
            // Check if selected
            if (this.selectedDate && dateStr === this.formatDate(this.selectedDate)) {
                classes.push('selected');
            }
            
            // Check availability - initially all future dates are potentially available
            if (date < this.minDate || date > this.maxDate) {
                classes.push('disabled');
            } else if (this.availableSlots[dateStr] && this.availableSlots[dateStr].length > 0) {
                classes.push('available');
            } else if (Object.keys(this.availableSlots).length === 0) {
                // No slots fetched yet - mark as potentially available
                if (date >= this.minDate && date <= this.maxDate) {
                    classes.push('available');
                }
            } else {
                classes.push('disabled');
            }
            
            html += '<div class="' + classes.join(' ') + '" data-date="' + dateStr + '">' + day + '</div>';
        }
        
        // Next month leading days (fill to 6 rows = 42 cells)
        var totalCells = startOffset + lastDay.getDate();
        var remainingCells = totalCells <= 35 ? 35 - totalCells : 42 - totalCells;
        for (var d = 1; d <= remainingCells; d++) {
            html += '<div class="calendar-day other-month">' + d + '</div>';
        }
        
        container.innerHTML = html;
        
        // Bind click events to available days
        var availableDays = container.querySelectorAll('.calendar-day.available');
        for (var j = 0; j < availableDays.length; j++) {
            (function(dayEl) {
                dayEl.onclick = function(e) {
                    self.onDayClick(e, dayEl);
                };
            })(availableDays[j]);
        }
        
        console.log('[Appointment] Calendar rendered:', monthDisplay.textContent, '- Days:', lastDay.getDate());
    };

    AppointmentCalendar.prototype.updateNavButtons = function() {
        var prevBtn = document.getElementById('prev-month');
        var nextBtn = document.getElementById('next-month');
        
        if (prevBtn) {
            // Disable prev if current month <= min date month
            var currentMonth = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth(), 1);
            var minMonth = new Date(this.minDate.getFullYear(), this.minDate.getMonth(), 1);
            prevBtn.disabled = currentMonth <= minMonth;
            console.log('[Appointment] Prev button disabled:', prevBtn.disabled, 'Current:', currentMonth, 'Min:', minMonth);
        }
        
        if (nextBtn) {
            var nextMonth = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() + 1, 1);
            nextBtn.disabled = nextMonth > this.maxDate;
        }
    };

    AppointmentCalendar.prototype.fetchSlots = function() {
        var self = this;
        var startDate = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth(), 1);
        var endDate = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() + 1, 0);
        
        console.log('[Appointment] Fetching slots:', this.formatDate(startDate), 'to', this.formatDate(endDate));
        
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/appointment/slots', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    try {
                        var data = JSON.parse(xhr.responseText);
                        console.log('[Appointment] Slots response:', data);
                        if (data.result && data.result.slots) {
                            self.availableSlots = data.result.slots;
                            self.renderCalendar();
                            
                            if (self.selectedDate) {
                                self.renderTimeSlots();
                            }
                        } else if (data.result && data.result.error) {
                            console.error('[Appointment] Server error:', data.result.error);
                        }
                    } catch(e) {
                        console.error('[Appointment] Parse error:', e);
                    }
                } else {
                    console.error('[Appointment] HTTP error:', xhr.status);
                }
            }
        };
        
        xhr.send(JSON.stringify({
            jsonrpc: '2.0',
            method: 'call',
            params: {
                appointment_type_id: this.config.appointmentTypeId,
                user_id: this.config.userId,
                start_date: this.formatDate(startDate),
                end_date: this.formatDate(endDate),
                timezone: this.timezone
            },
            id: Date.now()
        }));
    };

    AppointmentCalendar.prototype.renderTimeSlots = function() {
        var panel = document.getElementById('timeslots-panel');
        var header = document.getElementById('timeslots-header');
        var list = document.getElementById('timeslots-list');
        
        if (!panel || !header || !list) return;
        
        var dateStr = this.formatDate(this.selectedDate);
        var slots = this.availableSlots[dateStr] || [];
        
        // Update header
        var options = { weekday: 'long', month: 'long', day: 'numeric' };
        header.textContent = this.selectedDate.toLocaleDateString('en-US', options);
        
        var self = this;
        
        // Render slots
        if (slots.length === 0) {
            list.innerHTML = '<div class="no-slots">No available times for this date</div>';
        } else {
            var html = '';
            for (var i = 0; i < slots.length; i++) {
                var slot = slots[i];
                var displayTime = slot.display_time || slot.start_formatted || slot.start.split('T')[1].substring(0, 5);
                var isSelected = self.selectedSlot && self.selectedSlot.start === slot.start;
                
                html += '<div class="timeslot-item">';
                html += '<button type="button" class="timeslot-btn ' + (isSelected ? 'selected' : '') + '" ';
                html += 'data-start="' + slot.start + '" data-end="' + slot.end + '" data-display="' + displayTime + '">';
                html += displayTime;
                html += '</button>';
                if (isSelected) {
                    html += '<button type="button" class="timeslot-confirm">Next</button>';
                }
                html += '</div>';
            }
            list.innerHTML = html;
            
            // Bind time slot clicks
            var slotBtns = list.querySelectorAll('.timeslot-btn');
            for (var j = 0; j < slotBtns.length; j++) {
                (function(btn) {
                    btn.onclick = function(e) {
                        self.onTimeSlotClick(e, btn);
                    };
                })(slotBtns[j]);
            }
            
            var confirmBtns = list.querySelectorAll('.timeslot-confirm');
            for (var k = 0; k < confirmBtns.length; k++) {
                (function(btn) {
                    btn.onclick = function(e) {
                        self.onConfirmClick(e);
                    };
                })(confirmBtns[k]);
            }
        }
        
        // Show panel
        panel.style.display = 'block';
    };

    // Event Handlers
    AppointmentCalendar.prototype.onPrevMonth = function() {
        console.log('[Appointment] onPrevMonth called, current:', this.currentDate);
        this.currentDate.setMonth(this.currentDate.getMonth() - 1);
        console.log('[Appointment] After prev, current:', this.currentDate);
        this.selectedDate = null;
        this.selectedSlot = null;
        var panel = document.getElementById('timeslots-panel');
        if (panel) panel.style.display = 'none';
        this.fetchSlots();
    };

    AppointmentCalendar.prototype.onNextMonth = function() {
        console.log('[Appointment] onNextMonth called, current:', this.currentDate);
        this.currentDate.setMonth(this.currentDate.getMonth() + 1);
        console.log('[Appointment] After next, current:', this.currentDate);
        this.selectedDate = null;
        this.selectedSlot = null;
        var panel = document.getElementById('timeslots-panel');
        if (panel) panel.style.display = 'none';
        this.fetchSlots();
    };

    AppointmentCalendar.prototype.onDayClick = function(e, dayEl) {
        var dateStr = dayEl.getAttribute('data-date');
        
        if (!dateStr) return;
        
        this.selectedDate = new Date(dateStr + 'T00:00:00');
        this.selectedSlot = null;
        
        console.log('[Appointment] Day selected:', dateStr);
        
        // Update calendar UI
        this.renderCalendar();
        
        // Show time slots
        this.renderTimeSlots();
    };

    AppointmentCalendar.prototype.onTimeSlotClick = function(e, btn) {
        this.selectedSlot = {
            start: btn.getAttribute('data-start'),
            end: btn.getAttribute('data-end'),
            displayTime: btn.getAttribute('data-display') || btn.textContent.trim()
        };
        
        console.log('[Appointment] Time selected:', this.selectedSlot);
        
        // Re-render to show confirm button
        this.renderTimeSlots();
    };

    AppointmentCalendar.prototype.onConfirmClick = function(e) {
        e.preventDefault();
        
        if (!this.selectedDate || !this.selectedSlot) return;
        
        console.log('[Appointment] Proceeding to form');
        
        // Hide calendar, show form
        var calPanel = document.getElementById('calendar-panel');
        var slotsPanel = document.getElementById('timeslots-panel');
        var formPanel = document.getElementById('form-panel');
        var backBtn = document.getElementById('back-to-calendar');
        
        if (calPanel) calPanel.style.display = 'none';
        if (slotsPanel) slotsPanel.style.display = 'none';
        if (formPanel) formPanel.style.display = 'block';
        if (backBtn) backBtn.style.display = 'flex';
        
        // Show selected time in left panel
        var selectedTimeDisplay = document.getElementById('selected-time-display');
        var datetimeText = document.getElementById('selected-datetime-text');
        var timezoneText = document.getElementById('selected-timezone-text');
        
        if (selectedTimeDisplay && datetimeText && timezoneText) {
            var dateOptions = { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' };
            var dateFormatted = this.selectedDate.toLocaleDateString('en-US', dateOptions);
            datetimeText.textContent = this.selectedSlot.displayTime + ', ' + dateFormatted;
            timezoneText.textContent = this.getTimezoneName(this.timezone);
            selectedTimeDisplay.style.display = 'block';
        }
        
        // Set hidden form fields (IDs match the HTML template)
        var formDatetime = document.getElementById('selected-datetime-input');
        var formTimezone = document.getElementById('selected-timezone-input');
        if (formDatetime) formDatetime.value = this.selectedSlot.start;
        if (formTimezone) formTimezone.value = this.timezone;
    };

    AppointmentCalendar.prototype.onBackToCalendar = function() {
        console.log('[Appointment] Back to calendar');
        
        // Show calendar, hide form
        var calPanel = document.getElementById('calendar-panel');
        var slotsPanel = document.getElementById('timeslots-panel');
        var formPanel = document.getElementById('form-panel');
        var backBtn = document.getElementById('back-to-calendar');
        var selectedTimeDisplay = document.getElementById('selected-time-display');
        
        if (calPanel) calPanel.style.display = 'block';
        if (slotsPanel) slotsPanel.style.display = 'block';
        if (formPanel) formPanel.style.display = 'none';
        if (backBtn) backBtn.style.display = 'none';
        if (selectedTimeDisplay) selectedTimeDisplay.style.display = 'none';
    };

    AppointmentCalendar.prototype.onAddGuests = function() {
        var container = document.getElementById('guests-container');
        var btn = document.getElementById('add-guests-btn');
        
        if (container && btn) {
            container.style.display = 'block';
            btn.style.display = 'none';
        }
    };

    AppointmentCalendar.prototype.onFormSubmit = function(e) {
        var form = e.target;
        var submitBtn = document.getElementById('submit-btn');
        
        // Validate
        if (!form.checkValidity()) {
            return;
        }
        
        // Disable button
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="loading-spinner"></span> Scheduling...';
        }
    };

    // Utilities
    AppointmentCalendar.prototype.formatDate = function(date) {
        var year = date.getFullYear();
        var month = String(date.getMonth() + 1).padStart(2, '0');
        var day = String(date.getDate()).padStart(2, '0');
        return year + '-' + month + '-' + day;
    };

    // Initialize when ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCalendar);
    } else {
        // DOM already loaded
        initCalendar();
    }
    
    // Also try after a short delay (for lazy-loaded scripts)
    setTimeout(initCalendar, 500);
    setTimeout(initCalendar, 1500);

})();

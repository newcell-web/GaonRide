/* driver.js — Driver dashboard logic (driver.html only) */

let _driverMap = null;
let _driverMarkers = [];

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    initDriverMap();
    loadGroups();
    setupRefreshButton();
    setupSeedButton();
    setupOfferModal();
});

// ---------------------------------------------------------------------------
// Map initialisation
// ---------------------------------------------------------------------------

function initDriverMap() {
    if (typeof L === 'undefined') return;
    _driverMap = initMap('driver-map', [26.3, 91.6], 8);
}

// ---------------------------------------------------------------------------
// Load and render groups
// ---------------------------------------------------------------------------

async function loadGroups() {
    showLoading('Loading demand groups…');
    try {
        const groups = await apiFetch('/groups/');
        updateStats(groups);

        const grid = document.getElementById('groups-grid');
        const empty = document.getElementById('empty-state');
        if (!grid) return;

        grid.innerHTML = '';
        clearMap(_driverMap);
        _driverMarkers = [];

        if (groups.length === 0) {
            if (empty) empty.removeAttribute('hidden');
        } else {
            if (empty) empty.setAttribute('hidden', '');
            groups.forEach(group => {
                grid.appendChild(renderGroupCard(group));

                // Add destination marker if coords available
                if (_driverMap && group.dest_lat && group.dest_lon) {
                    const label = `${group.destination_text}\n${group.total_passengers} passenger(s)`;
                    const m = addMarker(_driverMap, group.dest_lat, group.dest_lon, label, 'orange');
                    _driverMarkers.push(m);
                }
            });

            if (_driverMarkers.length > 0) {
                fitMarkers(_driverMap, _driverMarkers);
            }
        }
    } catch (err) {
        showToast(err.message || 'Failed to load groups', 'error');
    } finally {
        hideLoading();
    }
}

// ---------------------------------------------------------------------------
// Stats bar
// ---------------------------------------------------------------------------

function updateStats(groups) {
    const setEl = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };

    const totalPassengers = groups.reduce((sum, g) => sum + (g.total_passengers || 0), 0);
    const offeredCount = groups.filter(g => g.driver_offer && g.status === 'confirmed').length;

    setEl('stat-groups',     groups.length);
    setEl('stat-passengers', totalPassengers);
    setEl('stat-offered',    offeredCount);
}

// ---------------------------------------------------------------------------
// Group card rendering
// ---------------------------------------------------------------------------

function renderGroupCard(group) {
    const card = document.createElement('div');
    card.className = 'group-card';

    const hasOffer = !!group.driver_offer;
    const statusLabel = _statusLabel(group.status);
    const departure = group.suggested_departure ? formatTime(group.suggested_departure) : 'TBD';

    card.innerHTML = `
        <div class="group-card-header">
            <span class="group-destination">${_esc(group.destination_text)}</span>
            <span class="status-badge status-badge--${_esc(group.status)}">${statusLabel}</span>
        </div>
        <dl class="group-card-meta">
            <div class="meta-item">
                <dt>📅 Date</dt>
                <dd>${formatDate(group.travel_date)}</dd>
            </div>
            <div class="meta-item">
                <dt>🕐 Departure</dt>
                <dd>${departure}</dd>
            </div>
            <div class="meta-item">
                <dt>👥 Passengers</dt>
                <dd>${group.total_passengers}</dd>
            </div>
            <div class="meta-item">
                <dt>👤 Members</dt>
                <dd>${group.member_count}</dd>
            </div>
            ${hasOffer ? `
            <div class="meta-item meta-item--full">
                <dt>🚐 Driver</dt>
                <dd>${_esc(group.driver_offer.driver_name)} — ${_esc(group.driver_offer.vehicle_type)}
                    (${group.driver_offer.available_seats} seats)</dd>
            </div>` : ''}
        </dl>
        <div class="group-card-footer">
            <button
                type="button"
                class="btn btn-primary offer-ride-btn"
                ${hasOffer ? 'disabled' : ''}>
                ${hasOffer ? '✓ Offer Confirmed' : 'Offer a Ride'}
            </button>
        </div>
    `;

    if (!hasOffer) {
        card.querySelector('.offer-ride-btn').addEventListener('click', () => openOfferModal(group));
    }

    return card;
}

function _statusLabel(status) {
    const map = { active: 'Active', confirmed: 'Confirmed', completed: 'Completed' };
    return map[status] || status;
}

function _esc(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ---------------------------------------------------------------------------
// Offer modal
// ---------------------------------------------------------------------------

function openOfferModal(group) {
    const modal    = document.getElementById('offer-modal');
    const nameEl   = document.getElementById('modal-group-name');
    const detailEl = document.getElementById('modal-group-details');
    const idInput  = document.getElementById('offer-group-id');
    const deptInput = document.getElementById('departure-time');

    if (nameEl) nameEl.textContent = `Group #${group.id} — ${group.destination_text}`;
    if (detailEl) {
        detailEl.textContent = [
            formatDate(group.travel_date),
            group.suggested_departure ? `Suggested departure: ${formatTime(group.suggested_departure)}` : '',
            `${group.total_passengers} passenger(s)`,
        ].filter(Boolean).join(' · ');
    }
    if (idInput) idInput.value = group.id;
    if (deptInput && group.suggested_departure) {
        // Pre-fill with suggested time (HH:MM)
        deptInput.value = String(group.suggested_departure).substring(0, 5);
    }

    if (modal) modal.removeAttribute('hidden');
}

function closeOfferModal() {
    const modal = document.getElementById('offer-modal');
    if (modal) modal.setAttribute('hidden', '');
    const form = document.getElementById('offer-form');
    if (form) form.reset();
}

async function submitOffer() {
    const form = document.getElementById('offer-form');
    if (!form) return;

    const fd = new FormData(form);
    const get = key => (fd.get(key) || '').trim();

    const payload = {
        group_id:           parseInt(get('group_id'), 10),
        driver_name:        get('driver_name'),
        driver_phone:       get('driver_phone'),
        vehicle_type:       get('vehicle_type'),
        available_seats:    parseInt(get('available_seats'), 10),
        proposed_departure: get('departure_time'),
    };

    if (!payload.driver_name || !payload.driver_phone || !payload.vehicle_type ||
        !payload.available_seats || !payload.proposed_departure) {
        showToast('Please fill in all required fields.', 'error');
        return;
    }

    showLoading('Submitting your offer…');
    try {
        await apiFetch('/drivers/offer', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
        closeOfferModal();
        showToast('Ride offered successfully!', 'success');
        loadGroups();
    } catch (err) {
        showToast(err.message || 'Failed to submit offer', 'error');
    } finally {
        hideLoading();
    }
}

// ---------------------------------------------------------------------------
// Seed data
// ---------------------------------------------------------------------------

async function seedData() {
    showLoading('Loading demo data…');
    try {
        await apiFetch('/seed', { method: 'POST' });
        showToast('Demo data loaded!', 'success');
        loadGroups();
    } catch (err) {
        showToast(err.message || 'Failed to load demo data', 'error');
    } finally {
        hideLoading();
    }
}

// ---------------------------------------------------------------------------
// Button wiring
// ---------------------------------------------------------------------------

function setupRefreshButton() {
    const btn = document.getElementById('refresh-btn');
    if (btn) btn.addEventListener('click', loadGroups);
}

function setupSeedButton() {
    const btn = document.getElementById('seed-btn');
    if (btn) btn.addEventListener('click', seedData);
}

function setupOfferModal() {
    // Close on backdrop click
    const modal = document.getElementById('offer-modal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeOfferModal();
        });
    }

    // Close on X button
    const closeBtn = document.getElementById('modal-close-btn');
    if (closeBtn) closeBtn.addEventListener('click', closeOfferModal);

    // Close on Cancel button
    const cancelBtn = document.getElementById('cancel-offer-btn');
    if (cancelBtn) cancelBtn.addEventListener('click', closeOfferModal);

    // Form submit
    const form = document.getElementById('offer-form');
    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            submitOffer();
        });
    }
}

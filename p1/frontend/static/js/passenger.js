/* passenger.js — Passenger dashboard logic (passenger.html only) */

let _passengerMap = null;
let _passengerMarkers = [];

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupTextForm();
    setupAIConfirmButton();
    setupEditManuallyButton();
    initPassengerMap();
    loadGroupsPreview();
});

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------

function setupTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.tab;

            // Deactivate all
            tabBtns.forEach(b => {
                b.classList.remove('tab-btn--active');
                b.setAttribute('aria-selected', 'false');
            });
            document.querySelectorAll('.tab-panel').forEach(p => {
                p.classList.remove('tab-panel--active');
                p.setAttribute('hidden', '');
            });

            // Activate selected
            btn.classList.add('tab-btn--active');
            btn.setAttribute('aria-selected', 'true');
            const panel = document.getElementById('tab-' + target);
            if (panel) {
                panel.classList.add('tab-panel--active');
                panel.removeAttribute('hidden');
            }
        });
    });
}

// ---------------------------------------------------------------------------
// Text form submit
// ---------------------------------------------------------------------------

function setupTextForm() {
    const form = document.getElementById('ride-request-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const payload = buildPayloadFromForm(form, false);
        if (!payload) return; // validation failed

        showLoading('Finding matching rides…');
        try {
            const data = await apiFetch('/requests/', {
                method: 'POST',
                body: JSON.stringify(payload),
            });
            renderGroupSuggestion(data);
            showToast('Your ride request has been submitted!', 'success');
        } catch (err) {
            showToast(err.message || 'Submission failed', 'error');
        } finally {
            hideLoading();
        }
    });
}

/**
 * Build a RideRequestCreate payload from a form element.
 * Returns null if required fields are missing.
 */
function buildPayloadFromForm(form, aiParsed) {
    const fd = new FormData(form);
    const get = key => (fd.get(key) || '').trim();

    const name = get('passenger_name');
    const origin = get('origin');
    const destination = get('destination');
    const travelDate = get('travel_date');
    const preferredTime = get('preferred_time');

    if (!name || !origin || !destination || !travelDate || !preferredTime) {
        showToast('Please fill in all required fields.', 'error');
        return null;
    }

    return {
        passenger_name:  name,
        passenger_phone: get('passenger_phone') || null,
        origin,
        destination,
        travel_date:     travelDate,
        preferred_time:  preferredTime,
        passenger_count: parseInt(get('passenger_count'), 10) || 1,
        notes:           get('notes') || null,
        ai_parsed:       aiParsed,
    };
}

// ---------------------------------------------------------------------------
// AI confirm button
// ---------------------------------------------------------------------------

function setupAIConfirmButton() {
    const btn = document.getElementById('confirm-ai-btn');
    if (!btn) return;

    btn.addEventListener('click', async () => {
        const parsed = typeof getLastParsed === 'function' ? getLastParsed() : null;
        if (!parsed) {
            showToast('No AI result to confirm.', 'error');
            return;
        }

        // Try to get name/phone from the text form fields (shared page)
        const nameEl  = document.getElementById('passenger-name');
        const phoneEl = document.getElementById('passenger-phone');
        const passengerName  = (nameEl  && nameEl.value.trim())  || '';
        const passengerPhone = (phoneEl && phoneEl.value.trim()) || null;

        if (!passengerName) {
            showToast('Please enter your name in the "Type Request" tab before confirming.', 'error');
            return;
        }

        const payload = {
            passenger_name:  passengerName,
            passenger_phone: passengerPhone,
            origin:          parsed.origin,
            destination:     parsed.destination,
            travel_date:     parsed.travel_date,
            preferred_time:  parsed.preferred_time,
            passenger_count: parsed.passenger_count || 1,
            language:        parsed.language || 'en',
            notes:           parsed.notes || null,
            ai_parsed:       true,
        };

        showLoading('Submitting your ride request…');
        try {
            const data = await apiFetch('/requests/', {
                method: 'POST',
                body: JSON.stringify(payload),
            });
            renderGroupSuggestion(data);
            showToast('Your ride request has been submitted!', 'success');
            // Hide the AI card now that it's been confirmed
            const card = document.getElementById('ai-result-card');
            if (card) card.setAttribute('hidden', '');
        } catch (err) {
            showToast(err.message || 'Submission failed', 'error');
        } finally {
            hideLoading();
        }
    });
}

// ---------------------------------------------------------------------------
// Edit Manually button
// ---------------------------------------------------------------------------

function setupEditManuallyButton() {
    const btn = document.getElementById('edit-manually-btn');
    if (!btn) return;

    btn.addEventListener('click', () => {
        const parsed = typeof getLastParsed === 'function' ? getLastParsed() : null;

        // Switch to text tab
        const textTabBtn = document.getElementById('tab-text-btn');
        if (textTabBtn) textTabBtn.click();

        // Pre-fill the text form if we have parsed data
        if (parsed) {
            _setField('origin',           parsed.origin);
            _setField('destination',      parsed.destination);
            _setField('travel_date',      parsed.travel_date);
            _setField('preferred_time',   parsed.preferred_time ? parsed.preferred_time.substring(0, 5) : '');
            _setField('passenger_count',  parsed.passenger_count || 1);
            _setField('notes',            parsed.notes || '');
        }
    });
}

function _setField(id, value) {
    const el = document.getElementById(id);
    if (el && value !== null && value !== undefined) el.value = value;
}

// ---------------------------------------------------------------------------
// Render group suggestion card
// ---------------------------------------------------------------------------

function renderGroupSuggestion(responseData) {
    // responseData is a RideRequestOut; we need to also show group info.
    // The group id lives in responseData.group_id.
    // We'll show what we have from the request response and then optionally
    // fetch group details.

    const card = document.getElementById('group-suggestion');
    if (!card) return;

    const groupId = responseData.group_id;

    // Show immediately with request-level info
    _setResultField('group-name',        groupId ? `Group #${groupId}` : 'Pending');
    _setResultField('group-destination', responseData.destination);
    _setResultField('group-date',        formatDate(responseData.travel_date));
    _setResultField('group-departure',   formatTime(responseData.preferred_time));
    _setResultField('group-passengers',  responseData.passenger_count);
    _setResultField('group-driver-status', 'Awaiting driver offer');

    card.removeAttribute('hidden');
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // If we have a group id, fetch full group info for enriched display
    if (groupId) {
        apiFetch(`/groups/${groupId}`)
            .then(group => {
                _setResultField('group-name',        `Group #${group.id} — ${group.destination_text}`);
                _setResultField('group-date',        formatDate(group.travel_date));
                _setResultField('group-departure',   formatTime(group.suggested_departure));
                _setResultField('group-passengers',  `${group.total_passengers} passenger(s) in group`);

                const offerStatus = group.driver_offer
                    ? `✅ Driver: ${group.driver_offer.driver_name} (${group.driver_offer.vehicle_type})`
                    : 'Awaiting driver offer';
                _setResultField('group-driver-status', offerStatus);

                // Show map if destination coords are available
                if (group.dest_lat && group.dest_lon) {
                    showPassengerMap(responseData, group);
                }
            })
            .catch(() => { /* enrichment is best-effort */ });
    }
}

function _setResultField(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value != null ? value : '—';
}

// ---------------------------------------------------------------------------
// Passenger map
// ---------------------------------------------------------------------------

function initPassengerMap() {
    if (typeof L === 'undefined') return;
    _passengerMap = initMap('passenger-map', [26.3, 91.6], 8);
}

function showPassengerMap(requestData, groupData) {
    const section = document.getElementById('passenger-map-section');
    if (!section || !_passengerMap) return;

    section.removeAttribute('hidden');
    clearMap(_passengerMap);
    _passengerMarkers = [];

    // Destination marker
    if (groupData.dest_lat && groupData.dest_lon) {
        const m = addMarker(_passengerMap, groupData.dest_lat, groupData.dest_lon,
            'Destination: ' + groupData.destination_text, 'green');
        _passengerMarkers.push(m);
    }

    // Route line from API if available
    if (groupData.route && groupData.route.coordinates && groupData.route.coordinates.length > 1) {
        drawRouteLine(_passengerMap, groupData.route.coordinates);
    }

    fitMarkers(_passengerMap, _passengerMarkers);
    // Trigger resize in case the section was previously hidden
    setTimeout(() => _passengerMap.invalidateSize(), 100);
}

// ---------------------------------------------------------------------------
// Load groups preview
// ---------------------------------------------------------------------------

async function loadGroupsPreview() {
    try {
        await apiFetch('/groups/');
        // Groups preview is optional; currently the page focuses on the passenger's own group
        // after submission. No-op here unless a dedicated preview element is added later.
    } catch (_) { /* non-critical */ }
}

/* map.js — Leaflet map utilities (passenger.html and driver.html) */

const OSM_TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const OSM_ATTRIBUTION = '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

// ---------------------------------------------------------------------------
// Map initialisation
// ---------------------------------------------------------------------------

/**
 * Create and return a Leaflet map inside the element with the given id.
 * @param {string} elementId  - DOM element id
 * @param {number[]} center   - [lat, lon] default center (Assam region)
 * @param {number}   zoom     - initial zoom level
 * @returns {L.Map}
 */
function initMap(elementId, center = [26.3, 91.6], zoom = 10) {
    const map = L.map(elementId, { center, zoom });
    L.tileLayer(OSM_TILE_URL, { attribution: OSM_ATTRIBUTION }).addTo(map);
    return map;
}

// ---------------------------------------------------------------------------
// Colored div-icon helper
// ---------------------------------------------------------------------------

/**
 * Build a small SVG circle icon for the given color.
 * @param {string} color - fill color
 * @returns {L.DivIcon}
 */
function _makeColorIcon(color) {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14">
        <circle cx="7" cy="7" r="6" fill="${color}" stroke="white" stroke-width="2"/>
    </svg>`;
    return L.divIcon({
        html: svg,
        className: '',          // clear Leaflet's default white box
        iconSize: [14, 14],
        iconAnchor: [7, 7],
        popupAnchor: [0, -9],
    });
}

// ---------------------------------------------------------------------------
// Markers
// ---------------------------------------------------------------------------

/**
 * Add a circle-marker to the map with a popup label.
 * @param {L.Map}    map
 * @param {number}   lat
 * @param {number}   lon
 * @param {string}   label
 * @param {string}   color  - 'orange' | 'green' | 'blue' (default)
 * @returns {L.Marker}
 */
function addMarker(map, lat, lon, label, color = 'blue') {
    const icon = _makeColorIcon(color);
    const marker = L.marker([lat, lon], { icon }).addTo(map);
    if (label) marker.bindPopup(label);
    return marker;
}

// ---------------------------------------------------------------------------
// Route line
// ---------------------------------------------------------------------------

/**
 * Draw a dashed polyline through the given coordinate array.
 * @param {L.Map}       map
 * @param {number[][]}  points - array of [lat, lon] pairs
 * @returns {L.Polyline}
 */
function drawRouteLine(map, points) {
    const line = L.polyline(points, {
        color: 'orange',
        weight: 3,
        dashArray: '8, 6',
        opacity: 0.85,
    }).addTo(map);
    return line;
}

// ---------------------------------------------------------------------------
// Fit bounds
// ---------------------------------------------------------------------------

/**
 * Adjust the map view to show all provided markers.
 * @param {L.Map}      map
 * @param {L.Marker[]} markers
 */
function fitMarkers(map, markers) {
    if (!markers || markers.length === 0) return;

    if (markers.length === 1) {
        map.setView(markers[0].getLatLng(), 13);
        return;
    }

    const bounds = L.latLngBounds(markers.map(m => m.getLatLng()));
    map.fitBounds(bounds, { padding: [40, 40] });
}

// ---------------------------------------------------------------------------
// Clear map layers (keeps tile layer)
// ---------------------------------------------------------------------------

/**
 * Remove all non-tile layers from the map.
 * @param {L.Map} map
 */
function clearMap(map) {
    map.eachLayer(layer => {
        if (!(layer instanceof L.TileLayer)) {
            map.removeLayer(layer);
        }
    });
}

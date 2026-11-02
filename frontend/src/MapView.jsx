import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { request } from './api';
import { Icon } from './icons';

const tileUrl = import.meta.env.VITE_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
export default function MapView({ coverage, source, destination, route, onPick, pickTarget, offline, setOffline }) {
  const container = useRef(null), map = useRef(null), tile = useRef(null);
  const routeLayers = useRef(null), markers = useRef(null), boundary = useRef(null), roads = useRef(null);
  const pickRef = useRef(onPick);
  const [mapError, setMapError] = useState('');
  useEffect(() => { pickRef.current = onPick; }, [onPick]);
  useEffect(() => {
    const instance = L.map(container.current, { zoomControl: false, preferCanvas: true, minZoom: 10 }).setView([28.60, 77.10], 12);
    map.current = instance;
    tile.current = L.tileLayer(tileUrl, { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' }).addTo(instance);
    tile.current.on('tileerror', () => setMapError('Map tiles unavailable. Use the offline road map.'));
    routeLayers.current = L.layerGroup().addTo(instance);
    markers.current = L.layerGroup().addTo(instance);
    L.control.zoom({ position: 'bottomright' }).addTo(instance);
    L.control.scale({ position: 'bottomleft', imperial: false }).addTo(instance);
    instance.on('click', event => pickRef.current({ lat: event.latlng.lat, lon: event.latlng.lng,
      name: `${event.latlng.lat.toFixed(5)}, ${event.latlng.lng.toFixed(5)}` }));
    const observer = new ResizeObserver(() => instance.invalidateSize());
    observer.observe(container.current);
    return () => { observer.disconnect(); instance.remove(); map.current = null; };
  }, []);
  useEffect(() => {
    if (!coverage || !map.current) return;
    const [s, w, n, e] = coverage.bbox;
    boundary.current?.remove();
    boundary.current = L.rectangle([[s, w], [n, e]], { color: '#527668', weight: 1.5, dashArray: '6 7', fillOpacity: 0, interactive: false }).addTo(map.current);
    map.current.setMaxBounds([[s - .09, w - .09], [n + .09, e + .09]]);
  }, [coverage]);
  useEffect(() => {
    if (!map.current) return;
    markers.current.clearLayers();
    for (const [place, letter, color] of [[source, 'A', '#245847'], [destination, 'B', '#c17a27']]) {
      if (!place) continue;
      const icon = L.divIcon({ className: 'place-pin', html: `<span style="background:${color}">${letter}</span>`, iconSize: [32, 42], iconAnchor: [16, 40] });
      const marker = L.marker([place.lat, place.lon], { icon, title: place.name }).addTo(markers.current);
      const label = document.createElement('span'); label.textContent = place.name; marker.bindTooltip(label);
    }
  }, [source, destination]);
  useEffect(() => {
    if (!map.current) return;
    routeLayers.current.clearLayers();
    if (!route) return;
    const latlngs = route.geometry.coordinates.map(([lon, lat]) => [lat, lon]);
    L.polyline(latlngs, { color: '#ffffff', weight: 10, opacity: .95 }).addTo(routeLayers.current);
    const line = L.polyline(latlngs, { color: '#275d48', weight: 5, opacity: 1 }).addTo(routeLayers.current);
    for (const [original, snapped] of [[source, route.snapped.source], [destination, route.snapped.destination]]) {
      if (original && snapped.distance_m > 5) L.polyline([[original.lat, original.lon], [snapped.lat, snapped.lon]],
        { color: '#9b733f', weight: 2, dashArray: '4 6', interactive: false }).addTo(routeLayers.current);
    }
    map.current.fitBounds(line.getBounds(), { padding: [70, 70], maxZoom: 16 });
  }, [route, source, destination]);
  useEffect(() => {
    if (!map.current) return;
    const controller = new AbortController();
    if (!offline) { roads.current?.remove(); tile.current.addTo(map.current); return; }
    tile.current.remove(); setMapError('');
    if (roads.current) roads.current.addTo(map.current);
    else request('/network', { signal: controller.signal }).then(data => {
      if (controller.signal.aborted || !map.current) return;
      roads.current = L.geoJSON(data, { style: { color: '#aebbad', weight: 1.5, opacity: .75 }, interactive: false });
      roads.current.addTo(map.current).bringToBack();
    }).catch(error => { if (!controller.signal.aborted) setMapError(error.message); });
    return () => controller.abort();
  }, [offline]);
  return <section className="map-area" aria-label="Interactive route map">
    <div ref={container} className="map-canvas" />
    <div className="map-topline"><span className="map-location"><span className="live-dot"/> DELHI NCR <span className="map-separator">/</span> PILOT AREA</span>
      <button className={`map-style ${offline ? 'selected' : ''}`} onClick={() => setOffline(!offline)} aria-pressed={offline}><Icon name="layers" size={17}/>{offline ? 'Offline roads' : 'Road map'}</button>
    </div>
    {!route && <div className="map-instruction"><Icon name="pin" size={16}/> Click the map to set your <strong>{pickTarget}</strong></div>}
    {mapError && <div className="map-error" role="status">{mapError} {!offline && <button onClick={() => setOffline(true)}>Use offline roads</button>}</div>}
    <div className="map-caption"><Icon name="compass" size={15}/><span>{offline ? 'Local OSM geometry · no map-tile connection needed' : 'Dwarka → Central Delhi · routes stay inside the dotted boundary'}</span></div>
    {offline && <div className="offline-attribution">© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> · ODbL</div>}
  </section>;
}

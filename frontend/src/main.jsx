import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import SearchBox from './SearchBox';
import MapView from './MapView';
import { API_BASE, request, distance, duration } from './api';
import { Icon } from './icons';
import './styles.css';
import { locateOrigin, ipEstimate } from './location';

function App() {
  const [source, setSource] = useState(null), [destination, setDestination] = useState(null);
  const [mode, setMode] = useState('driving'), [algorithm, setAlgorithm] = useState('world');
  const [health, setHealth] = useState(null);
  const [route, setRoute] = useState(null), [busy, setBusy] = useState(false);
  const [error, setError] = useState(''), [status, setStatus] = useState('Connecting to the routing API…');
  const [pickTarget, setPickTarget] = useState('source'), [offline, setOffline] = useState(false);
  const [info, setInfo] = useState(false), [locationState, setLocationState] = useState('idle');
  const [exampleBusy, setExampleBusy] = useState(false);
  const locationAbort = useRef(null);
  const cancelLocation = () => { locationAbort.current?.abort(); setLocationState('idle'); };
  const routeAbort = useRef(null), revision = useRef(0);
  const initAbort = useRef(null), modal = useRef(null);
  const initialize = async () => {
    initAbort.current?.abort(); const controller = new AbortController(); initAbort.current = controller;
    setStatus('Connecting… Free hosting may take a minute to wake up.');
    try {
      const h = await request('/health', { signal: controller.signal });
      if (controller.signal.aborted) return;
      setHealth(h); setStatus('Routing engine ready');
    } catch (err) { if (!controller.signal.aborted) setStatus(err.message); }
  };
  useEffect(() => { initialize(); return () => { initAbort.current?.abort(); routeAbort.current?.abort(); }; }, []);
  const invalidate = () => { revision.current++; routeAbort.current?.abort(); setBusy(false); setRoute(null); setError(''); };
  const updateSource = value => { cancelLocation(); invalidate(); setSource(value); };
  const updateDestination = value => { invalidate(); setDestination(value); };
  const pick = point => {
    if (pickTarget === 'source') { updateSource(point); setPickTarget('destination'); }
    else updateDestination(point);
  };
  const compute = async event => {
    event?.preventDefault(); if (!source || !destination) return;
    routeAbort.current?.abort(); const controller = new AbortController(); routeAbort.current = controller;
    const current = revision.current; setBusy(true); setError(''); setRoute(null);
    try {
      const result = await request('/route', { method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
        body: JSON.stringify({ source: { lat: source.lat, lon: source.lon }, destination: { lat: destination.lat, lon: destination.lon }, mode, algorithm }) });
      if (current === revision.current && !controller.signal.aborted) setRoute(result);
    } catch (err) { if (!controller.signal.aborted && current === revision.current) setError(err.message); }
    finally { if (current === revision.current) setBusy(false); }
  };
  const useLocation = async () => {
    locationAbort.current?.abort();
    const controller = new AbortController();
    locationAbort.current = controller;
    try {
      const place = await locateOrigin({geolocation:navigator.geolocation, fetchEstimate:ipEstimate,
        onStage:setLocationState, signal:controller.signal});
      if (controller.signal.aborted) return;
      invalidate(); setSource(place); setLocationState(place.method+'-ready'); setPickTarget('destination');
    } catch {
      if (!controller.signal.aborted) setLocationState('unavailable');
    }
  };
  useEffect(() => { useLocation(); return () => locationAbort.current?.abort(); }, []);
  const locationMessage = {gps:'Finding your GPS location…', ip:'Estimating your area from your IP…',
    'ip-ready':'Approximate origin from your IP. You can move the pin.', 'gps-ready':'Origin set from device location.',
    unavailable:'Location unavailable. Search for a place or select a point on the map.'}[locationState];
  const geoBusy = locationState==='gps' || locationState==='ip';
  const example = async (to = 'Vegas') => {
    cancelLocation(); invalidate(); setExampleBusy(true); const current = revision.current;
    try {
      const [a, b] = await Promise.all([request('/geocode?q=NSUT&scope=local'), request(`/geocode?scope=local&q=${encodeURIComponent(to)}`)]);
      if (current !== revision.current) return;
      if (!a.results.length || !b.results.length) throw new Error('This example is unavailable in the current extract. Search or choose points on the map.');
      setAlgorithm('astar'); setSource(a.results[0]); setDestination(b.results[0]); setPickTarget('destination');
    } catch (err) { if (current === revision.current) setError(err.message); }
    finally { setExampleBusy(false); }
  };
  useEffect(() => { if (info) modal.current?.showModal(); else modal.current?.close(); }, [info]);
  return <div className="app">
    <header className="topbar">
      <a className="brand" href="/" aria-label="Navic home"><span className="brand-mark"><Icon name="compass" size={26}/></span><span>navic<span className="brand-period">.</span></span></a>
      <div className="header-divider"/><span className="brand-tagline">A little clarity.<br/>A better way there.</span>
      <nav aria-label="Main navigation"><span className="nav-active">Route planner</span><button onClick={() => setInfo(true)}>Behind the route <Icon name="arrow" size={15}/></button></nav>
      <span className="project-label">BUILT ON OPEN MAPS <span>↗</span></span>
    </header>
    <nav className="panel-shortcuts" aria-label="Jump to a panel">
      <a href="#planner"><Icon name="route" size={17}/> Plan route</a>
      <a href="#route-map"><Icon name="pin" size={17}/> View map</a>
    </nav>
    <main className="workspace">
      <aside id="planner" className="sidebar" tabIndex={-1} aria-label="Route planner">
        <div className="planner-content">
          <div className="eyebrow"><span className="short-line"/> YOUR CITY, CONNECTED</div>
          <h1>Every journey<br/> starts <em>somewhere.</em></h1>
          <p className="intro">Find a road route anywhere in the world.</p>
          <div className="mode-tabs" role="group" aria-label="Travel mode">{[['driving', 'car', 'Drive'], ['walking', 'walk', 'Walk'], ['cycling', 'bike', 'Cycle']].map(([value, icon, label]) =>
            <button key={value} className={mode === value ? 'selected' : ''} aria-pressed={mode === value} onClick={() => { invalidate(); setMode(value); }}><Icon name={icon}/>{label}</button>)}</div>
          <form onSubmit={compute}>
            <div className="endpoints">
              <SearchBox label="STARTING POINT" value={source} onChange={updateSource} onEdit={cancelLocation} onFocus={() => setPickTarget('source')}/>
              <div className="origin-location"><button type="button" className="location-button" onClick={useLocation} disabled={geoBusy}><Icon name="locate" size={16}/>{geoBusy ? 'Locating…' : ['ip-ready','unavailable'].includes(locationState) ? 'Retry GPS' : 'Use my current location'}</button>
                <small role="status">{locationMessage}</small></div>
              <div className="endpoint-connector"/><button type="button" className="swap-button" aria-label="Swap source and destination" onClick={() => { cancelLocation(); invalidate(); setSource(destination); setDestination(source); }}><Icon name="swap" size={17}/></button>
              <SearchBox label="DESTINATION" value={destination} onChange={updateDestination} onFocus={() => setPickTarget('destination')} destination/>
            </div>

            <div className="algorithm-row"><label htmlFor="algorithm">Routing algorithm <span title="Local algorithms use the Delhi snapshot. Other locations use worldwide routing.">ⓘ</span></label><select id="algorithm" value={algorithm} onChange={event => { invalidate(); setAlgorithm(event.target.value); }}><option value="world">Worldwide routing</option><option value="astar">A* · Delhi demo</option><option value="dijkstra">Dijkstra · Delhi demo</option></select></div>
            <button className="route-button" disabled={!source || !destination || busy || !health} type="submit"><span>{busy ? 'Finding your way…' : 'Find my route'}</span>{busy ? <span className="spinner"/> : <Icon name="arrow" size={21}/>}</button>
          </form>
          {error && <div className="error-message" role="alert"><Icon name="info" size={18}/><span>{error}</span><button className="icon-button" aria-label="Dismiss error" onClick={() => setError('')}><Icon name="close" size={16}/></button></div>}
          {!health && <div className="connection-note" role="status">{status}<button onClick={initialize}>Retry connection</button></div>}
          {route ? <section className="route-result" aria-live="polite">
            <div className="result-heading"><span><Icon name="check" size={16}/> YOUR ROUTE IS READY</span><span className="result-mode">{mode}</span></div>
            <div className="route-metrics"><div><strong>{duration(route.duration_s)}</strong><span>Estimated travel time</span></div><div><strong>{distance(route.distance_m)}</strong><span>Road distance</span></div></div>
            <p className="route-caveat">{route.provider==='osrm' ? 'OSRM road route' : 'Shortest distance on the local graph'} · no live traffic<br/>Snapping gaps: {distance(route.snapped.source.distance_m)} at start, {distance(route.snapped.destination.distance_m)} at end.</p>
            <details className="directions" open><summary>Turn by turn <span>{route.steps.length} steps</span></summary><ol>{route.steps.map((step, index) => <li key={index}><span className="step-icon"><Icon name={step.maneuver === 'arrive' ? 'flag' : step.maneuver === 'left' ? 'left' : step.maneuver === 'right' ? 'right' : 'straight'} size={19}/></span><div><p>{step.instruction}</p>{step.distance_m > 0 && <small>{distance(step.distance_m)}</small>}</div></li>)}</ol></details>
            <details className="engine-details"><summary>Under the hood</summary><p>{route.provider==='osrm' ? 'Worldwide directions by OSRM / FOSSGIS.' : route.cached ? 'Route served from the in-memory cache; no new search performed.' : `${route.visited_nodes.toLocaleString()} nodes visited in ${route.search_ms.toFixed(2)} ms (search only).`}</p><p>{route.provider==='osrm' ? 'OSRM chose the route for the selected travel mode.' : algorithm === 'astar' ? 'A* with a haversine distance heuristic.' : 'Dijkstra with nonnegative distance weights.'}</p><ul>{route.warnings.map(warning => <li key={warning}>{warning}</li>)}</ul></details>
          </section> : <section className="explore">
            <div className="section-heading"><h2>A good place to start</h2><span>TRY A JOURNEY</span></div>
            <button className="journey-card" disabled={exampleBusy || !health} onClick={() => example()}><span className="journey-art"><Icon name="route" size={28}/></span><span><strong>From campus to a coffee</strong><small>NSUT → Vegas Mall, Dwarka</small></span><Icon name="arrow" size={17}/></button>
            <button className="journey-card" disabled={exampleBusy || !health} onClick={() => example('India Gate')}><span className="journey-art warm"><Icon name="compass" size={28}/></span><span><strong>Take the city route</strong><small>NSUT → India Gate</small></span><Icon name="arrow" size={17}/></button>
            <div className="map-tip"><Icon name="pin" size={17}/><p>Have a spot in mind?<br/><strong>Choose your endpoints directly on the map.</strong></p></div>
          </section>}
        </div>
        <footer className="sidebar-footer"><span className={`status-dot ${health ? '' : 'pending'}`}/><span>{health ? 'Connected to Navic routing' : 'Waiting for the routing engine'}</span><button onClick={() => setInfo(true)} aria-label="About this project"><Icon name="info" size={16}/></button></footer>
      </aside>
      <MapView source={source} destination={destination} route={route} onPick={pick} pickTarget={pickTarget} offline={offline} setOffline={setOffline}/>
    </main>
    <dialog ref={modal} className="about-dialog" onCancel={() => setInfo(false)} onClick={event => { if (event.target === modal.current) setInfo(false); }}>
      <button className="dialog-close icon-button" onClick={() => setInfo(false)} aria-label="Close project information"><Icon name="close"/></button>
      <div className="eyebrow">BEHIND THE ROUTE</div><h2>Open roads.<br/><em>Understandable algorithms.</em></h2>
      <p>Navic is a minor-project navigator built with a C++17 API, React and Leaflet. Dijkstra and A* are implemented from scratch on real OpenStreetMap data.</p>
      <div className="about-stats"><div><strong>{health?.nodes.toLocaleString() || '—'}</strong><span>graph nodes</span></div><div><strong>{health?.edges.toLocaleString() || '—'}</strong><span>directed edges</span></div></div>
      <p><strong>Coverage:</strong> Worldwide place search by Photon and routes by OSRM / FOSSGIS. The Delhi demos also work with a bundled graph and place index.</p>
      <p><strong>Be aware:</strong> local demo routes minimize road distance. ETA excludes traffic, signals and snapping gaps. Basic instructions do not account for turn restrictions, barriers or conditional access. This is an educational prototype.</p>
      <p><strong>Offline demo:</strong> run the local API and select “Road map” to switch to bundled road geometry. Offline road geometry covers Delhi. GPS is requested first. If unavailable, FreeIPAPI estimates your area from your IP; search queries go to Photon and worldwide route endpoints go to OSRM.</p>
      <a className="docs-link" href={`${API_BASE}/docs`} target="_blank" rel="noreferrer">Explore the API documentation <Icon name="arrow" size={17}/></a>
      <small>Map data © OpenStreetMap contributors, ODbL. <a href="https://www.openstreetmap.org/fixthemap" target="_blank" rel="noreferrer">Report a map issue</a>.</small>
    </dialog>
  </div>;
}
createRoot(document.getElementById('root')).render(<App/>);

import React, { useEffect, useId, useRef, useState } from 'react';
import { request } from './api';
import { Icon } from './icons';

export default function SearchBox({ label, value, onChange, onFocus, destination }) {
  const id = useId();
  const [text, setText] = useState(value?.name || '');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [active, setActive] = useState(-1);
  const root = useRef(null);
  const editing = useRef(false);
  useEffect(() => {
    if (editing.current) { editing.current = false; return; }
    setText(value?.name || ''); setOpen(false);
  }, [value]);
  useEffect(() => {
    const close = event => { if (!root.current?.contains(event.target)) setOpen(false); };
    document.addEventListener('pointerdown', close);
    return () => document.removeEventListener('pointerdown', close);
  }, []);
  useEffect(() => {
    if (!open || text.trim().length < 2 || value?.name === text) { setResults([]); setBusy(false); return; }
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setBusy(true); setError('');
      try {
        const data = await request(`/geocode?q=${encodeURIComponent(text.trim())}&limit=6`, { signal: controller.signal });
        setResults(data.results); setActive(-1);
      } catch (err) { if (!controller.signal.aborted) setError(err.message); }
      finally { if (!controller.signal.aborted) setBusy(false); }
    }, 300);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [text, open, value]);
  const choose = place => { onChange(place); setText(place.name); setOpen(false); setResults([]); };
  return <div className={`search-field ${destination ? 'destination-field' : ''}`} ref={root}>
    <span className={`endpoint-dot ${destination ? 'end' : ''}`} aria-hidden="true" />
    <div className="input-wrap">
      <label htmlFor={id}>{label}</label>
      <input id={id} role="combobox" aria-autocomplete="list" aria-expanded={open && text.length >= 2}
        aria-controls={`${id}-results`} aria-activedescendant={active >= 0 ? `${id}-${active}` : undefined}
        autoComplete="off" placeholder={destination ? 'Where are you heading?' : 'Choose a starting point'} value={text}
        onFocus={() => { setOpen(true); onFocus(); }}
        onChange={event => { const next = event.target.value; if (value) { editing.current = true; onChange(null); } setText(next); setOpen(true); setActive(-1); }}
        onKeyDown={event => {
          if (event.key === 'Escape') setOpen(false);
          if (event.key === 'ArrowDown' && results.length) { event.preventDefault(); setActive(i => Math.min(i + 1, results.length - 1)); }
          if (event.key === 'ArrowUp' && results.length) { event.preventDefault(); setActive(i => Math.max(i - 1, 0)); }
          if (event.key === 'Enter' && open && results.length) { event.preventDefault(); choose(results[Math.max(0, active)]); }
        }} />
    </div>
    {value && <button className="clear-input icon-button" type="button" aria-label={`Clear ${label.toLowerCase()}`} onClick={() => { onChange(null); setText(''); }}><Icon name="close" size={15}/></button>}
    {open && text.trim().length >= 2 && value?.name !== text && <div className="suggestions" id={`${id}-results`} role="listbox" aria-label={`${label} suggestions`}>
      {busy ? <p>Searching Delhi places…</p> : error ? <p role="alert">{error}</p> : results.length === 0 ? <p>No match yet. Try a landmark, road, or click the map.</p> : results.map((place, i) =>
        <button key={place.id} id={`${id}-${i}`} role="option" aria-selected={active === i} type="button"
          className={active === i ? 'active' : ''} onClick={() => choose(place)}>
          <Icon name="pin" size={18}/><span><strong>{place.name}</strong><small>{place.kind.replaceAll('_', ' ')} · Delhi pilot</small></span>
        </button>)}
    </div>}
  </div>;
}

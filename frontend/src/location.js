// Browser-side IP lookup estimates the visitor, rather than the API host.
export async function locateOrigin({ geolocation, fetchEstimate, onStage, signal }) {
  function point(lat, lon, method) {
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat)>90 || Math.abs(lon)>180)
      throw new Error('Location service returned invalid coordinates.');
    return {lat, lon, method, name:method==='gps' ? 'Current location' : 'Approximate location (IP)'};
  }
  onStage('gps');
  try {
    if (!geolocation) throw new Error('Geolocation unavailable');
    const position = await new Promise((resolve,reject) => geolocation.getCurrentPosition(resolve,reject,
      {enableHighAccuracy:true, timeout:10000, maximumAge:0}));
    signal.throwIfAborted();
    return point(position.coords.latitude,position.coords.longitude,'gps');
  } catch {
    signal.throwIfAborted();
    onStage('ip');
    const data = await fetchEstimate(signal);
    signal.throwIfAborted();
    return point(data.latitude,data.longitude,'ip');
  }
}

export async function ipEstimate(signal) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (signal.aborted) abort();
  signal.addEventListener('abort',abort,{once:true});
  const timer = setTimeout(abort,6000);
  try {
    const response = await fetch(import.meta.env.VITE_IP_LOCATION_URL || 'https://free.freeipapi.com/api/v1/json/',
      {signal:controller.signal,credentials:'omit',referrerPolicy:'no-referrer',cache:'no-store'});
    if (!response.ok) throw new Error('IP estimate unavailable');
    return await response.json();
  } finally {
    clearTimeout(timer);
    signal.removeEventListener('abort',abort);
  }
}

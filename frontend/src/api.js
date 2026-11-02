export const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export async function request(path, { signal, ...options } = {}) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (signal?.aborted) controller.abort();
  signal?.addEventListener('abort', abort, { once: true });
  const timeout = setTimeout(abort, 90000); // accommodates a sleeping free API
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...options, signal: controller.signal });
    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('json')) {
      throw new Error('The API may be waking up. Wait a minute, then retry.');
    }
    const body = await response.json();
    if (!response.ok) throw new Error(body.error?.message || `Request failed (${response.status})`);
    return body;
  } catch (error) {
    if (controller.signal.aborted && !signal?.aborted) throw new Error('The API took too long to respond. It may be waking up; please retry.');
    if (error instanceof TypeError) throw new Error('Cannot reach the API. Check your connection and retry.');
    throw error;
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener('abort', abort);
  }
}

export const distance = meters => meters < 1000 ? `${Math.round(meters)} m` : `${(meters / 1000).toFixed(1)} km`;
export const duration = seconds => {
  if (seconds === 0) return '0 min';
  const minutes = Math.max(1, Math.round(seconds / 60));
  return minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)} hr ${minutes % 60} min`;
};

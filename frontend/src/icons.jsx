import React from 'react';

const paths = {
  compass: <><path d="m12 3 7 17-7-4-7 4Z"/><path d="M12 3v13"/></>,
  arrow: <><path d="M4 12h16m-6-6 6 6-6 6"/></>,
  pin: <><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2.5"/></>,
  car: <><path d="m5 7 2-4h10l2 4 2 3v8H3v-8l2-3Zm0 0h14M3 11h18M6 18v3m12-3v3"/><path d="M6 14h2m8 0h2"/></>,
  walk: <><circle cx="14" cy="4" r="2"/><path d="m7 21 4-7 2-6 3 4 4 1M5 12l5-4 3 1m-2 5 5 3 1 4"/></>,
  bike: <><circle cx="5" cy="16" r="4"/><circle cx="19" cy="16" r="4"/><path d="m5 16 6-9 8 9M8 6h5m-3 5 4 5H5m10-13h3l2 4"/></>,
  swap: <><path d="M8 3v16m-4-4 4 4 4-4m4 6V5m-4 4 4-4 4 4"/></>,
  locate: <><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4"/></>,
  layers: <><path d="m12 3 10 6-10 6L2 9Zm-9 11 9 5 9-5m-18 5 9 5 9-5"/></>,
  info: <><circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/></>,
  close: <path d="m6 6 12 12M6 18 18 6"/>,
  right: <path d="M6 21V10h13m-5-5 5 5-5 5"/>,
  left: <path d="M18 21V10H5m5-5-5 5 5 5"/>,
  straight: <path d="M12 21V3M6 9l6-6 6 6"/>,
  flag: <><path d="M5 22V3m0 1c6-5 8 5 15 0v11c-7 5-9-5-15 0"/></>,
  clock: <><circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/></>,
  route: <><circle cx="5" cy="5" r="2"/><circle cx="19" cy="19" r="2"/><path d="M5 7v9a3 3 0 0 0 3 3h9M7 5h9a3 3 0 0 1 0 6H8"/></>,
  check: <path d="m5 12 4 4L19 6"/>,
};
export function Icon({ name, size = 20, ...props }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name] || paths.straight}</svg>;
}

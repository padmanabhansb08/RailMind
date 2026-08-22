/* eslint-disable */
import React, { useState, useEffect } from 'react';

export const API_BASE = `http://${window.location.hostname}:8000`;

// The four states a probe in backend/services/health.py can report, plus
// "unknown" for when we cannot reach the API at all — which must never be
// rendered as healthy.
export const STATUS_META = {
  ok:             { label: 'Operational',     color: '#10b981' },
  degraded:       { label: 'Degraded',        color: '#f59e0b' },
  down:           { label: 'Down',            color: '#ef4444' },
  not_configured: { label: 'Not configured',  color: '#64748b' },
  unknown:        { label: 'Unreachable',     color: '#ef4444' }
};

export const statusMeta = (status) => STATUS_META[status] || STATUS_META.unknown;

export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return null;
  if (seconds < 90) return `${Math.round(seconds)} sec`;
  if (seconds < 5400) return `${(seconds / 60).toFixed(1)} min`;
  return `${(seconds / 3600).toFixed(1)} hr`;
}

// Polls the live health endpoint. On any failure the whole system reads as
// unreachable rather than falling back to the last-known-good snapshot.
export function useSystemStatus(intervalMs = 10000) {
  const [status, setStatus] = useState(null);
  const [reachable, setReachable] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/system-status`);
        if (!res.ok) throw new Error(`Server responded ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          setStatus(data);
          setReachable(true);
        }
      } catch (err) {
        console.error("[API] system-status unreachable:", err);
        if (!cancelled) setReachable(false);
      }
    };

    load();
    const timer = setInterval(load, intervalMs);
    return () => { cancelled = true; clearInterval(timer); };
  }, [intervalMs]);

  return { status, reachable };
}

export function StatusDot({ status }) {
  const { color } = statusMeta(status);
  return (
    <span style={{
      width: '8px',
      height: '8px',
      borderRadius: '50%',
      backgroundColor: color,
      boxShadow: `0 0 6px ${color}`,
      flexShrink: 0
    }} />
  );
}

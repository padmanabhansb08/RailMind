/* eslint-disable */
import React, { useState } from 'react';
import { FlaskConical, AlertTriangle, Check, ArrowRight } from 'lucide-react';
import { API_BASE } from '../systemStatus';

/* Kept as a top-level component rather than a closure inside App: defined
   inline, React remounted it on every parent render — and this screen re-renders
   on every websocket message — so a half-typed station name or the result of an
   injection was wiped a second after it appeared. */

const label = {
  fontSize: '12px',
  color: '#8b949e',
  fontWeight: 500,
  marginBottom: '7px',
  display: 'block',
};

const field = {
  backgroundColor: 'var(--bg-panel)',
  border: '1px solid var(--border-color)',
  color: '#f0f6fc',
  padding: '10px 12px',
  fontSize: '13px',
  outline: 'none',
  borderRadius: '7px',
  width: '100%',
  fontFamily: 'inherit',
};

const panel = {
  backgroundColor: 'var(--bg-main)',
  border: '1px solid var(--border-color)',
  borderRadius: '10px',
  padding: '22px 24px',
};

const STEPS = [
  'The train’s live telemetry is overridden with the delay, status and station you set.',
  'The detection rules re-run over the whole tracked fleet, including the overridden train.',
  'The reasoning model assesses the situation; if it is unreachable, a plan is derived from the recorded telemetry instead.',
  'Department tasks and the passenger notice are drafted, and the route graph is checked for a usable detour.',
  'An incident is written to the queue and appears under Incident Alerts, awaiting your decision.',
];

export default function SimulationPortal({ trains = [], onRefresh, onOpenIncidents }) {
  const [selectedTrain, setSelectedTrain] = useState(trains[0]?.train_number || '12301');
  const [delayMinutes, setDelayMinutes] = useState(60);
  const [status, setStatus] = useState('Delayed');
  const [currentStation, setCurrentStation] = useState('Kanpur Central');
  const [isInjecting, setIsInjecting] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [result, setResult] = useState(null);

  const handleInject = async () => {
    setIsInjecting(true);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/simulate-anomaly`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          train_number: selectedTrain,
          delay_minutes: parseInt(delayMinutes, 10) || 0,
          status,
          current_station: currentStation,
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (res.ok) {
        setResult(body);
        if (onRefresh) onRefresh();
      } else {
        setResult({ error: body.detail || `The API rejected the injection (${res.status}).` });
      }
    } catch (err) {
      console.error('[SIMULATION] Injection failed:', err);
      setResult({ error: 'Could not reach the RailMind API.' });
    } finally {
      setIsInjecting(false);
    }
  };

  const handleReset = async () => {
    setIsResetting(true);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/reset-simulation`, { method: 'POST' });
      if (res.ok && onRefresh) onRefresh();
      if (!res.ok) setResult({ error: `Reset failed (${res.status}).` });
    } catch (err) {
      console.error('[SIMULATION] Reset failed:', err);
      setResult({ error: 'Could not reach the RailMind API.' });
    } finally {
      setIsResetting(false);
    }
  };

  const resultTone = result?.error
    ? { border: 'rgba(248,113,113,.4)', bg: 'rgba(248,113,113,.06)', fg: '#fca5a5', title: 'Injection failed' }
    : result?.incident_raised
      ? { border: 'rgba(52,211,153,.35)', bg: 'rgba(52,211,153,.05)', fg: '#34d399', title: 'Incident raised' }
      : { border: 'var(--border-color)', bg: 'var(--bg-panel)', fg: '#c9d1d9', title: 'No incident raised' };

  return (
    <div style={{ padding: '26px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '22px' }}>
      <header>
        <h2 style={{ fontSize: '19px', fontWeight: 600, color: '#f0f6fc', margin: 0 }}>Simulation portal</h2>
        <p style={{ fontSize: '13px', color: '#8b949e', margin: '5px 0 0', lineHeight: 1.6, maxWidth: '68ch' }}>
          Override a train&rsquo;s live telemetry and run one full response cycle against it. Incidents
          raised this way are marked as simulated wherever they appear.
        </p>
      </header>

      <div style={{ display: 'flex', gap: '22px', flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <section style={{ ...panel, flex: 2, minWidth: '380px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <h3 style={{
            fontSize: '13px', fontWeight: 600, color: '#c9d1d9', margin: 0,
            borderBottom: '1px solid var(--border-color)', paddingBottom: '12px',
          }}>
            Injection
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '18px' }}>
            <div>
              <label style={label} htmlFor="sim-train">Train</label>
              <select id="sim-train" value={selectedTrain} onChange={(e) => setSelectedTrain(e.target.value)} style={field}>
                {trains.length === 0 && <option value={selectedTrain}>{selectedTrain}</option>}
                {trains.map((t) => (
                  <option key={t.train_number} value={t.train_number}>
                    {t.train_number} — {t.train_name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={label} htmlFor="sim-status">Status</label>
              <select id="sim-status" value={status} onChange={(e) => setStatus(e.target.value)} style={field}>
                <option value="Delayed">Delayed</option>
                <option value="Cancelled">Cancelled</option>
                <option value="Overcrowded">Overcrowded</option>
                <option value="On Time">On time</option>
              </select>
            </div>

            <div>
              <label style={label} htmlFor="sim-delay">Delay (minutes)</label>
              <input
                id="sim-delay"
                type="number"
                min="0"
                max="480"
                value={delayMinutes}
                onChange={(e) => setDelayMinutes(e.target.value)}
                style={field}
              />
              <span style={{ fontSize: '11px', color: '#6e7681', display: 'block', marginTop: '6px' }}>
                Detection triggers above 15 min; 60+ is treated as high severity.
              </span>
            </div>

            <div>
              <label style={label} htmlFor="sim-station">Station</label>
              <input
                id="sim-station"
                type="text"
                value={currentStation}
                onChange={(e) => setCurrentStation(e.target.value)}
                style={field}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <button
              onClick={handleInject}
              disabled={isInjecting || isResetting}
              style={{
                flex: '1 1 220px',
                padding: '12px 20px',
                backgroundColor: '#e6edf3',
                color: '#0d1117',
                border: '1px solid #e6edf3',
                borderRadius: '7px',
                fontWeight: 600,
                fontSize: '13px',
                fontFamily: 'inherit',
                cursor: isInjecting ? 'default' : 'pointer',
                opacity: isInjecting ? 0.65 : 1,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
              }}
            >
              <FlaskConical size={15} />
              {isInjecting ? 'Running the cycle…' : 'Inject anomaly'}
            </button>

            <button
              onClick={handleReset}
              disabled={isInjecting || isResetting}
              style={{
                padding: '12px 20px',
                backgroundColor: 'transparent',
                color: '#8b949e',
                border: '1px solid var(--border-color)',
                borderRadius: '7px',
                fontWeight: 600,
                fontSize: '13px',
                fontFamily: 'inherit',
                cursor: 'pointer',
              }}
            >
              {isResetting ? 'Resetting…' : 'Reset all overrides'}
            </button>
          </div>

          {isInjecting && (
            <p style={{ fontSize: '12px', color: '#8b949e', lineHeight: 1.6, margin: 0 }}>
              Detection, assessment and dispatch are running against the live fleet. This can take
              up to a minute.
            </p>
          )}

          {result && !isInjecting && (
            <div style={{
              border: `1px solid ${resultTone.border}`,
              backgroundColor: resultTone.bg,
              borderRadius: '8px',
              padding: '15px 17px',
              display: 'flex',
              flexDirection: 'column',
              gap: '9px',
            }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: resultTone.fg, display: 'flex', alignItems: 'center', gap: '8px' }}>
                {result.error ? <AlertTriangle size={14} /> : result.incident_raised ? <Check size={14} /> : null}
                {resultTone.title}
              </span>
              <span style={{ fontSize: '12px', color: '#8b949e', lineHeight: 1.6 }}>
                {result.error || result.detail}
              </span>
              {result.incident?.incident_title && (
                <span style={{ fontSize: '13px', color: '#f0f6fc', lineHeight: 1.6 }}>
                  {result.incident.incident_title}
                </span>
              )}
              {!result.error && onOpenIncidents && (
                <button
                  onClick={onOpenIncidents}
                  style={{
                    alignSelf: 'flex-start',
                    marginTop: '3px',
                    padding: '9px 15px',
                    backgroundColor: 'transparent',
                    border: '1px solid var(--border-color)',
                    borderRadius: '7px',
                    color: '#c9d1d9',
                    fontSize: '12px',
                    fontWeight: 600,
                    fontFamily: 'inherit',
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '7px',
                  }}
                >
                  Open Incident Alerts <ArrowRight size={13} />
                </button>
              )}
            </div>
          )}
        </section>

        <section style={{ ...panel, flex: 1, minWidth: '300px' }}>
          <h3 style={{
            fontSize: '13px', fontWeight: 600, color: '#c9d1d9', margin: '0 0 16px',
            borderBottom: '1px solid var(--border-color)', paddingBottom: '12px',
          }}>
            What happens next
          </h3>
          <ol style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {STEPS.map((step, i) => (
              <li key={i} style={{ display: 'flex', gap: '12px', fontSize: '12px', color: '#8b949e', lineHeight: 1.7 }}>
                <span style={{ color: '#6e7681', fontWeight: 600, flexShrink: 0 }}>{i + 1}</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </div>
  );
}

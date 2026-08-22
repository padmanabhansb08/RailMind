/* eslint-disable */
import React, { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, Check, X, Pencil, RotateCcw, ChevronDown, ChevronRight, Clock, Repeat, Network } from 'lucide-react';
import { API_BASE } from '../systemStatus';

const SEVERITY_COLOR = {
  critical: '#ef4444',
  high: '#ef4444',
  severe: '#ef4444',
  warning: '#f59e0b',
  medium: '#f59e0b',
  low: '#06b6d4',
  info: '#64748b'
};

const severityColor = (s) => SEVERITY_COLOR[String(s).toLowerCase()] || '#64748b';

const STATUS_LABEL = {
  approved: 'Approved',
  overridden: 'Modified',
  rejected: 'Rejected',
  acknowledged: 'Acknowledged'
};

const btn = (bg, fg, extra = {}) => ({
  padding: '8px 14px',
  backgroundColor: bg,
  color: fg,
  border: bg === 'transparent' ? '1px solid var(--border-color)' : 'none',
  borderRadius: '8px',
  fontSize: '11px',
  fontWeight: 700,
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  transition: 'opacity 0.15s',
  ...extra
});

const inputStyle = {
  backgroundColor: 'var(--bg-main)',
  border: '1px solid var(--border-color)',
  borderRadius: '6px',
  color: '#f8fafc',
  padding: '8px 10px',
  fontSize: '12px',
  outline: 'none',
  width: '100%',
  fontFamily: 'inherit'
};

// Why this card sits where it does. Operators won't trust an ordering they
// can't interrogate, so the score is always openable.
function ScoreBreakdown({ card }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        style={{
          background: 'transparent', border: 'none', color: '#64748b',
          fontSize: '10px', cursor: 'pointer', display: 'flex',
          alignItems: 'center', gap: '4px', padding: 0
        }}
      >
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
        Priority {card.score} — why?
      </button>
      {open && (
        <div style={{
          marginTop: '8px', padding: '10px 12px', backgroundColor: 'var(--bg-main)',
          border: '1px solid var(--border-color)', borderRadius: '6px',
          display: 'flex', flexDirection: 'column', gap: '5px'
        }}>
          {card.score_breakdown.map((b) => (
            <div key={b.factor} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
              <span style={{ color: '#94a3b8' }}>{b.factor} <span style={{ color: '#64748b' }}>({b.value})</span></span>
              <span style={{ color: b.points > 0 ? '#cbd5e1' : '#475569', fontWeight: 600 }}>+{b.points}</span>
            </div>
          ))}
          <div style={{
            display: 'flex', justifyContent: 'space-between', fontSize: '11px',
            borderTop: '1px solid var(--border-color)', paddingTop: '5px', marginTop: '2px'
          }}>
            <span style={{ color: '#f8fafc', fontWeight: 700 }}>Total</span>
            <span style={{ color: '#f8fafc', fontWeight: 700 }}>{card.score}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// Trains heading into the same station. Worded as convergence, never as a
// prediction of delay — the feed has no track topology to justify that claim.
function NetworkImpact({ impact }) {
  const [open, setOpen] = useState(false);
  if (!impact) return null;

  if (!impact.matched) {
    return (
      <div style={{ fontSize: '10px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '5px' }}>
        <Network size={11} /> Network impact unknown — {impact.reason}
      </div>
    );
  }

  if (impact.count === 0) {
    return (
      <div style={{ fontSize: '10px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '5px' }}>
        <Network size={11} /> No other train is at or approaching {impact.station} in the live feed
      </div>
    );
  }

  const soonest = impact.next_arrival_in;
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        style={{
          background: 'transparent', border: 'none', color: '#38bdf8', padding: 0,
          fontSize: '11px', fontWeight: 600, cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: '5px', textAlign: 'left'
        }}
      >
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
        <Network size={12} />
        {impact.count} train{impact.count === 1 ? '' : 's'} converging on {impact.station}
        {soonest != null && <span style={{ color: '#64748b', fontWeight: 500 }}>· next in {soonest} min</span>}
      </button>

      {open && (
        <div style={{
          marginTop: '8px', padding: '10px 12px', backgroundColor: 'var(--bg-main)',
          border: '1px solid var(--border-color)', borderRadius: '6px',
          display: 'flex', flexDirection: 'column', gap: '6px'
        }}>
          {impact.trains.map((t) => (
            <div key={t.train_number} style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', fontSize: '11px' }}>
              <span style={{ color: '#cbd5e1', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                <span style={{ color: '#38bdf8', fontWeight: 600 }}>{t.train_number}</span>{' '}{t.train_name}
              </span>
              <span style={{ color: t.relation === 'at_station' ? '#f59e0b' : '#94a3b8', flexShrink: 0, fontWeight: 500 }}>
                {t.relation === 'at_station' ? 'at station' : `in ${t.arrives_in_minutes} min`}
              </span>
            </div>
          ))}
          {impact.truncated > 0 && (
            <span style={{ fontSize: '10px', color: '#64748b' }}>+{impact.truncated} more</span>
          )}
          <span style={{ fontSize: '10px', color: '#475569', borderTop: '1px solid var(--border-color)', paddingTop: '6px', lineHeight: 1.5 }}>
            Scheduled to arrive at this station within {impact.window_minutes} min. Convergence only —
            the live feed carries no track or platform data, so this does not predict which will be delayed.
          </span>
        </div>
      )}
    </div>
  );
}

function DecisionCard({ card, rank, onDecide, busy }) {
  const [mode, setMode] = useState(null);       // 'approve' | 'modify' | 'reject'
  const [password, setPassword] = useState('');
  const [plan, setPlan] = useState(card.proposed_plan || '');
  const [reason, setReason] = useState('');
  const [error, setError] = useState(null);

  const color = severityColor(card.severity);
  const decided = card.resolution_status !== 'pending';

  const reset = () => { setMode(null); setPassword(''); setReason(''); setError(null); };

  const submit = async (action, extra = {}) => {
    setError(null);
    const err = await onDecide(card.id, action, extra);
    if (err) setError(err); else reset();
  };

  return (
    <div style={{
      backgroundColor: 'var(--bg-panel)',
      border: '1px solid var(--border-color)',
      borderLeft: `4px solid ${decided ? '#334155' : color}`,
      borderRadius: '10px',
      padding: '18px 20px',
      display: 'flex',
      flexDirection: 'column',
      gap: '14px',
      opacity: decided ? 0.65 : 1
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '14px' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start', minWidth: 0 }}>
          <span style={{
            fontSize: '13px', fontWeight: 700, color: '#475569',
            minWidth: '22px', paddingTop: '1px'
          }}>{rank}</span>
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '5px' }}>
              <span style={{
                fontSize: '9px', fontWeight: 700, color, textTransform: 'uppercase',
                border: `1px solid ${color}`, backgroundColor: `${color}14`,
                padding: '2px 7px', borderRadius: '4px'
              }}>{card.severity}</span>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                {card.train_number}{card.train_name ? ` · ${card.train_name}` : ''}
              </span>
              {card.station && <span style={{ fontSize: '11px', color: '#64748b' }}>@ {card.station}</span>}
            </div>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#f8fafc', lineHeight: 1.4 }}>
              {card.title || 'Operations anomaly'}
            </h3>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '5px', flexShrink: 0 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: '#64748b' }}>
            <Clock size={11} /> {card.age_label} unanswered
          </span>
          {card.recurrence > 1 && (
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: '#f59e0b' }}>
              <Repeat size={11} /> {card.recurrence}× recurrence
            </span>
          )}
        </div>
      </div>

      {/* Why it happened */}
      {card.situation_summary && (
        <p style={{ fontSize: '12px', color: '#cbd5e1', lineHeight: 1.6, margin: 0 }}>
          {card.situation_summary}
        </p>
      )}

      {/* Cost of doing nothing */}
      <div style={{
        display: 'flex', gap: '8px', alignItems: 'flex-start',
        backgroundColor: 'rgba(245, 158, 11, 0.06)',
        border: '1px solid rgba(245, 158, 11, 0.25)',
        borderRadius: '6px', padding: '10px 12px'
      }}>
        <AlertTriangle size={13} style={{ color: '#f59e0b', flexShrink: 0, marginTop: '1px' }} />
        <span style={{ fontSize: '11px', color: '#fcd34d', lineHeight: 1.5 }}>{card.inaction_note}</span>
      </div>

      {/* The proposed action and its concrete consequences */}
      {(card.proposed_plan || card.dispatches?.length > 0) && (
        <div style={{
          backgroundColor: 'var(--bg-main)', border: '1px solid var(--border-color)',
          borderRadius: '6px', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: '10px'
        }}>
          <span style={{ fontSize: '9px', fontWeight: 700, color: '#64748b', letterSpacing: '0.5px' }}>
            PROPOSED PLAN
          </span>
          <span style={{ fontSize: '12px', color: '#f8fafc', lineHeight: 1.5 }}>
            {card.proposed_plan || 'No reroute proposed.'}
          </span>
          {card.dispatches?.length > 0 && (
            <>
              <span style={{ fontSize: '9px', fontWeight: 700, color: '#64748b', letterSpacing: '0.5px', marginTop: '2px' }}>
                APPROVING DISPATCHES {card.dispatches.length} TASK{card.dispatches.length === 1 ? '' : 'S'}
              </span>
              {card.dispatches.map((d) => (
                <div key={d.department} style={{ display: 'flex', gap: '8px', fontSize: '11px', lineHeight: 1.5 }}>
                  <span style={{ color: '#06b6d4', fontWeight: 600, minWidth: '100px', flexShrink: 0 }}>{d.department}</span>
                  <span style={{ color: '#94a3b8' }}>{d.task}</span>
                </div>
              ))}
            </>
          )}
        </div>
      )}

      <NetworkImpact impact={card.network_impact} />

      <ScoreBreakdown card={card} />

      {error && (
        <div style={{ fontSize: '11px', color: '#fca5a5', backgroundColor: 'rgba(239,68,68,0.08)', border: '1px solid #ef4444', borderRadius: '6px', padding: '8px 10px' }}>
          {error}
        </div>
      )}

      {/* Decision surface */}
      {decided ? (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
          <span style={{ fontSize: '11px', color: '#94a3b8' }}>
            {STATUS_LABEL[card.resolution_status] || card.resolution_status}
            {card.decisions?.length > 0 && (
              <span style={{ color: '#64748b' }}>
                {' '}by {card.decisions[card.decisions.length - 1].actor}
                {card.decisions[card.decisions.length - 1].reason
                  ? ` — "${card.decisions[card.decisions.length - 1].reason}"` : ''}
              </span>
            )}
          </span>
          <button
            disabled={busy}
            onClick={() => submit('undo')}
            style={btn('transparent', '#94a3b8')}
          >
            <RotateCcw size={12} /> UNDO
          </button>
        </div>
      ) : mode === null ? (
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
          <button disabled={busy} onClick={() => setMode('approve')} style={btn('#10b981', '#04120c')}>
            <Check size={13} /> APPROVE PLAN
          </button>
          <button disabled={busy} onClick={() => setMode('modify')} style={btn('transparent', '#cbd5e1')}>
            <Pencil size={12} /> MODIFY
          </button>
          <button disabled={busy} onClick={() => setMode('reject')} style={btn('transparent', '#fca5a5')}>
            <X size={12} /> REJECT
          </button>
          <button disabled={busy} onClick={() => submit('acknowledge')} style={btn('transparent', '#64748b', { marginLeft: 'auto' })}>
            DISMISS
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
          {mode === 'modify' && (
            <label style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
              <span style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 600 }}>REPLACEMENT PLAN</span>
              <textarea value={plan} onChange={(e) => setPlan(e.target.value)} rows={3} style={{ ...inputStyle, resize: 'vertical' }} />
            </label>
          )}
          {mode === 'reject' && (
            <label style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
              <span style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 600 }}>REASON FOR REJECTING</span>
              <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why is this plan wrong?" style={inputStyle} />
            </label>
          )}
          {(mode === 'approve' || mode === 'modify') && (
            <label style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
              <span style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 600 }}>ADMIN PASSWORD</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Required to dispatch work"
                style={inputStyle}
                autoComplete="current-password"
              />
            </label>
          )}
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              disabled={busy}
              onClick={() => submit(mode, { password, plan, reason })}
              style={btn(mode === 'reject' ? '#ef4444' : '#10b981', mode === 'reject' ? '#fff' : '#04120c')}
            >
              CONFIRM {mode.toUpperCase()}
            </button>
            <button disabled={busy} onClick={reset} style={btn('transparent', '#94a3b8')}>CANCEL</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function DecisionQueue({ refreshKey = 0, onDecided }) {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reachable, setReachable] = useState(true);
  const [busy, setBusy] = useState(false);
  const [showResolved, setShowResolved] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/decision-queue?include_resolved=${showResolved}`);
      if (!res.ok) throw new Error(`Server responded ${res.status}`);
      setCards(await res.json());
      setReachable(true);
    } catch (err) {
      console.error("[API] Failed to load decision queue:", err);
      setReachable(false);
    } finally {
      setLoading(false);
    }
  }, [showResolved]);

  useEffect(() => {
    load();
    const timer = setInterval(load, 10000);
    return () => clearInterval(timer);
  }, [load, refreshKey]);

  // Returns an error string on failure, or null on success, so the card can
  // surface the reason inline instead of silently doing nothing.
  const decide = async (id, action, extra = {}) => {
    setBusy(true);
    try {
      const res = await fetch(`${API_BASE}/api/incidents/${id}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, ...extra })
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        return body.detail || `Failed (${res.status})`;
      }
      await load();
      if (onDecided) onDecided();
      return null;
    } catch (err) {
      return "Could not reach the server.";
    } finally {
      setBusy(false);
    }
  };

  const openCount = cards.filter(c => c.resolution_status === 'pending').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '18px 20px', borderBottom: '1px solid var(--border-color)', flexShrink: 0, gap: '12px'
      }}>
        <div>
          <h2 style={{ fontSize: '15px', fontWeight: 600, color: '#f8fafc' }}>Decision Queue</h2>
          <p style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
            {loading ? 'Loading…'
              : !reachable ? 'API unreachable'
              : openCount === 0 ? 'Nothing needs your attention'
              : `${openCount} awaiting a decision, most urgent first`}
          </p>
        </div>
        <button
          onClick={() => setShowResolved(!showResolved)}
          style={{
            padding: '6px 12px', backgroundColor: showResolved ? 'var(--bg-card)' : 'transparent',
            border: '1px solid var(--border-color)', borderRadius: '8px',
            color: showResolved ? '#f8fafc' : '#94a3b8', fontSize: '10px',
            fontWeight: 700, cursor: 'pointer', flexShrink: 0
          }}
        >
          {showResolved ? 'HIDE DECIDED' : 'SHOW DECIDED'}
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {!reachable && (
          <div style={{
            backgroundColor: 'rgba(239, 68, 68, 0.08)', border: '1px solid #ef4444',
            borderRadius: '8px', padding: '14px 16px', fontSize: '12px', color: '#fca5a5'
          }}>
            Cannot reach the RailMind API at {API_BASE}. This queue may be out of date — do not treat it as empty.
          </div>
        )}

        {reachable && !loading && cards.length === 0 && (
          <div style={{
            padding: '48px 24px', textAlign: 'center', color: '#64748b', fontSize: '13px',
            border: '1px dashed var(--border-color)', borderRadius: '8px'
          }}>
            <Check size={26} style={{ color: '#10b981', marginBottom: '10px' }} />
            <div>No open incidents. The queue is clear.</div>
          </div>
        )}

        {cards.map((card, i) => (
          <DecisionCard
            key={card.id}
            card={card}
            rank={i + 1}
            onDecide={decide}
            busy={busy}
          />
        ))}
      </div>
    </div>
  );
}

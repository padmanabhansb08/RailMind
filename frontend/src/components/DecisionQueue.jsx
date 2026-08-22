/* eslint-disable */
import React, { useState, useEffect, useCallback } from 'react';
import {
  AlertTriangle, Check, X, Pencil, RotateCcw, ChevronDown, ChevronRight,
  Clock, Repeat, Network, ArrowRight, FlaskConical, MessageSquare
} from 'lucide-react';
import { API_BASE } from '../systemStatus';

/* The card answers four questions in order, because that is the order an
   operator asks them: what happened, what it costs to keep waiting, what is
   proposed, and what happens when I click the button. Everything on it comes
   from a recorded field; nothing is decorative. */

const SEVERITY = {
  critical: { color: '#f87171', label: 'Critical' },
  high:     { color: '#f87171', label: 'High' },
  severe:   { color: '#f87171', label: 'High' },
  warning:  { color: '#fbbf24', label: 'Warning' },
  medium:   { color: '#fbbf24', label: 'Medium' },
  low:      { color: '#94a3b8', label: 'Low' },
  info:     { color: '#8b949e', label: 'Info' },
};

const severityMeta = (s) => SEVERITY[String(s).toLowerCase()] || SEVERITY.info;

const STATUS_LABEL = {
  approved: 'Approved',
  overridden: 'Modified',
  rejected: 'Rejected',
  acknowledged: 'Dismissed',
};

const SOURCE_LABEL = {
  model: 'Assessed by the reasoning model',
  derived: 'Derived from recorded telemetry',
};

const btn = (variant) => {
  const base = {
    padding: '9px 15px',
    borderRadius: '7px',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '7px',
    fontFamily: 'inherit',
    transition: 'background-color .15s, border-color .15s, color .15s',
    border: '1px solid transparent',
    lineHeight: 1,
  };
  if (variant === 'primary') {
    return { ...base, backgroundColor: '#e6edf3', color: '#0d1117', borderColor: '#e6edf3' };
  }
  if (variant === 'danger') {
    return { ...base, backgroundColor: 'transparent', color: '#f87171', borderColor: 'rgba(248,113,113,.4)' };
  }
  if (variant === 'ghost') {
    return { ...base, backgroundColor: 'transparent', color: '#8b949e', borderColor: 'transparent' };
  }
  return { ...base, backgroundColor: 'transparent', color: '#c9d1d9', borderColor: 'var(--border-color)' };
};

const inputStyle = {
  backgroundColor: 'var(--bg-main)',
  border: '1px solid var(--border-color)',
  borderRadius: '6px',
  color: '#f0f6fc',
  padding: '9px 11px',
  fontSize: '13px',
  outline: 'none',
  width: '100%',
  fontFamily: 'inherit',
};

const sectionLabel = {
  fontSize: '11px',
  fontWeight: 600,
  color: '#8b949e',
  letterSpacing: '.02em',
  marginBottom: '8px',
  display: 'block',
};

function Disclosure({ label, icon, tone = '#8b949e', children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        style={{
          background: 'transparent', border: 'none', color: tone, padding: 0,
          fontSize: '12px', fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
          display: 'flex', alignItems: 'center', gap: '6px', textAlign: 'left',
        }}
      >
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        {icon}
        {label}
      </button>
      {open && <div style={{ marginTop: '10px' }}>{children}</div>}
    </div>
  );
}

/* Why this card sits where it does. Operators won't trust an ordering they
   can't interrogate, so the score is always openable. */
function ScoreBreakdown({ card }) {
  return (
    <Disclosure label={`Priority ${card.score} — how it was ranked`}>
      <div style={{
        padding: '11px 13px', backgroundColor: 'var(--bg-main)',
        border: '1px solid var(--border-color)', borderRadius: '7px',
        display: 'flex', flexDirection: 'column', gap: '6px',
      }}>
        {card.score_breakdown.map((b) => (
          <div key={b.factor} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
            <span style={{ color: '#c9d1d9' }}>
              {b.factor} <span style={{ color: '#6e7681' }}>({b.value})</span>
            </span>
            <span style={{ color: b.points > 0 ? '#c9d1d9' : '#4d5560', fontWeight: 600 }}>+{b.points}</span>
          </div>
        ))}
        <div style={{
          display: 'flex', justifyContent: 'space-between', fontSize: '12px',
          borderTop: '1px solid var(--border-color)', paddingTop: '7px', marginTop: '2px',
        }}>
          <span style={{ color: '#f0f6fc', fontWeight: 600 }}>Total</span>
          <span style={{ color: '#f0f6fc', fontWeight: 600 }}>{card.score}</span>
        </div>
      </div>
    </Disclosure>
  );
}

/* Trains heading into the same station. Worded as convergence, never as a
   prediction of delay — the feed has no track topology to justify that claim. */
function NetworkImpact({ impact }) {
  if (!impact) return null;

  if (!impact.matched) {
    return (
      <span style={{ fontSize: '12px', color: '#6e7681', display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Network size={12} /> Network impact unknown — {impact.reason}
      </span>
    );
  }

  if (impact.count === 0) {
    return (
      <span style={{ fontSize: '12px', color: '#6e7681', display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Network size={12} /> No other train is at or approaching {impact.station} in the live feed
      </span>
    );
  }

  const soonest = impact.next_arrival_in;
  return (
    <Disclosure
      tone="#c9d1d9"
      icon={<Network size={13} />}
      label={
        <span>
          {impact.count} train{impact.count === 1 ? '' : 's'} converging on {impact.station}
          {soonest != null && <span style={{ color: '#6e7681' }}> · next in {soonest} min</span>}
        </span>
      }
    >
      <div style={{
        padding: '11px 13px', backgroundColor: 'var(--bg-main)',
        border: '1px solid var(--border-color)', borderRadius: '7px',
        display: 'flex', flexDirection: 'column', gap: '7px',
      }}>
        {impact.trains.map((t) => (
          <div key={t.train_number} style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', fontSize: '12px' }}>
            <span style={{ color: '#c9d1d9', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              <span style={{ color: '#f0f6fc', fontWeight: 600 }}>{t.train_number}</span>{' '}{t.train_name}
            </span>
            <span style={{ color: t.relation === 'at_station' ? '#fbbf24' : '#8b949e', flexShrink: 0 }}>
              {t.relation === 'at_station' ? 'at station' : `in ${t.arrives_in_minutes} min`}
            </span>
          </div>
        ))}
        {impact.truncated > 0 && (
          <span style={{ fontSize: '11px', color: '#6e7681' }}>+{impact.truncated} more</span>
        )}
        <span style={{ fontSize: '11px', color: '#6e7681', borderTop: '1px solid var(--border-color)', paddingTop: '7px', lineHeight: 1.6 }}>
          Scheduled into this station within {impact.window_minutes} min. Convergence only — the live feed
          carries no track or platform data, so this does not predict which will be delayed.
        </span>
      </div>
    </Disclosure>
  );
}

/* The cost of leaving the card alone, itemised. */
function Consequences({ card }) {
  const items = card.consequences?.length
    ? card.consequences
    : [{ kind: 'note', headline: card.inaction_note, detail: null }];

  return (
    <div style={{
      border: '1px solid rgba(251,191,36,.22)',
      backgroundColor: 'rgba(251,191,36,.04)',
      borderRadius: '8px',
      padding: '13px 15px',
    }}>
      <span style={{ ...sectionLabel, color: '#d4a72c', display: 'flex', alignItems: 'center', gap: '7px' }}>
        <AlertTriangle size={13} /> If this is not resolved
      </span>
      <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '9px', margin: 0, padding: 0 }}>
        {items.map((c, i) => (
          <li key={i} style={{ display: 'flex', gap: '9px', alignItems: 'flex-start' }}>
            <span style={{
              width: '5px', height: '5px', borderRadius: '50%', backgroundColor: '#d4a72c',
              flexShrink: 0, marginTop: '7px',
            }} />
            <span style={{ minWidth: 0 }}>
              <span style={{ fontSize: '13px', color: '#f0f6fc', lineHeight: 1.5, display: 'block' }}>
                {c.headline}
              </span>
              {c.detail && (
                <span style={{ fontSize: '12px', color: '#8b949e', lineHeight: 1.6, display: 'block', marginTop: '2px' }}>
                  {c.detail}
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* What will actually happen when the operator approves. */
function ProposedResponse({ card }) {
  if (!card.proposed_plan && !card.dispatches?.length) return null;

  return (
    <div style={{
      border: '1px solid var(--border-color)',
      backgroundColor: 'var(--bg-main)',
      borderRadius: '8px',
      padding: '13px 15px',
      display: 'flex',
      flexDirection: 'column',
      gap: '13px',
    }}>
      <div>
        <span style={sectionLabel}>Recommended response</span>
        <p style={{ fontSize: '13px', color: '#f0f6fc', lineHeight: 1.6, margin: 0 }}>
          {card.proposed_plan || 'No movement plan recorded.'}
        </p>
        {card.expected_outcome && (
          <p style={{ fontSize: '12px', color: '#8b949e', lineHeight: 1.6, margin: '7px 0 0', display: 'flex', gap: '7px' }}>
            <ArrowRight size={13} style={{ flexShrink: 0, marginTop: '3px' }} />
            {card.expected_outcome}
          </p>
        )}
      </div>

      {card.dispatches?.length > 0 && (
        <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
          <span style={sectionLabel}>
            Approving dispatches {card.dispatches.length} task{card.dispatches.length === 1 ? '' : 's'}
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '9px' }}>
            {card.dispatches.map((d) => (
              <div key={d.department} style={{ display: 'flex', gap: '12px', fontSize: '12px', lineHeight: 1.6 }}>
                <span style={{ color: '#c9d1d9', fontWeight: 600, minWidth: '112px', flexShrink: 0 }}>
                  {d.department}
                </span>
                <span style={{ color: '#8b949e' }}>{d.task}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {card.passenger_sms && (
        <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
          <span style={sectionLabel}>Passenger notice</span>
          <p style={{
            fontSize: '12px', color: '#8b949e', lineHeight: 1.6, margin: 0,
            display: 'flex', gap: '8px', alignItems: 'flex-start',
          }}>
            <MessageSquare size={13} style={{ flexShrink: 0, marginTop: '3px' }} />
            {card.passenger_sms}
          </p>
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

  const meta = severityMeta(card.severity);
  const decided = card.resolution_status !== 'pending';

  const reset = () => { setMode(null); setPassword(''); setReason(''); setError(null); };

  const submit = async (action, extra = {}) => {
    setError(null);
    const err = await onDecide(card.id, action, extra);
    if (err) setError(err); else reset();
  };

  return (
    <article style={{
      backgroundColor: 'var(--bg-panel)',
      border: '1px solid var(--border-color)',
      borderLeft: `3px solid ${decided ? '#30363d' : meta.color}`,
      borderRadius: '10px',
      padding: '20px 22px',
      display: 'flex',
      flexDirection: 'column',
      gap: '18px',
      opacity: decided ? 0.6 : 1,
    }}>
      {/* Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '18px' }}>
        <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start', minWidth: 0 }}>
          <span style={{ fontSize: '13px', fontWeight: 600, color: '#4d5560', minWidth: '20px', paddingTop: '3px' }}>
            {rank}
          </span>
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '7px' }}>
              <span style={{
                fontSize: '11px', fontWeight: 600, color: meta.color,
                border: `1px solid ${meta.color}55`, backgroundColor: `${meta.color}12`,
                padding: '2px 8px', borderRadius: '4px', lineHeight: 1.6,
              }}>{meta.label}</span>
              <span style={{ fontSize: '12px', color: '#c9d1d9' }}>
                {card.train_number}{card.train_name ? ` · ${card.train_name}` : ''}
              </span>
              {card.station && <span style={{ fontSize: '12px', color: '#6e7681' }}>at {card.station}</span>}
              {card.simulated && (
                <span style={{
                  fontSize: '11px', color: '#8b949e', border: '1px dashed var(--border-color)',
                  padding: '2px 8px', borderRadius: '4px', display: 'inline-flex',
                  alignItems: 'center', gap: '5px', lineHeight: 1.6,
                }}>
                  <FlaskConical size={11} /> Simulated injection
                </span>
              )}
            </div>
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#f0f6fc', lineHeight: 1.4, margin: 0 }}>
              {card.title || 'Operations anomaly'}
            </h3>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px', flexShrink: 0 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px', color: '#6e7681' }}>
            <Clock size={12} /> {card.age_label} unanswered
          </span>
          {card.recurrence > 1 && (
            <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px', color: '#d4a72c' }}>
              <Repeat size={12} /> {card.recurrence}× recurrence
            </span>
          )}
        </div>
      </header>

      {/* What is happening */}
      {card.situation_summary && (
        <section>
          <span style={sectionLabel}>What is happening</span>
          <p style={{ fontSize: '13px', color: '#c9d1d9', lineHeight: 1.7, margin: 0 }}>
            {card.situation_summary}
          </p>
        </section>
      )}

      <Consequences card={card} />

      <ProposedResponse card={card} />

      {/* Evidence, folded away until asked for */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: '11px' }}>
        {card.reasoning_steps?.length > 0 && (
          <Disclosure label={`How this was assessed (${card.reasoning_steps.length} steps)`}>
            <ol style={{
              margin: 0, padding: '11px 13px 11px 30px', backgroundColor: 'var(--bg-main)',
              border: '1px solid var(--border-color)', borderRadius: '7px',
              display: 'flex', flexDirection: 'column', gap: '7px',
            }}>
              {card.reasoning_steps.map((step, i) => (
                <li key={i} style={{ fontSize: '12px', color: '#8b949e', lineHeight: 1.6 }}>{step}</li>
              ))}
            </ol>
            {(card.reasoning_source || card.confidence_score != null || card.memory_used) && (
              <p style={{ fontSize: '11px', color: '#6e7681', margin: '8px 0 0', lineHeight: 1.6 }}>
                {SOURCE_LABEL[card.reasoning_source] || 'Source not recorded'}
                {card.confidence_score != null && ` · model confidence ${card.confidence_score}%`}
                {card.memory_used && ` · ${card.memory_used}`}
              </p>
            )}
          </Disclosure>
        )}

        <NetworkImpact impact={card.network_impact} />
        <ScoreBreakdown card={card} />
      </section>

      {error && (
        <div style={{
          fontSize: '12px', color: '#fca5a5', backgroundColor: 'rgba(248,113,113,.08)',
          border: '1px solid rgba(248,113,113,.4)', borderRadius: '7px', padding: '10px 12px',
        }}>
          {error}
        </div>
      )}

      {/* Decision surface */}
      {decided ? (
        <footer style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '14px',
          borderTop: '1px solid var(--border-color)', paddingTop: '14px',
        }}>
          <span style={{ fontSize: '12px', color: '#8b949e' }}>
            {STATUS_LABEL[card.resolution_status] || card.resolution_status}
            {card.decisions?.length > 0 && (
              <span style={{ color: '#6e7681' }}>
                {' '}by {card.decisions[card.decisions.length - 1].actor}
                {card.decisions[card.decisions.length - 1].reason
                  ? ` — "${card.decisions[card.decisions.length - 1].reason}"` : ''}
              </span>
            )}
          </span>
          <button disabled={busy} onClick={() => submit('undo')} style={btn('secondary')}>
            <RotateCcw size={13} /> Undo
          </button>
        </footer>
      ) : mode === null ? (
        <footer style={{
          display: 'flex', gap: '9px', flexWrap: 'wrap', alignItems: 'center',
          borderTop: '1px solid var(--border-color)', paddingTop: '14px',
        }}>
          <button disabled={busy} onClick={() => setMode('approve')} style={btn('primary')}>
            <Check size={14} /> Approve and dispatch
          </button>
          <button disabled={busy} onClick={() => setMode('modify')} style={btn('secondary')}>
            <Pencil size={13} /> Modify plan
          </button>
          <button disabled={busy} onClick={() => setMode('reject')} style={btn('danger')}>
            <X size={13} /> Reject
          </button>
          <button disabled={busy} onClick={() => submit('acknowledge')} style={{ ...btn('ghost'), marginLeft: 'auto' }}>
            Dismiss
          </button>
        </footer>
      ) : (
        <footer style={{
          display: 'flex', flexDirection: 'column', gap: '12px',
          borderTop: '1px solid var(--border-color)', paddingTop: '14px',
        }}>
          {mode === 'modify' && (
            <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <span style={sectionLabel}>Replacement plan</span>
              <textarea value={plan} onChange={(e) => setPlan(e.target.value)} rows={3} style={{ ...inputStyle, resize: 'vertical' }} />
            </label>
          )}
          {mode === 'reject' && (
            <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <span style={sectionLabel}>Reason for rejecting</span>
              <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why is this plan wrong?" style={inputStyle} />
            </label>
          )}
          {(mode === 'approve' || mode === 'modify') && (
            <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <span style={sectionLabel}>Admin password</span>
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
          <div style={{ display: 'flex', gap: '9px' }}>
            <button
              disabled={busy}
              onClick={() => submit(mode, { password, plan, reason })}
              style={btn(mode === 'reject' ? 'danger' : 'primary')}
            >
              Confirm {mode}
            </button>
            <button disabled={busy} onClick={reset} style={btn('ghost')}>Cancel</button>
          </div>
        </footer>
      )}
    </article>
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
        padding: '20px 24px', borderBottom: '1px solid var(--border-color)', flexShrink: 0, gap: '14px'
      }}>
        <div>
          <h2 style={{ fontSize: '17px', fontWeight: 600, color: '#f0f6fc', margin: 0 }}>Incident alerts</h2>
          <p style={{ fontSize: '12px', color: '#6e7681', marginTop: '3px', marginBottom: 0 }}>
            {loading ? 'Loading…'
              : !reachable ? 'API unreachable'
              : openCount === 0 ? 'Nothing needs your attention'
              : `${openCount} awaiting a decision, most urgent first`}
          </p>
        </div>
        <button
          onClick={() => setShowResolved(!showResolved)}
          style={{
            ...btn('secondary'),
            backgroundColor: showResolved ? 'var(--bg-card)' : 'transparent',
            color: showResolved ? '#f0f6fc' : '#8b949e',
            flexShrink: 0,
          }}
        >
          {showResolved ? 'Hide decided' : 'Show decided'}
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '18px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {!reachable && (
          <div style={{
            backgroundColor: 'rgba(248,113,113,.08)', border: '1px solid rgba(248,113,113,.4)',
            borderRadius: '8px', padding: '15px 17px', fontSize: '13px', color: '#fca5a5'
          }}>
            Cannot reach the RailMind API at {API_BASE}. This queue may be out of date — do not treat it as empty.
          </div>
        )}

        {reachable && !loading && cards.length === 0 && (
          <div style={{
            padding: '54px 24px', textAlign: 'center', color: '#6e7681', fontSize: '14px',
            border: '1px dashed var(--border-color)', borderRadius: '8px'
          }}>
            <Check size={26} style={{ color: '#34d399', marginBottom: '12px' }} />
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

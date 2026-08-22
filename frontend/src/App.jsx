/* eslint-disable */
import React, { useState, useEffect, useRef, useMemo } from 'react';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import LiveMap from './components/LiveMap';
import TaskBoard from './components/TaskBoard';
import RouteIntelligence from './components/RouteIntelligence';
import DecisionQueue from './components/DecisionQueue';
import SimulationPortal from './components/SimulationPortal';
import { API_BASE, statusMeta, formatDuration, useSystemStatus, StatusDot } from './systemStatus';
import { Terminal, X, Bell } from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error("[ERROR BOUNDARY] Caught rendering error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
          <div style={{
            padding: '40px',
            backgroundColor: 'var(--bg-main)',
            color: '#ef4444',
            height: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            gap: '16px'
          }}>
            <h2 style={{ fontWeight: 600 }}>System Encountered an Error</h2>
            <p style={{ color: '#94a3b8', fontSize: '13px' }}>RailMind Dashboard encountered an unrecoverable rendering error.</p>
            <button 
              onClick={() => window.location.reload()}
              style={{
                padding: '10px 20px',
                backgroundColor: '#ffffff',
                color: '#05070a',
                border: 'none',
                borderRadius: '6px',
                fontWeight: 700,
                cursor: 'pointer',
                transition: 'background-color 0.2s'
              }}
            >
              REBOOT SYSTEM
            </button>
          </div>
      );
    }
    return this.props.children;
  }
}

function MainApp() {
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [loopCount, setLoopCount] = useState(0);
  const [incidentCount, setIncidentCount] = useState(0);
  const [incidents, setIncidents] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [trains, setTrains] = useState([]);
  const [wsStatus, setWsStatus] = useState('reconnecting');
  const [logs, setLogs] = useState([]);
  
  // Modal Overlay States
  const [showNotifications, setShowNotifications] = useState(false);
  // Last train the operator searched for, so the map can fly to it.
  const [focusTrainNumber, setFocusTrainNumber] = useState(null);
  const [searchError, setSearchError] = useState(null);

  // Resizable Panel States
  const [panelHeight, setPanelHeight] = useState(240);
  const dragRef = useRef({ isDragging: false, startY: 0, startHeight: 0 });

  const handleMouseDown = (e) => {
    dragRef.current = { isDragging: true, startY: e.clientY, startHeight: panelHeight };
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  const handleMouseMove = (e) => {
    if (!dragRef.current.isDragging) return;
    const dy = e.clientY - dragRef.current.startY;
    const newHeight = dragRef.current.startHeight - dy;
    setPanelHeight(Math.max(100, Math.min(newHeight, window.innerHeight - 200)));
  };

  const handleMouseUp = () => {
    dragRef.current.isDragging = false;
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };

  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const recentIncidentElements = useMemo(() => {
    const result = [];
    const len = Math.min(incidents.length, 5);
    for (let i = 0; i < len; i++) {
      const inc = incidents[i];
      result.push(
        <div key={inc.id} style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          padding: '14px 16px',
          borderRadius: '8px',
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          fontSize: '13px',
          color: '#cbd5e1'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ color: inc.severity === 'critical' ? '#ef4444' : '#f59e0b', fontWeight: 700, fontSize: '11px', textTransform: 'uppercase' }}>{inc.severity}</span>
            <span style={{ color: '#64748b', fontSize: '12px' }}>{inc.timestamp}</span>
          </div>
          {inc.title}
        </div>
      );
    }
    return result;
  }, [incidents]);

  const socketRef = useRef(null);

  // Fetch functions
  const fetchIncidents = async () => {
    try {
      // all=true: incident history now survives restarts, so the default
      // 24-hour window would hide everything the decision queue is showing.
      const res = await fetch(`${API_BASE}/api/incidents?all=true`);
      if (res.ok) {
        const data = await res.json();
        const formatted = data.map(inc => ({
          id: inc.incident_id || inc._id,
          severity: inc.severity || "info",
          title: inc.incident_title || inc.summary || "Operations Anomaly",
          description: inc.situation_summary || inc.summary || "Investigating operational status.",
          timestamp: new Date(inc.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          incident_title: inc.incident_title || inc.summary || "Operations Anomaly",
          situation_summary: inc.situation_summary || inc.summary || "Investigating operational status.",
          reroute_plan: inc.reroute_plan || null,
          maintenance_task: inc.maintenance_task || '',
          operations_task: inc.operations_task || '',
          station_manager_task: inc.station_manager_task || '',
          passenger_sms: inc.passenger_sms || '',
          resolution_status: inc.resolution_status || 'pending',
          approved: inc.resolution_status === 'approved',
          departments: inc.departments_notified || [],
          train_number: inc.train_number || 'Unknown'
        }));
        setIncidents(formatted);
      }
    } catch (err) {
      console.error("[API] Failed to fetch incidents:", err);
    }
  };

  // The Alerts badge counts open decision cards, read from the same endpoint
  // the queue renders. Deriving it from a differently-filtered list is what
  // let the header show 0 while the queue showed 14.
  const fetchOpenDecisions = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/decision-queue`);
      if (res.ok) {
        const cards = await res.json();
        setIncidentCount(cards.filter(c => c.resolution_status === 'pending').length);
      }
    } catch (err) {
      console.error("[API] Failed to fetch open decisions:", err);
    }
  };

  const fetchTrains = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/trains`);
      if (res.ok) {
        const data = await res.json();
        setTrains(data);
      }
    } catch (err) {
      console.error("[API] Failed to fetch trains:", err);
    }
  };

  const fetchTasks = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/dept-tasks`);
      if (res.ok) {
        const data = await res.json();
        setTasks(data);
      }
    } catch (err) {
      console.error("[API] Failed to fetch department tasks:", err);
    }
  };

  // After a decision lands, the task board and incident list are both stale.
  const refreshAll = () => {
    fetchIncidents();
    fetchOpenDecisions();
    fetchTasks();
  };

  // A failed search has to say so. Previously the backend invented a train for
  // any input, and this handler quietly ignored non-OK responses — so a bad
  // number either produced a fictional train or looked like nothing happened.
  const handleSearch = async (trainNumber) => {
    if (!trainNumber) return;
    setSearchError(null);
    try {
      const res = await fetch(`${API_BASE}/api/trains/search?train_number=${encodeURIComponent(trainNumber)}`);
      const body = await res.json().catch(() => ({}));

      if (!res.ok) {
        setSearchError(body.detail || `Search failed (${res.status})`);
        return;
      }
      if (!body || !body.train_number) {
        setSearchError(`No train ${trainNumber} found.`);
        return;
      }

      setTrains(prev => {
        const exists = prev.find(t => t.train_number === body.train_number);
        if (exists) {
          return prev.map(t => t.train_number === body.train_number ? body : t);
        }
        return [...prev, body];
      });
      setFocusTrainNumber(body.train_number);
    } catch (err) {
      console.error("Search failed:", err);
      setSearchError("Could not reach the RailMind API.");
    }
  };

  useEffect(() => {
    fetchIncidents();
    fetchOpenDecisions();
    fetchTrains();
    fetchTasks();

    // Poll trains every 5 seconds for live position updates
    const trainInterval = setInterval(fetchTrains, 5000);
    const wsUrl = `ws://${window.location.hostname}:8000/ws`;
    let socket;
    let reconnectTimeout;

    const connectWS = () => {
      console.log("[WEBSOCKET] Connecting to:", wsUrl);
      socket = new WebSocket(wsUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        console.log("[WEBSOCKET] Connected to RailMind WebSocket server");
        setWsStatus('connected');
      };

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          
          if (payload.type === 'INCIDENT_UPDATE') {
            const report = payload.data;
            
            const newIncident = {
              id: report.incident_id,
              severity: report.severity || "info",
              title: report.incident_title || report.summary || "New Incident Logged",
              description: report.situation_summary || report.summary || "Investigating operational status.",
              timestamp: new Date(report.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              incident_title: report.incident_title || report.summary || "New Incident Logged",
              situation_summary: report.situation_summary || report.summary || "Investigating operational status.",
              reroute_plan: report.reroute_plan || null,
              maintenance_task: report.maintenance_task || '',
              operations_task: report.operations_task || '',
              station_manager_task: report.station_manager_task || '',
              passenger_sms: report.passenger_sms || '',
              resolution_status: report.resolution_status || 'pending',
              approved: report.resolution_status === 'approved',
              departments: report.departments_notified || [],
              train_number: report.train_number || 'Unknown'
            };

            setIncidents(prev => {
              if (prev.some(inc => inc.id === newIncident.id)) return prev;
              return [newIncident, ...prev];
            });
            fetchOpenDecisions();
            if (report.loop_count !== undefined) {
              setLoopCount(report.loop_count);
            }

            fetchTasks();
            fetchTrains();
          } else if (payload.type === 'AGENT_LOG') {
            setLogs(prev => [...prev, payload].slice(-200)); // Keep last 200 logs
          }
        } catch (err) {
          console.error("[WEBSOCKET] Error parsing socket data:", err);
        }
      };

      socket.onclose = () => {
        console.log("[WEBSOCKET] Closed. Reconnecting in 3 seconds...");
        setWsStatus('reconnecting');
        reconnectTimeout = setTimeout(connectWS, 3000);
      };

      socket.onerror = (err) => {
        console.error("[WEBSOCKET] Error encountered:", err);
        socket.close();
      };
    };

    connectWS();

    return () => {
      if (socket) socket.close();
      clearTimeout(reconnectTimeout);
      clearInterval(trainInterval);
    };
  }, []);

  // Acknowledging is an auditable decision ("a human saw this and chose not to
  // act"), so it has to reach the server. Remove it optimistically, but put it
  // back if the write fails rather than silently losing the operator's action.
  const handleResolve = async (taskId) => {
    console.log(`Resolving department task: ${taskId}`);
    try {
      const res = await fetch(`${API_BASE}/api/dept-tasks/${taskId}/resolve`, {
        method: 'POST'
      });
      if (res.ok) {
        setTasks(prev => prev.map(t => {
          if (t._id === taskId || t.id === taskId) {
            return { ...t, status: 'resolved', urgency: 'resolved' };
          }
          return t;
        }));
      } else {
        console.error("Failed to mark task resolved on API server");
      }
    } catch (err) {
      console.error("Error sending resolution request:", err);
    }
  };

  // Views Render Functions
  // Every figure here is computed server-side from stored incidents. Where
  // there is not enough history to compute one, we say so instead of showing
  // a plausible-looking placeholder.
  const AnalyticsView = () => {
    const [analytics, setAnalytics] = useState(null);
    const [analyticsError, setAnalyticsError] = useState(false);
    const { status, reachable } = useSystemStatus();

    useEffect(() => {
      let cancelled = false;
      const load = async () => {
        try {
          const res = await fetch(`${API_BASE}/api/analytics`);
          if (!res.ok) throw new Error(`Server responded ${res.status}`);
          const data = await res.json();
          if (!cancelled) { setAnalytics(data); setAnalyticsError(false); }
        } catch (err) {
          console.error("[API] Failed to fetch analytics:", err);
          if (!cancelled) setAnalyticsError(true);
        }
      };
      load();
      const timer = setInterval(load, 15000);
      return () => { cancelled = true; clearInterval(timer); };
    }, []);

    const severity = analytics?.by_severity || {};
    const bars = Object.entries(severity)
      .sort((a, b) => b[1] - a[1])
      .map(([name, count]) => ({
        name,
        count,
        color: name === 'critical' || name === 'high' ? '#ef4444'
             : name === 'warning' || name === 'medium' ? '#f59e0b'
             : '#06b6d4'
      }));
    const maxCount = Math.max(...bars.map(b => b.count), 1);

    const avgResolution = formatDuration(analytics?.avg_resolution_seconds);
    const resolvedCount = analytics?.resolved_count ?? 0;

    const tiles = [
      {
        label: 'TOTAL INCIDENTS',
        val: analyticsError ? '—' : (analytics?.total_incidents ?? '…'),
        color: '#06b6d4',
        note: analytics ? `stored in ${analytics.store === 'mongodb' ? 'MongoDB' : 'local fallback file'}` : null
      },
      {
        label: 'RESOLVED',
        val: analyticsError ? '—' : resolvedCount,
        color: '#10b981',
        note: analytics ? `${analytics.total_incidents - resolvedCount} still open` : null
      },
      {
        label: 'AGENT CYCLES (THIS SESSION)',
        val: loopCount,
        color: '#10b981',
        note: 'resets when the server restarts'
      },
      {
        label: 'AVG RESOLUTION TIME',
        val: avgResolution ?? 'No data',
        color: avgResolution ? '#cbd5e1' : '#64748b',
        note: avgResolution
          ? `measured across ${resolvedCount} resolved incident${resolvedCount === 1 ? '' : 's'}`
          : 'needs at least one resolved incident'
      }
    ];

    return (
      <div style={{ padding: '24px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc' }}>OPERATIONS ANALYTICS</h2>
          <p style={{ fontSize: '11px', color: '#64748b' }}>COMPUTED FROM STORED INCIDENT HISTORY</p>
        </div>

        {analyticsError && (
          <div style={{
            backgroundColor: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid #ef4444',
            borderRadius: '8px',
            padding: '12px 16px',
            fontSize: '12px',
            color: '#fca5a5'
          }}>
            Could not reach the analytics endpoint — the figures below are unavailable, not zero.
          </div>
        )}

        {/* Stats Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
          {tiles.map((stat, idx) => (
            <div key={idx} style={{
              backgroundColor: 'var(--bg-main)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}>
              <span style={{ fontSize: '9px', fontWeight: 600, color: '#64748b', letterSpacing: '0.5px' }}>{stat.label}</span>
              <span style={{ fontSize: '28px', fontWeight: 700, color: stat.color }}>{stat.val}</span>
              {stat.note && (
                <span style={{ fontSize: '10px', color: '#64748b' }}>{stat.note}</span>
              )}
            </div>
          ))}
        </div>

        {/* Charts and Data Representation */}
        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
          <div style={{
            flex: 1,
            minWidth: '340px',
            backgroundColor: 'var(--bg-main)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}>
            <h3 style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc', letterSpacing: '0.5px' }}>INCIDENTS BY SEVERITY</h3>
            {bars.length === 0 ? (
              <div style={{ color: '#64748b', fontSize: '12px', padding: '40px 0', textAlign: 'center' }}>
                {analyticsError ? 'Unavailable' : 'No incidents recorded yet'}
              </div>
            ) : (
              <div style={{ display: 'flex', justifyContent: 'space-around', alignItems: 'flex-end', height: '180px', paddingTop: '20px' }}>
                {bars.map((bar, idx) => (
                  <div key={idx} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', width: '60px' }}>
                    <span style={{ fontSize: '12px', fontWeight: 600, color: '#fff' }}>{bar.count}</span>
                    <div style={{
                      width: '32px',
                      height: `${Math.max((bar.count / maxCount) * 140, 6)}px`,
                      backgroundColor: bar.color,
                      borderRadius: '8px',
                      transition: 'height 0.5s ease-out'
                    }}></div>
                    <span style={{ fontSize: '10px', color: '#64748b', textTransform: 'capitalize' }}>{bar.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={{
            flex: 1,
            minWidth: '340px',
            backgroundColor: 'var(--bg-main)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}>
            <h3 style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc', letterSpacing: '0.5px' }}>LIVE SUBSYSTEM STATUS</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '11px', color: '#cbd5e1', marginTop: '10px' }}>
              {!reachable && (
                <div style={{ color: '#ef4444', fontWeight: 600 }}>API unreachable — status unknown.</div>
              )}
              {reachable && !status && (
                <div style={{ color: '#64748b' }}>Probing subsystems…</div>
              )}
              {reachable && status?.components?.map((c) => {
                const meta = statusMeta(c.status);
                return (
                  <div key={c.id} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: '12px',
                    borderBottom: '1px solid var(--border-color)',
                    paddingBottom: '6px'
                  }}>
                    <span title={c.detail} style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.name}</span>
                    <span style={{ color: meta.color, fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
                      <StatusDot status={c.status} />
                      {meta.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const LogsView = ({ logs = [], onClear }) => {
    const logEndRef = useRef(null);

    useEffect(() => {
      if (logEndRef.current) {
        logEndRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    }, [logs]);

    return (
      <div style={{ padding: '24px', flex: 1, display: 'flex', flexDirection: 'column', gap: '16px', height: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2  style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Terminal size={20} style={{ color: '#06b6d4' }} />
              COGNITIVE OPERATIONS STREAM
            </h2>
            <p  style={{ fontSize: '11px', color: '#64748b' }}>REAL-TIME AGENT STATE MACHINE TRACE</p>
          </div>
          <button
            onClick={onClear}
            
            style={{
              padding: '6px 12px',
              backgroundColor: 'transparent',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              color: '#94a3b8',
              fontSize: '10px',
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
            onMouseEnter={e => {
              e.currentTarget.style.backgroundColor = '#17202b';
              e.currentTarget.style.borderColor = '#06b6d4';
              e.currentTarget.style.color = '#e2e8f0';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.borderColor = '#2b3240';
              e.currentTarget.style.color = '#94a3b8';
            }}
          >
            CLEAR LOGSTREAM
          </button>
        </div>

        <div style={{
          flex: 1,
          backgroundColor: '#05070a',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '20px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          fontSize: '11px',
          color: '#06b6d4',
          boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.8)'
        }}>
          {logs.length === 0 ? (
            <div  style={{ color: '#64748b', fontStyle: 'italic' }}>
              [SYSTEM] Awaiting live logs from operations agent stream...
            </div>
          ) : (
            logs.map((log, idx) => (
              <div key={idx} style={{ lineBreak: 'anywhere' }}>
                <span style={{ color: '#f59e0b' }}>{log.message.substring(0, 21)}</span>
                <span style={{ color: '#06b6d4' }}>{log.message.substring(21, 35)}</span>
                <span style={{ color: '#e2e8f0' }}>{log.message.substring(35)}</span>
              </div>
            ))
          )}
          <div ref={logEndRef}></div>
        </div>
      </div>
    );
  };

  const SchedulesView = () => {
    const [scheduleTrains, setScheduleTrains] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchSchedules = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/trains`);
        if (res.ok) {
          const data = await res.json();
          setScheduleTrains(data);
        }
      } catch (err) {
        console.error("Failed to fetch schedules:", err);
      } finally {
        setLoading(false);
      }
    };

    useEffect(() => {
      fetchSchedules();
      const interval = setInterval(fetchSchedules, 30000);
      return () => clearInterval(interval);
    }, []);

    if (loading && scheduleTrains.length === 0) {
      return <div  style={{ padding: '24px', color: '#94a3b8', fontSize: '12px' }}>Retrieving Timetable...</div>;
    }

    return (
      <div style={{ padding: '24px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2  style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc' }}>Rail Network Timetable</h2>
          <p  style={{ fontSize: '11px', color: '#64748b' }}>Auto-refresh Interval [30s]</p>
        </div>

        <div style={{
          backgroundColor: 'var(--bg-main)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          overflow: 'hidden'
        }}>
          <table  style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12px' }}>
            <thead>
              <tr style={{ backgroundColor: 'var(--bg-panel)', borderBottom: '1px solid var(--border-color)', color: '#94a3b8' }}>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>TRAIN NO</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>NAME</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>CORRIDOR ROUTE</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>STATUS</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>DELAY OFFSET</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>POSITION</th>
              </tr>
            </thead>
            <tbody>
              {scheduleTrains.map((train, idx) => {
                const isDelayed = train.delay_minutes > 0;
                const statusColor = train.status === 'cancelled' ? '#ef4444' : isDelayed ? '#f59e0b' : '#10b981';
                return (
                  <tr key={idx} style={{
                    borderBottom: '1px solid #11141a',
                    color: '#cbd5e1',
                    backgroundColor: idx % 2 === 0 ? '#090b0e' : '#0f141b'
                  }}>
                    <td style={{ padding: '12px 16px', fontWeight: 700, color: '#06b6d4' }}>{train.train_number}</td>
                    <td style={{ padding: '12px 16px' }}>{train.train_name}</td>
                    <td style={{ padding: '12px 16px' }}>{train.source || 'NDLS'} → {train.destination || 'RKMP'}</td>
                    <td style={{ padding: '12px 16px', fontWeight: 600, color: statusColor }}>
                      {train.status?.toUpperCase() || 'UNKNOWN'}
                    </td>
                    <td style={{ padding: '12px 16px', color: isDelayed ? '#f59e0b' : '#64748b' }}>
                      {isDelayed ? `+${train.delay_minutes} min` : '--'}
                    </td>
                    <td style={{ padding: '12px 16px', color: '#94a3b8' }}>
                      {train.position_label || train.current_station || 'No position reported'}
                      {train.position_source === 'simulated' && (
                        <span style={{ color: '#f59e0b', fontSize: '10px', marginLeft: '6px' }}>(simulated)</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // System registry. Each row is a live probe result from
  // backend/services/health.py — nothing here is asserted by the frontend.
  const AssetsView = () => {
    const { status, reachable } = useSystemStatus(5000);

    const overall = reachable ? (status?.overall || 'unknown') : 'unknown';
    const overallMeta = statusMeta(overall);
    const components = reachable ? (status?.components || []) : [];

    const contactEntries = [
      ['MAINTENANCE', status?.contacts?.maintenance],
      ['OPERATIONS', status?.contacts?.operations],
      ['STATION MANAGER', status?.contacts?.station_manager]
    ];

    return (
      <div style={{ padding: '24px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc' }}>System Registry</h2>
            <p style={{ fontSize: '11px', color: '#64748b' }}>
              {status?.checked_at
                ? `Live probe — last checked ${new Date(status.checked_at).toLocaleTimeString()}`
                : 'Live probe of every subsystem'}
            </p>
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '10px 16px',
            borderRadius: '8px',
            border: `1px solid ${overallMeta.color}`,
            backgroundColor: `${overallMeta.color}14`
          }}>
            <StatusDot status={overall} />
            <span style={{ fontSize: '12px', fontWeight: 700, color: overallMeta.color }}>
              {overall === 'ok' ? 'ALL SYSTEMS OPERATIONAL' : `SYSTEM ${overallMeta.label.toUpperCase()}`}
            </span>
          </div>
        </div>

        {!reachable && (
          <div style={{
            backgroundColor: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid #ef4444',
            borderRadius: '8px',
            padding: '14px 18px',
            fontSize: '12px',
            color: '#fca5a5'
          }}>
            Cannot reach the RailMind API at {API_BASE}. Subsystem states below are unknown — this page will not
            guess. Check that the backend is running.
          </div>
        )}

        {/* Connection Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
          {components.map((c) => {
            const meta = statusMeta(c.status);
            return (
              <div key={c.id} style={{
                backgroundColor: 'var(--bg-main)',
                border: '1px solid var(--border-color)',
                borderLeft: `3px solid ${meta.color}`,
                borderRadius: '8px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc' }}>{c.name}</span>
                  <StatusDot status={c.status} />
                </div>
                <span style={{ fontSize: '13px', color: meta.color, fontWeight: 700 }}>
                  {meta.label.toUpperCase()}
                  {c.latency_ms != null && (
                    <span style={{ color: '#64748b', fontWeight: 500 }}> · {c.latency_ms} ms</span>
                  )}
                </span>
                <span style={{ fontSize: '11px', color: '#94a3b8', lineHeight: 1.5 }}>{c.detail}</span>
              </div>
            );
          })}
        </div>

        {/* Contacts Section */}
        <div style={{
          backgroundColor: 'var(--bg-main)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px'
        }}>
          <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#f8fafc' }}>DISPATCH CONTACTS</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '16px' }}>
            {contactEntries.map(([label, number]) => (
              <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <span style={{ fontSize: '10px', color: '#64748b', fontWeight: 600 }}>{label}</span>
                <span style={{ fontSize: '13px', color: number ? '#cbd5e1' : '#64748b', fontWeight: 500 }}>
                  {number || 'Not configured'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderContent = () => {
    switch (activeTab) {
      // The queue leads. An operator opening this should see what needs them
      // before they see anything else; the map and task board are context for
      // the decision, not the main event.
      // Overview is map + task board. The decision queue lives on its own tab
      // (Incident Alerts) rather than competing with the map for width here.
      case 'Dashboard':
        return (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            flex: 1,
            overflow: 'hidden',
            backgroundColor: '#05070a'
          }}>
            <div style={{ flex: 1, position: 'relative' }}>
              <LiveMap trains={trains} incidents={incidents} focusTrainNumber={focusTrainNumber} />
            </div>
            
            {/* Draggable Handle */}
            <div 
              onMouseDown={handleMouseDown}
              style={{ 
                height: '4px', 
                backgroundColor: 'var(--border-color)', 
                cursor: 'ns-resize',
                zIndex: 10,
                transition: 'background-color 0.2s',
              }}
              onMouseEnter={(e) => e.target.style.backgroundColor = '#64748b'}
              onMouseLeave={(e) => e.target.style.backgroundColor = 'var(--border-color)'}
            />

            <div style={{ height: `${panelHeight}px`, flexShrink: 0 }}>
              <TaskBoard tasks={tasks} onResolve={handleResolve} />
            </div>
          </div>
        );

      case 'Live Map':
        return (
          <div style={{ flex: 1, position: 'relative', height: '100%' }}>
            <LiveMap trains={trains} incidents={incidents} focusTrainNumber={focusTrainNumber} />
          </div>
        );

      case 'Incident Feed':
        return (
          <div style={{ flex: 1, height: '100%', overflow: 'hidden' }}>
            <DecisionQueue refreshKey={incidents.length} onDecided={refreshAll} />
          </div>
        );

      case 'Task Board':
        return (
          <div style={{ flex: 1, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <TaskBoard tasks={tasks} onResolve={handleResolve} fullScreen={true} />
          </div>
        );

      case 'Analytics':
        return <AnalyticsView />;


      case 'Logs':
        return <LogsView logs={logs} onClear={() => setLogs([])} />;

      case 'Sensor Data':
        return <RouteIntelligence trains={trains} />;

      case 'Timetable':
        return <SchedulesView />;

      case 'Fleet':
        return <AssetsView />;

      case 'Simulation':
        return (
          <SimulationPortal
            trains={trains}
            onRefresh={() => { fetchTrains(); refreshAll(); }}
            onOpenIncidents={() => setActiveTab('Incident Feed')}
          />
        );

      default:
        return <div  style={{ padding: '24px', fontSize: '12px' }}>Page Not Deployed</div>;
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      backgroundColor: '#05070a',
      overflow: 'hidden'
    }}>
      <TopBar 
        loopCount={loopCount} 
        incidentCount={incidentCount} 
        wsStatus={wsStatus} 
        activeTab={activeTab}
        onSearch={handleSearch}
        searchError={searchError}
        onDismissSearchError={() => setSearchError(null)}
        onTabChange={(tab) => {
          if (tab === 'Rail Network') {
            setActiveTab('Dashboard');
          } else {
            setActiveTab(tab);
          }
        }}
        onNotificationsClick={() => setShowNotifications(true)}
      />

      {wsStatus === 'reconnecting' && (
        <div style={{
          backgroundColor: '#ef4444',
          color: '#ffffff',
          textAlign: 'center',
          padding: '8px 24px',
          fontSize: '12px',
          fontWeight: 700,
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          letterSpacing: '1px',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          gap: '8px',
          zIndex: 1000,
          borderBottom: '1px solid #ef4444',
          boxShadow: '0 4px 20px rgba(239, 68, 68, 0.2)'
        }}>
          <span style={{
            display: 'inline-block',
            width: '8px',
            height: '8px',
            backgroundColor: '#ffffff',
            borderRadius: '50%',
            animation: 'pulse-live 1s infinite'
          }}></span>
          Offline / Re-establishing connection...
        </div>
      )}

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        {renderContent()}
      </div>

      {/* Notifications Modal */}
      {showNotifications && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          backgroundColor: 'rgba(5, 7, 10, 0.85)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          backdropFilter: 'blur(8px)'
        }}>
          <div style={{
            backgroundColor: 'var(--bg-panel)',
            border: '1px solid var(--border-color)',
            borderRadius: '12px',
            padding: '28px',
            width: '440px',
            maxHeight: '480px',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
            boxShadow: '0 24px 64px rgba(0, 0, 0, 0.5)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontFamily: "'Outfit', sans-serif", fontSize: '16px', fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Bell size={18} style={{ color: '#ef4444' }} />
                Recent Alerts
              </h3>
              <button onClick={() => setShowNotifications(false)} style={{ backgroundColor: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', padding: '4px' }}>
                <X size={18} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto', flex: 1 }}>
              {recentIncidentElements}
              {incidents.length === 0 && (
                <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", color: '#64748b', textAlign: 'center', padding: '24px', fontSize: '13px' }}>
                  No system alerts recorded.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <MainApp />
    </ErrorBoundary>
  );
}

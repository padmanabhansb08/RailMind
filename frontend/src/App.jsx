/* eslint-disable */
import React, { useState, useEffect, useRef, useMemo } from 'react';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import LiveMap from './components/LiveMap';
import IncidentFeed from './components/IncidentFeed';
import TaskBoard from './components/TaskBoard';
import RouteIntelligence from './components/RouteIntelligence';
import { ShieldAlert, AlertTriangle, Info, Check, CornerDownRight, Terminal, RefreshCw, X, Shield, User, HelpCircle, Activity, Bell, Settings } from 'lucide-react';

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
          backgroundColor: '#080a0d',
          color: '#ff3366',
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: "'JetBrains Mono', monospace",
          gap: '16px'
        }}>
          <h2 style={{ fontWeight: 600 }}>[ SYSTEM ERROR // RAILMIND CRASH ]</h2>
          <p style={{ color: '#8a9ba8', fontSize: '13px' }}>RailMind Dashboard encountered an unrecoverable rendering error.</p>
          <button 
            onClick={() => window.location.reload()}
            style={{
              padding: '10px 20px',
              backgroundColor: '#00f0ff',
              color: '#080a0d',
              border: 'none',
              borderRadius: '0px',
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
  const [showSettings, setShowSettings] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfile, setShowProfile] = useState(false);

  const recentIncidentElements = useMemo(() => {
    const result = [];
    const len = Math.min(incidents.length, 5);
    for (let i = 0; i < len; i++) {
      const inc = incidents[i];
      result.push(
        <div key={inc.id} className="palantir-mono" style={{
          backgroundColor: '#121820',
          border: '1px solid #1a2433',
          padding: '10px 14px',
          borderRadius: '0px',
          fontSize: '11px',
          color: '#cbd5e1'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ color: '#ff3366', fontWeight: 700 }}>{inc.severity.toUpperCase()}</span>
            <span style={{ color: '#5c7080' }}>{inc.timestamp}</span>
          </div>
          {inc.title}
        </div>
      );
    }
    return result;
  }, [incidents]);

  const socketRef = useRef(null);
  const API_BASE = `http://${window.location.hostname}:8000`;

  // Fetch functions
  const fetchIncidents = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/incidents`);
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
        setIncidentCount(formatted.length);
      }
    } catch (err) {
      console.error("[API] Failed to fetch incidents:", err);
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

  useEffect(() => {
    fetchIncidents();
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
            setIncidentCount(prev => prev + 1);
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

  const handleApprove = async (incidentId) => {
    console.log(`Approving reroute plan for incident: ${incidentId}`);
    const adminPassword = window.prompt("Enter Admin Password to approve this reroute plan:");
    if (adminPassword === null) {
      return; // User cancelled
    }
    try {
      const headers = new Headers();
      headers.set('Authorization', 'Basic ' + btoa('admin:' + adminPassword));
      const res = await fetch(`${API_BASE}/api/incidents/${incidentId}/approve`, {
        method: 'POST',
        headers: headers
      });
      if (res.ok) {
        setIncidents(prev => prev.map(inc => {
          if (inc.id === incidentId) {
            return { ...inc, approved: true };
          }
          return inc;
        }));
      } else if (res.status === 401) {
        alert("Incorrect admin password.");
        console.error("Unauthorized: Incorrect admin password.");
      } else {
        console.error("Failed to approve incident reroute plan on backend");
      }
    } catch (err) {
      console.error("Error approving reroute plan:", err);
    }
  };

  const handleAcknowledge = (incidentId) => {
    console.log(`Acknowledging warning incident: ${incidentId}`);
    setIncidents(prev => prev.filter(inc => inc.id !== incidentId));
    setIncidentCount(prev => Math.max(0, prev - 1));
  };

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
  const IncidentFeedView = () => {
    const [filter, setFilter] = useState('ALL');
    const [expandedIncident, setExpandedIncident] = useState(null);

    const filteredIncidents = incidents.filter(inc => {
      if (filter === 'ALL') return true;
      return inc.severity?.toUpperCase() === filter;
    });

    return (
      <div style={{ padding: '24px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 className="palantir-mono" style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc' }}>ANOMALY COMMAND CENTER</h2>
            <p className="palantir-mono" style={{ fontSize: '11px', color: '#5c7080' }}>OPERATIONAL ALERTS AUDIT FEED</p>
          </div>
          {/* Filters */}
          <div style={{ display: 'flex', gap: '8px', backgroundColor: '#0d1117', padding: '4px', borderRadius: '0px', border: '1px solid #1a2433' }}>
            {['ALL', 'CRITICAL', 'WARNING', 'INFO'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className="palantir-mono"
                style={{
                  padding: '6px 12px',
                  backgroundColor: filter === f ? '#00f0ff' : 'transparent',
                  color: filter === f ? '#080a0d' : '#8a9ba8',
                  border: 'none',
                  borderRadius: '0px',
                  fontSize: '10px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '16px' }}>
          {filteredIncidents.length === 0 ? (
            <div className="palantir-mono" style={{ gridColumn: '1 / -1', padding: '40px', textAlign: 'center', color: '#5c7080', backgroundColor: '#0d1117', border: '1px dashed #1a2433' }}>
              [ NO ANOMALIES RECORDED FOR STATUS: {filter} ]
            </div>
          ) : (
            filteredIncidents.map(inc => {
              const isCritical = inc.severity === 'critical';
              const isWarning = inc.severity === 'warning';
              const borderColor = isCritical ? '#ff3366' : isWarning ? '#ffb300' : '#00f0ff';

              return (
                <div key={inc.id} style={{
                  backgroundColor: '#121820',
                  border: '1px solid #1a2433',
                  borderLeft: `4px solid ${borderColor}`,
                  borderRadius: '0px',
                  padding: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="palantir-mono" style={{
                      fontSize: '9px',
                      fontWeight: 700,
                      color: borderColor,
                      backgroundColor: `${borderColor}0c`,
                      padding: '3px 8px',
                      border: `1px solid ${borderColor}`,
                      textTransform: 'uppercase'
                    }}>{inc.severity}</span>
                    <span className="palantir-mono" style={{ fontSize: '11px', color: '#5c7080' }}>{inc.timestamp}</span>
                  </div>

                  <div>
                    <h3 className="palantir-mono" style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>{inc.title}</h3>
                    <p className="palantir-mono" style={{ fontSize: '11px', color: '#8a9ba8', marginTop: '4px' }}>TRAIN: {inc.train_number}</p>
                  </div>

                  {inc.reroute_plan && (
                    <div style={{
                      backgroundColor: 'rgba(0, 240, 255, 0.02)',
                      border: '1px dashed #1a2433',
                      padding: '12px',
                      borderRadius: '0px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px'
                    }}>
                      <div className="palantir-mono" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '9px', color: '#5c7080', fontWeight: 700 }}>
                        <CornerDownRight size={12} style={{ color: '#00f0ff' }} />
                        REROUTE PLAN COMMAND
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
                        <span className="palantir-mono" style={{ fontSize: '11px', color: '#cbd5e1' }}>{inc.reroute_plan}</span>
                        {inc.approved ? (
                          <span className="palantir-mono" style={{ color: '#00e676', fontSize: '10px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '2px' }}>
                            <Check size={12} /> APPROVED
                          </span>
                        ) : (
                          <button
                            onClick={() => handleApprove(inc.id)}
                            className="palantir-mono"
                            style={{
                              backgroundColor: '#00f0ff',
                              color: '#080a0d',
                              border: 'none',
                              borderRadius: '0px',
                              padding: '4px 10px',
                              fontSize: '10px',
                              fontWeight: 700,
                              cursor: 'pointer'
                            }}
                          >
                            APPROVE
                          </button>
                        )}
                      </div>
                    </div>
                  )}

                  <div style={{ borderTop: '1px solid #1a2433', paddingTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="palantir-mono" style={{ fontSize: '10px', color: '#5c7080' }}>
                      DISPATCH: {inc.departments.join(' // ') || 'NONE'}
                    </span>
                    <button
                      onClick={() => setExpandedIncident(expandedIncident === inc.id ? null : inc.id)}
                      className="palantir-mono"
                      style={{
                        backgroundColor: 'transparent',
                        border: 'none',
                        color: '#00f0ff',
                        fontSize: '11px',
                        cursor: 'pointer',
                        fontWeight: 600
                      }}
                    >
                      {expandedIncident === inc.id ? 'HIDE DETAILS' : 'VIEW DETAILS'}
                    </button>
                  </div>

                  {expandedIncident === inc.id && (
                    <div className="palantir-mono" style={{
                      backgroundColor: '#080a0d',
                      border: '1px solid #1a2433',
                      padding: '12px',
                      borderRadius: '0px',
                      fontSize: '11px',
                      color: '#8a9ba8',
                      whiteSpace: 'pre-wrap',
                      marginTop: '4px'
                    }}>
                      {inc.description}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    );
  };

  const AnalyticsView = () => {
    const criticalCount = incidents.filter(i => i.severity === 'critical').length;
    const warningCount = incidents.filter(i => i.severity === 'warning').length;
    const infoCount = incidents.filter(i => i.severity === 'info').length;
    const totalCount = incidents.length;

    const maxCount = Math.max(criticalCount, warningCount, infoCount, 1);

    return (
      <div style={{ padding: '24px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div>
          <h2 className="palantir-mono" style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc' }}>OPERATIONS ANALYTICS</h2>
          <p className="palantir-mono" style={{ fontSize: '11px', color: '#5c7080' }}>HISTORICAL ANOMALY & AGENT CYCLES TIMELINE</p>
        </div>

        {/* Stats Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
          {[
            { label: 'TOTAL INCIDENTS', val: totalCount, color: '#00f0ff' },
            { label: 'CRITICAL ALERTS', val: criticalCount, color: '#ff3366' },
            { label: 'AGENT COGNITIVE LOOPS', val: loopCount, color: '#00e676' },
            { label: 'AVG ANOMALY RESOLUTION', val: '4.2 min', color: '#cbd5e1' }
          ].map((stat, idx) => (
            <div key={idx} style={{
              backgroundColor: '#0d1117',
              border: '1px solid #1a2433',
              borderRadius: '0px',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}>
              <span className="palantir-mono" style={{ fontSize: '9px', fontWeight: 600, color: '#5c7080', letterSpacing: '0.5px' }}>{stat.label}</span>
              <span className="palantir-mono" style={{ fontSize: '28px', fontWeight: 700, color: stat.color }}>{stat.val}</span>
            </div>
          ))}
        </div>

        {/* Charts and Data Representation */}
        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
          {/* Custom SVG Bar Chart */}
          <div style={{
            flex: 1,
            minWidth: '340px',
            backgroundColor: '#0d1117',
            border: '1px solid #1a2433',
            borderRadius: '0px',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}>
            <h3 className="palantir-mono" style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc', letterSpacing: '0.5px' }}>INCIDENTS BY SEVERITY</h3>
            <div style={{ display: 'flex', justifyContent: 'space-around', alignItems: 'flex-end', height: '180px', paddingTop: '20px' }}>
              {[
                { name: 'Critical', count: criticalCount, color: '#ff3366' },
                { name: 'Warning', count: warningCount, color: '#ffb300' },
                { name: 'Info', count: infoCount, color: '#00f0ff' }
              ].map((bar, idx) => {
                const heightPercent = (bar.count / maxCount) * 140; // max height 140px
                return (
                  <div key={idx} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', width: '60px' }}>
                    <span className="palantir-mono" style={{ fontSize: '12px', fontWeight: 600, color: '#fff' }}>{bar.count}</span>
                    <div style={{
                      width: '32px',
                      height: `${Math.max(heightPercent, 6)}px`,
                      backgroundColor: bar.color,
                      borderRadius: '0px',
                      transition: 'height 0.5s ease-out'
                    }}></div>
                    <span className="palantir-mono" style={{ fontSize: '10px', color: '#5c7080' }}>{bar.name}</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{
            flex: 1,
            minWidth: '340px',
            backgroundColor: '#0d1117',
            border: '1px solid #1a2433',
            borderRadius: '0px',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}>
            <h3 className="palantir-mono" style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc', letterSpacing: '0.5px' }}>CORE SYSTEM STATUS REPORT</h3>
            <div className="palantir-mono" style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '11px', color: '#cbd5e1', marginTop: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #2b3240', paddingBottom: '6px' }}>
                <span>Operations Agent State</span>
                <span style={{ color: '#10b981', fontWeight: 600 }}>[ ACTIVE // NOMINAL ]</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #2b3240', paddingBottom: '6px' }}>
                <span>Primary API Client</span>
                <span style={{ color: '#10b981', fontWeight: 600 }}>[ ACTIVE // LIVE TELEMETRY ]</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #2b3240', paddingBottom: '6px' }}>
                <span>Database Client</span>
                <span style={{ color: '#10b981', fontWeight: 600 }}>[ ACTIVE // MONGO PERSISTENCE ]</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px' }}>
                <span>SMS Alert Dispatcher</span>
                <span style={{ color: '#10b981', fontWeight: 600 }}>[ ACTIVE // TWILIO DISPATCH ]</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const SupportView = () => {
    return (
      <div style={{ padding: '40px', flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '20px', color: '#e2e8f0', textAlign: 'center' }}>
        <div style={{
          backgroundColor: '#0d1117',
          border: '1px solid #00f0ff',
          boxShadow: '0 0 15px rgba(0, 240, 255, 0.15)',
          borderRadius: '0px',
          padding: '40px 60px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '16px',
          maxWidth: '560px'
        }}>
          <ShieldAlert size={48} style={{ color: '#00f0ff' }} />
          <h2 className="palantir-mono" style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc', letterSpacing: '1px' }}>RAILMIND TERMINAL PORTAL</h2>
          <p className="palantir-mono" style={{ fontSize: '12px', color: '#8a9ba8', lineHeight: '1.6' }}>
            RailMind SECURE v1.0 — Multi-Agent Railway Cognitive Engine.<br />
            Secure operations console interface.
          </p>
          <div style={{ width: '100%', height: '1px', backgroundColor: '#1a2433', margin: '10px 0' }}></div>
          <span className="palantir-mono" style={{ fontSize: '10px', color: '#ff3366', fontWeight: 600, letterSpacing: '0.5px' }}>
            [ AUTHORIZED MILITARY / COGNITIVE AGENTS ONLY • SEC-SESSION 402 ]
          </span>
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
            <h2 className="palantir-mono" style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Terminal size={20} style={{ color: '#00f0ff' }} />
              COGNITIVE OPERATIONS STREAM
            </h2>
            <p className="palantir-mono" style={{ fontSize: '11px', color: '#5c7080' }}>REAL-TIME AGENT STATE MACHINE TRACE</p>
          </div>
          <button
            onClick={onClear}
            className="palantir-mono"
            style={{
              padding: '6px 12px',
              backgroundColor: 'transparent',
              border: '1px solid #1a2433',
              borderRadius: '0px',
              color: '#8a9ba8',
              fontSize: '10px',
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
            onMouseEnter={e => {
              e.currentTarget.style.backgroundColor = '#17202b';
              e.currentTarget.style.borderColor = '#00f0ff';
              e.currentTarget.style.color = '#e2e8f0';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.borderColor = '#1a2433';
              e.currentTarget.style.color = '#8a9ba8';
            }}
          >
            CLEAR LOGSTREAM
          </button>
        </div>

        <div style={{
          flex: 1,
          backgroundColor: '#05070a',
          border: '1px solid #1a2433',
          borderRadius: '0px',
          padding: '20px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '11px',
          color: '#00f0ff',
          boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.8)'
        }}>
          {logs.length === 0 ? (
            <div className="palantir-mono" style={{ color: '#5c7080', fontStyle: 'italic' }}>
              [SYSTEM] Awaiting live logs from operations agent stream...
            </div>
          ) : (
            logs.map((log, idx) => (
              <div key={idx} style={{ lineBreak: 'anywhere' }}>
                <span style={{ color: '#ffb300' }}>{log.message.substring(0, 21)}</span>
                <span style={{ color: '#00f0ff' }}>{log.message.substring(21, 35)}</span>
                <span style={{ color: '#e2e8f0' }}>{log.message.substring(35)}</span>
              </div>
            ))
          )}
          <div ref={logEndRef}></div>
        </div>
      </div>
    );
  };

  const TelemetryView = () => {
    const [telemetry, setTelemetry] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchTelemetry = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/telemetry`);
        if (res.ok) {
          const data = await res.json();
          setTelemetry(data);
        }
      } catch (err) {
        console.error("Failed to fetch telemetry:", err);
      } finally {
        setLoading(false);
      }
    };

    useEffect(() => {
      fetchTelemetry();
      const interval = setInterval(fetchTelemetry, 5000);
      return () => clearInterval(interval);
    }, []);

    if (loading && !telemetry) {
      return <div className="palantir-mono" style={{ padding: '24px', color: '#8a9ba8', fontSize: '12px' }}>[ Retrieving Sensor Data... ]</div>;
    }

    const metrics = [
      { name: 'Agent Loop Status', value: telemetry?.agent_loop_status?.toUpperCase() || 'RUNNING', color: '#00e676' },
      { name: 'Last API Call Check', value: telemetry?.last_api_call || 'Never', color: '#cbd5e1' },
      { name: 'Indian Railways Latency', value: `${telemetry?.railways_latency_ms || 0} ms`, color: '#00f0ff' },
      { name: 'AI Cognitive Latency', value: `${telemetry?.ai_latency_ms || 0} ms`, color: '#00f0ff' },
      { name: 'Live WS Connections', value: telemetry?.websocket_clients || 0, color: '#ffb300' },
      { name: 'MongoDB Incident Collections', value: telemetry?.mongodb_incidents || 0, color: '#ff3366' },
      { name: 'MongoDB Task Collections', value: telemetry?.mongodb_tasks || 0, color: '#ff3366' },
    ];

    return (
      <div style={{ padding: '24px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 className="palantir-mono" style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc' }}>System Metrics & Sensor Data</h2>
          <p className="palantir-mono" style={{ fontSize: '11px', color: '#5c7080' }}>Real-time Hardware & Multi-agent State Data</p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '16px' }}>
          {metrics.map((m, idx) => (
            <div key={idx} style={{
              backgroundColor: '#0d1117',
              border: '1px solid #1a2433',
              borderRadius: '0px',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}>
              <span className="palantir-mono" style={{ fontSize: '10px', fontWeight: 600, color: '#5c7080' }}>{m.name}</span>
              <span className="palantir-mono" style={{ fontSize: '20px', fontWeight: 700, color: m.color, textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }} title={m.value}>{m.value}</span>
            </div>
          ))}
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
      return <div className="palantir-mono" style={{ padding: '24px', color: '#8a9ba8', fontSize: '12px' }}>[ Retrieving Timetable... ]</div>;
    }

    return (
      <div style={{ padding: '24px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 className="palantir-mono" style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc' }}>Rail Network Timetable</h2>
          <p className="palantir-mono" style={{ fontSize: '11px', color: '#5c7080' }}>Auto-refresh Interval [30s]</p>
        </div>

        <div style={{
          backgroundColor: '#0d1117',
          border: '1px solid #1a2433',
          borderRadius: '0px',
          overflow: 'hidden'
        }}>
          <table className="palantir-mono" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12px' }}>
            <thead>
              <tr style={{ backgroundColor: '#121820', borderBottom: '1px solid #1a2433', color: '#8a9ba8' }}>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>TRAIN NO</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>NAME</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>CORRIDOR ROUTE</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>STATUS</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>DELAY OFFSET</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>GPS POSITION</th>
              </tr>
            </thead>
            <tbody>
              {scheduleTrains.map((train, idx) => {
                const isDelayed = train.delay_minutes > 0;
                const statusColor = train.status === 'cancelled' ? '#ff3366' : isDelayed ? '#ffb300' : '#00e676';
                return (
                  <tr key={idx} style={{
                    borderBottom: '1px solid #121820',
                    color: '#cbd5e1',
                    backgroundColor: idx % 2 === 0 ? '#0d1117' : '#0f141b'
                  }}>
                    <td style={{ padding: '12px 16px', fontWeight: 700, color: '#00f0ff' }}>{train.train_number}</td>
                    <td style={{ padding: '12px 16px' }}>{train.train_name}</td>
                    <td style={{ padding: '12px 16px' }}>{train.source || 'NDLS'} → {train.destination || 'RKMP'}</td>
                    <td style={{ padding: '12px 16px', fontWeight: 600, color: statusColor }}>
                      {train.status?.toUpperCase() || 'UNKNOWN'}
                    </td>
                    <td style={{ padding: '12px 16px', color: isDelayed ? '#ffb300' : '#5c7080' }}>
                      {isDelayed ? `+${train.delay_minutes} min` : '--'}
                    </td>
                    <td style={{ padding: '12px 16px', color: '#8a9ba8' }}>{train.current_station || 'GPS LOSS'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const AssetsView = () => {
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/system-status`);
        if (res.ok) {
          const data = await res.json();
          setStatus(data);
        }
      } catch (err) {
        console.error("Failed to fetch system status:", err);
      } finally {
        setLoading(false);
      }
    };

    useEffect(() => {
      fetchStatus();
    }, []);

    if (loading && !status) {
      return <div className="palantir-mono" style={{ padding: '24px', color: '#8a9ba8', fontSize: '12px' }}>[ Connecting to System Fleet... ]</div>;
    }

    const services = [
      { name: 'Core Orchestrator Node', status: status?.agent_status || 'ACTIVE', isConnected: true },
      { name: 'Cognitive Reasoning Model', status: status?.model || 'GEMINI 2.5 FLASH / CLAUDE', isConnected: true },
      { name: 'Indian Railways Telemetry API', status: status?.railways_api || 'Disconnected', isConnected: status?.railways_api === 'Connected' },
      { name: 'Twilio Warning Alert Gateway', status: status?.twilio_sms || 'Disconnected', isConnected: status?.twilio_sms === 'Connected' },
      { name: 'MongoDB Cloud Collections', status: status?.mongodb || 'Disconnected', isConnected: status?.mongodb === 'Connected' }
    ];

    return (
      <div style={{ padding: '24px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div>
          <h2 className="palantir-mono" style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc' }}>System Registry & Fleet</h2>
          <p className="palantir-mono" style={{ fontSize: '11px', color: '#5c7080' }}>Node Networks & Fleet Status</p>
        </div>

        {/* Connection Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
          {services.map((s, idx) => (
            <div key={idx} style={{
              backgroundColor: '#0d1117',
              border: '1px solid #1a2433',
              borderRadius: '0px',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="palantir-mono" style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc' }}>{s.name}</span>
                <span style={{
                  width: '6px',
                  height: '6px',
                  backgroundColor: s.isConnected ? '#00e676' : '#ff3366',
                  boxShadow: s.isConnected ? '0 0 6px #00e676' : '0 0 6px #ff3366'
                }}></span>
              </div>
              <span className="palantir-mono" style={{ fontSize: '13px', color: s.isConnected ? '#00e676' : '#ff3366', fontWeight: 700 }}>
                [ {s.status.toUpperCase()} ]
              </span>
            </div>
          ))}
        </div>

        {/* Contacts Section */}
        <div style={{
          backgroundColor: '#0d1117',
          border: '1px solid #1a2433',
          borderRadius: '0px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px'
        }}>
          <h3 className="palantir-mono" style={{ fontSize: '13px', fontWeight: 600, color: '#f8fafc' }}>NODE DISPATCH CONTACTS REGISTRY</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '16px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <span className="palantir-mono" style={{ fontSize: '10px', color: '#5c7080', fontWeight: 600 }}>MAINTENANCE COORDINATES</span>
              <span className="palantir-mono" style={{ fontSize: '13px', color: '#cbd5e1', fontWeight: 500 }}>{status?.contacts?.maintenance || 'MOCK_GATEWAY'}</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <span className="palantir-mono" style={{ fontSize: '10px', color: '#5c7080', fontWeight: 600 }}>OPERATIONS CONTROLLERS</span>
              <span className="palantir-mono" style={{ fontSize: '13px', color: '#cbd5e1', fontWeight: 500 }}>{status?.contacts?.operations || 'MOCK_GATEWAY'}</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <span className="palantir-mono" style={{ fontSize: '10px', color: '#5c7080', fontWeight: 600 }}>STATION MANAGERS DESK</span>
              <span className="palantir-mono" style={{ fontSize: '13px', color: '#cbd5e1', fontWeight: 500 }}>{status?.contacts?.station_manager || 'MOCK_GATEWAY'}</span>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const SimulationView = () => {
    const [selectedTrain, setSelectedTrain] = useState(trains[0]?.train_number || '12301');
    const [delayMinutes, setDelayMinutes] = useState(60);
    const [status, setStatus] = useState('Delayed');
    const [currentStation, setCurrentStation] = useState('Kanpur Central');
    const [isInjected, setIsInjected] = useState(false);
    const [isResetting, setIsResetting] = useState(false);

    const handleInject = async () => {
      setIsInjected(true);
      try {
        const res = await fetch(`${API_BASE}/api/simulate-anomaly`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            train_number: selectedTrain,
            delay_minutes: parseInt(delayMinutes),
            status: status,
            current_station: currentStation
          })
        });
        if (res.ok) {
          console.log("[SIMULATION] Anomaly successfully injected.");
          setTimeout(() => {
            fetchTrains();
            fetchIncidents();
            fetchTasks();
          }, 3000);
        }
      } catch (err) {
        console.error("Failed to inject anomaly:", err);
      } finally {
        setTimeout(() => setIsInjected(false), 2000);
      }
    };

    const handleReset = async () => {
      setIsResetting(true);
      try {
        const res = await fetch(`${API_BASE}/api/reset-simulation`, {
          method: 'POST'
        });
        if (res.ok) {
          console.log("[SIMULATION] Simulation registry reset.");
          setTimeout(() => {
            fetchTrains();
            fetchIncidents();
            fetchTasks();
          }, 3000);
        }
      } catch (err) {
        console.error("Failed to reset simulation:", err);
      } finally {
        setTimeout(() => setIsResetting(false), 2000);
      }
    };

    return (
      <div style={{ padding: '24px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div>
          <h2 className="palantir-mono" style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc' }}>ANOMALY SIMULATION COMMAND</h2>
          <p className="palantir-mono" style={{ fontSize: '11px', color: '#5c7080' }}>INJECT TELEMETRY OVERRIDES AND TEST AGENT COGNITION</p>
        </div>

        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
          <div style={{
            flex: 2,
            minWidth: '360px',
            backgroundColor: '#0d1117',
            border: '1px solid #1a2433',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px'
          }}>
            <h3 className="palantir-mono" style={{ fontSize: '13px', fontWeight: 600, color: '#00f0ff', borderBottom: '1px solid #1a2433', paddingBottom: '10px' }}>
              INJECTION CONFIGURATION
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label className="palantir-mono" style={{ fontSize: '10px', color: '#8a9ba8', fontWeight: 600 }}>SELECT CORRIDOR TRAIN</label>
                <select
                  value={selectedTrain}
                  onChange={(e) => setSelectedTrain(e.target.value)}
                  className="palantir-mono"
                  style={{
                    backgroundColor: '#121820',
                    border: '1px solid #1a2433',
                    color: '#f8fafc',
                    padding: '10px',
                    fontSize: '11px',
                    outline: 'none',
                    borderRadius: '0px',
                    width: '100%'
                  }}
                >
                  {trains.map(t => (
                    <option key={t.train_number} value={t.train_number}>
                      {t.train_number} - {t.train_name}
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label className="palantir-mono" style={{ fontSize: '10px', color: '#8a9ba8', fontWeight: 600 }}>ANOMALY TYPE / STATUS</label>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  className="palantir-mono"
                  style={{
                    backgroundColor: '#121820',
                    border: '1px solid #1a2433',
                    color: '#f8fafc',
                    padding: '10px',
                    fontSize: '11px',
                    outline: 'none',
                    borderRadius: '0px',
                    width: '100%'
                  }}
                >
                  <option value="Delayed">Delayed</option>
                  <option value="Cancelled">Cancelled</option>
                  <option value="Overcrowded">Overcrowded</option>
                  <option value="On Time">Nominal / On Time</option>
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label className="palantir-mono" style={{ fontSize: '10px', color: '#8a9ba8', fontWeight: 600 }}>DELAY OFFSET (MINUTES)</label>
                <input
                  type="number"
                  min="0"
                  max="480"
                  value={delayMinutes}
                  onChange={(e) => setDelayMinutes(e.target.value)}
                  className="palantir-mono"
                  style={{
                    backgroundColor: '#121820',
                    border: '1px solid #1a2433',
                    color: '#f8fafc',
                    padding: '10px',
                    fontSize: '11px',
                    outline: 'none',
                    borderRadius: '0px',
                    width: '100%'
                  }}
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label className="palantir-mono" style={{ fontSize: '10px', color: '#8a9ba8', fontWeight: 600 }}>STATION OVERRIDE COORDINATE</label>
                <input
                  type="text"
                  value={currentStation}
                  onChange={(e) => setCurrentStation(e.target.value)}
                  className="palantir-mono"
                  style={{
                    backgroundColor: '#121820',
                    border: '1px solid #1a2433',
                    color: '#f8fafc',
                    padding: '10px',
                    fontSize: '11px',
                    outline: 'none',
                    borderRadius: '0px',
                    width: '100%'
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', marginTop: '10px' }}>
              <button
                onClick={handleInject}
                disabled={isInjected}
                className="palantir-mono"
                style={{
                  flex: 1,
                  padding: '12px 20px',
                  backgroundColor: '#ff3366',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '0px',
                  fontWeight: 700,
                  fontSize: '11px',
                  cursor: 'pointer',
                  boxShadow: '0 0 10px rgba(255, 51, 102, 0.2)',
                  transition: 'opacity 0.2s',
                  opacity: isInjected ? 0.7 : 1
                }}
              >
                {isInjected ? "INJECTING ALARM..." : "TRIGGER ANOMALY INJECTION"}
              </button>

              <button
                onClick={handleReset}
                disabled={isResetting}
                className="palantir-mono"
                style={{
                  padding: '12px 20px',
                  backgroundColor: 'transparent',
                  color: '#8a9ba8',
                  border: '1px solid #1a2433',
                  borderRadius: '0px',
                  fontWeight: 700,
                  fontSize: '11px',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = '#00f0ff';
                  e.currentTarget.style.color = '#e2e8f0';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = '#1a2433';
                  e.currentTarget.style.color = '#8a9ba8';
                }}
              >
                {isResetting ? "RESETTING..." : "RESET ALL OVERRIDES"}
              </button>
            </div>
          </div>

          <div style={{
            flex: 1,
            minWidth: '280px',
            backgroundColor: '#0d1117',
            border: '1px dashed #1a2433',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px'
          }}>
            <h3 className="palantir-mono" style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc', letterSpacing: '0.5px' }}>
              HOW THE PIPELINE RESPONDS
            </h3>
            
            <div className="palantir-mono" style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '11px', color: '#8a9ba8' }}>
              <div style={{ display: 'flex', gap: '8px' }}>
                <span style={{ color: '#00f0ff', fontWeight: 700 }}>1.</span>
                <span>Telemetry data is overridden with the custom coordinates and delays.</span>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <span style={{ color: '#00f0ff', fontWeight: 700 }}>2.</span>
                <span>The **Detect Node** classifies the state and logs the anomaly severity.</span>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <span style={{ color: '#00f0ff', fontWeight: 700 }}>3.</span>
                <span>The **Reason Node** uses Gemini/Claude to formulate mitigation plans.</span>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <span style={{ color: '#00f0ff', fontWeight: 700 }}>4.</span>
                <span>**Dijkstra Detours** calculates emergency bypass routes.</span>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <span style={{ color: '#00f0ff', fontWeight: 700 }}>5.</span>
                <span>**Coordination Agents** dispatch tasks to all operational desks.</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'Dashboard':
        return (
          <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              flex: 1,
              borderRight: '1px solid #1a2433',
              backgroundColor: '#080a0d'
            }}>
              <div style={{ flex: 1, position: 'relative' }}>
                <LiveMap trains={trains} incidents={incidents} />
              </div>
              <TaskBoard tasks={tasks} onResolve={handleResolve} />
            </div>
            <IncidentFeed 
              incidents={incidents} 
              onApprove={handleApprove}
              onAcknowledge={handleAcknowledge}
            />
          </div>
        );

      case 'Live Map':
        return (
          <div style={{ flex: 1, position: 'relative', height: '100%' }}>
            <LiveMap trains={trains} incidents={incidents} />
          </div>
        );

      case 'Incident Feed':
        return <IncidentFeedView />;

      case 'Task Board':
        return (
          <div style={{ flex: 1, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <TaskBoard tasks={tasks} onResolve={handleResolve} fullScreen={true} />
          </div>
        );

      case 'Analytics':
        return <AnalyticsView />;

      case 'Support':
        return <SupportView />;

      case 'Logs':
        return <LogsView logs={logs} onClear={() => setLogs([])} />;

      case 'Sensor Data':
        return <RouteIntelligence trains={trains} />;

      case 'Timetable':
        return <SchedulesView />;

      case 'Fleet':
        return <AssetsView />;

      case 'Simulation':
        return <SimulationView />;

      default:
        return <div className="palantir-mono" style={{ padding: '24px', fontSize: '12px' }}>[ PAGE NOT DEPLOYED ]</div>;
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      backgroundColor: '#080a0d',
      overflow: 'hidden'
    }}>
      <TopBar 
        loopCount={loopCount} 
        incidentCount={incidentCount} 
        wsStatus={wsStatus} 
        activeTab={activeTab}
        onTabChange={(tab) => {
          if (tab === 'Rail Network') {
            setActiveTab('Dashboard');
          } else {
            setActiveTab(tab);
          }
        }}
        onSettingsClick={() => setShowSettings(true)}
        onNotificationsClick={() => setShowNotifications(true)}
        onProfileClick={() => setShowProfile(true)}
      />

      {wsStatus === 'reconnecting' && (
        <div style={{
          backgroundColor: '#ff3366',
          color: '#ffffff',
          textAlign: 'center',
          padding: '8px 24px',
          fontSize: '11px',
          fontWeight: 700,
          fontFamily: "'JetBrains Mono', monospace",
          letterSpacing: '1px',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          gap: '8px',
          zIndex: 1000,
          borderBottom: '1px solid #ff3366',
          boxShadow: '0 4px 20px rgba(255, 51, 102, 0.2)'
        }}>
          <span style={{
            display: 'inline-block',
            width: '6px',
            height: '6px',
            backgroundColor: '#ffffff',
            borderRadius: '50%',
            animation: 'pulse-live 1s infinite'
          }}></span>
          [ OFFLINE // RE-ESTABLISHING AGENT CONNECTION... ]
        </div>
      )}

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        {renderContent()}
      </div>

      {/* Settings Modal */}
      {showSettings && (
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
          backdropFilter: 'blur(3px)'
        }}>
          <div style={{
            backgroundColor: '#0d1117',
            border: '1px solid #00f0ff',
            borderRadius: '0px',
            padding: '24px',
            width: '420px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            boxShadow: '0 0 20px rgba(0, 240, 255, 0.2)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 className="palantir-mono" style={{ fontSize: '14px', fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Settings size={18} style={{ color: '#00f0ff' }} />
                SYSTEM // CONFIGURATION
              </h3>
              <button onClick={() => setShowSettings(false)} style={{ backgroundColor: 'transparent', border: 'none', color: '#5c7080', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>
            
            <div className="palantir-mono" style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '11px', color: '#cbd5e1' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input type="checkbox" defaultChecked style={{ accentColor: '#00f0ff' }} /> ALLOW COGNITIVE REROUTING DISPATCH
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input type="checkbox" defaultChecked style={{ accentColor: '#00f0ff' }} /> TELEMETRY CACHE / DATABASE FALLBACK
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input type="checkbox" defaultChecked style={{ accentColor: '#00f0ff' }} /> ENABLE REAL-TIME WS STREAMING
              </label>
            </div>

            <button
              onClick={() => setShowSettings(false)}
              className="palantir-mono"
              style={{
                marginTop: '10px',
                padding: '8px 16px',
                backgroundColor: '#00f0ff',
                color: '#080a0d',
                border: 'none',
                borderRadius: '0px',
                fontWeight: 700,
                fontSize: '11px',
                cursor: 'pointer'
              }}
            >
              SAVE CONFIGURATION
            </button>
          </div>
        </div>
      )}

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
          backdropFilter: 'blur(3px)'
        }}>
          <div style={{
            backgroundColor: '#0d1117',
            border: '1px solid #ff3366',
            borderRadius: '0px',
            padding: '24px',
            width: '420px',
            maxHeight: '400px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            boxShadow: '0 0 20px rgba(255, 51, 102, 0.15)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 className="palantir-mono" style={{ fontSize: '14px', fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Bell size={18} style={{ color: '#ff3366' }} />
                REAL-TIME WARNINGS STREAM
              </h3>
              <button onClick={() => setShowNotifications(false)} style={{ backgroundColor: 'transparent', border: 'none', color: '#5c7080', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto', flex: 1 }}>
              {recentIncidentElements}
              {incidents.length === 0 && (
                <div className="palantir-mono" style={{ color: '#5c7080', fontStyle: 'italic', textAlign: 'center', padding: '20px', fontSize: '11px' }}>
                  [ NO SYSTEM ALERTS RECORDED ]
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Profile Modal */}
      {showProfile && (
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
          backdropFilter: 'blur(3px)'
        }}>
          <div style={{
            backgroundColor: '#0d1117',
            border: '1px solid #00f0ff',
            borderRadius: '0px',
            padding: '28px',
            width: '380px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '16px',
            textAlign: 'center',
            boxShadow: '0 0 20px rgba(0, 240, 255, 0.2)'
          }}>
            <div style={{ alignSelf: 'stretch', display: 'flex', justifySelf: 'flex-end', justifyContent: 'flex-end' }}>
              <button onClick={() => setShowProfile(false)} style={{ backgroundColor: 'transparent', border: 'none', color: '#5c7080', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>

            <div style={{
              width: '80px',
              height: '80px',
              borderRadius: '0px',
              overflow: 'hidden',
              border: '1px solid #00f0ff',
              boxShadow: '0 0 15px rgba(0, 240, 255, 0.3)'
            }}>
              <img 
                src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&q=80" 
                alt="User profile" 
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            </div>

            <div>
              <h3 className="palantir-mono" style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc' }}>OPERATOR // SHREYAM</h3>
              <p className="palantir-mono" style={{ fontSize: '11px', color: '#00f0ff', fontWeight: 600 }}>CHIEF OPERATIONS MANAGER</p>
            </div>

            <div style={{ width: '100%', height: '1px', backgroundColor: '#1a2433' }}></div>

            <div className="palantir-mono" style={{ alignSelf: 'stretch', display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '11px', color: '#cbd5e1' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#5c7080' }}>OPERATIONS TERMINAL</span>
                <span>SEC-NODE-ALPHA</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#5c7080' }}>AUTHORIZATION LEVEL</span>
                <span style={{ color: '#ffb300', fontWeight: 600 }}>SEC-LEVEL-5</span>
              </div>
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

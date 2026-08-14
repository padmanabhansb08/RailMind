/* eslint-disable */
import React, { useState } from 'react';
import { ShieldAlert, AlertTriangle, Info, CheckCircle2, Lock, Unlock, BrainCircuit, Navigation } from 'lucide-react';

const STATION_COORDS = {
  "NDLS": [28.6419, 77.2194],
  "CNB": [26.4499, 80.3319],
  "ALD": [25.4358, 81.8463],
  "BSB": [25.3176, 82.9739],
  "BPL": [23.2599, 77.4126],
  "NGP": [21.1458, 79.0882],
  "BZA": [16.5193, 80.6305],
  "MAS": [13.0827, 80.2707],
  "HWH": [22.5958, 88.2636],
  "SDAH": [22.5697, 88.3697],
  "BWN": [23.2324, 87.8615],
  "GKP": [26.7606, 83.3732],
  "LDH": [30.9010, 75.8573],
  "LKO": [26.8467, 80.9462],
  "VSKP": [17.7231, 83.2985],
  "MDU": [9.9252, 78.1198]
};

const TRAIN_ROUTES = {
  "12301": "NDLS ➔ HWH",
  "12951": "NDLS ➔ MMCT",
  "12001": "NDLS ➔ RKMP",
  "12259": "NDLS ➔ SDAH",
  "12565": "DBG ➔ NDLS",
  "11057": "CSMT ➔ ASR",
  "12627": "NDLS ➔ SBC",
  "12625": "NDLS ➔ TVC",
  "12621": "NDLS ➔ MAS",
  "12615": "NDLS ➔ MAS",
  "12309": "RJPB ➔ NDLS",
  "12721": "VSKP ➔ NDLS",
  "12229": "LJN ➔ NDLS",
  "12311": "HWH ➔ KLK",
  "12641": "CAPE ➔ NZM"
};

const getRelativeTime = (timestampStr) => {
  if (!timestampStr) return "Just now";
  try {
    const parsed = new Date(timestampStr);
    const diffMs = new Date() - parsed;
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins <= 0) return "Just now";
    if (diffMins === 1) return "1 min ago";
    if (diffMins < 60) return `${diffMins} mins ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours === 1) return "1 hr ago";
    return `${diffHours} hrs ago`;
  } catch (e) {
    return "Recently";
  }
};

const MiniIndiaMap = ({ lat, lng, severityColor }) => {
  const minLat = 8.0;
  const maxLat = 36.0;
  const minLng = 68.0;
  const maxLng = 98.0;

  const width = 80;
  const height = 90;

  const x = ((lng - minLng) / (maxLng - minLng)) * width;
  const y = (1 - (lat - minLat) / (maxLat - minLat)) * height;

  const refStations = [
    { code: 'NDLS', lat: 28.6419, lng: 77.2194 },
    { code: 'HWH', lat: 22.5958, lng: 88.2636 },
    { code: 'CSTM', lat: 18.9398, lng: 72.8355 },
    { code: 'MAS', lat: 13.0827, lng: 80.2707 },
    { code: 'BPL', lat: 23.2599, lng: 77.4126 }
  ].map(s => ({
    ...s,
    x: ((s.lng - minLng) / (maxLng - minLng)) * width,
    y: (1 - (s.lat - minLat) / (maxLat - minLat)) * height
  }));

  return (
    <div style={{
      width: `${width}px`,
      height: `${height}px`,
      border: '1px solid #1a2433',
      backgroundColor: '#05070a',
      position: 'relative',
      borderRadius: '2px',
      overflow: 'hidden',
      flexShrink: 0
    }}>
      <svg width={width} height={height}>
        {/* Simplified Outline */}
        <polygon
          points="20,4 40,4 48,15 44,26 60,26 68,45 74,58 66,63 62,75 52,80 40,85 35,82 30,73 22,63 14,57 9,48 11,38 16,35 14,28 20,22"
          fill="none"
          stroke="#1a2433"
          strokeWidth="1"
          strokeDasharray="2,2"
        />
        {/* Reference station dots */}
        {refStations.map(s => (
          <circle
            key={s.code}
            cx={s.x}
            cy={s.y}
            r="1.2"
            fill="#5c7080"
            opacity="0.5"
          />
        ))}
        {/* Active Train dot */}
        {lat && lng && (
          <>
            <circle
              cx={x}
              cy={y}
              r="3.5"
              fill={severityColor}
            />
            <circle
              cx={x}
              cy={y}
              r="7"
              fill="none"
              stroke={severityColor}
              strokeWidth="0.8"
              style={{ opacity: 0.7 }}
            />
          </>
        )}
      </svg>
    </div>
  );
};

const getRouteGraphic = (trainNo, stationCode) => {
  const trainRoutes = {
    "12301": { src: "Delhi", dest: "Howrah" },
    "12951": { src: "Delhi", dest: "Mumbai" },
    "12001": { src: "Delhi", dest: "Bhopal" },
    "12259": { src: "Delhi", dest: "Sealdah" },
    "12565": { src: "Darbhanga", dest: "Delhi" },
    "11057": { src: "Mumbai", dest: "Amritsar" },
    "12627": { src: "Delhi", dest: "Bangalore" },
    "12625": { src: "Delhi", dest: "Trivandrum" },
    "12621": { src: "Delhi", dest: "Chennai" },
    "12615": { src: "Delhi", dest: "Chennai" },
    "12309": { src: "Patna", dest: "Delhi" },
    "12721": { src: "Visakhapatnam", dest: "Delhi" },
    "12229": { src: "Lucknow", dest: "Delhi" },
    "12311": { src: "Howrah", dest: "Kalka" },
    "12641": { src: "Kanyakumari", dest: "Delhi" }
  };
  
  const route = trainRoutes[trainNo] || { src: "Delhi", dest: "Howrah" };
  const displayCode = stationCode || "CNB";
  return (
    <div style={{ display: 'flex', flexDirection: 'column', margin: '4px 0', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color: '#cbd5e1' }}>
      <div style={{ display: 'flex', alignItems: 'center', width: '100%', justifyContent: 'space-between', gap: '8px' }}>
        <span style={{ fontWeight: 600 }}>{route.src}</span>
        <span style={{ flex: 1, textAlign: 'center', color: '#5c7080', letterSpacing: '-1.5px', overflow: 'hidden', whiteSpace: 'nowrap' }}>
          —————————————●—————————————→
        </span>
        <span style={{ fontWeight: 600 }}>{route.dest}</span>
      </div>
      <div style={{ textAlign: 'center', fontSize: '9px', color: '#ffb300', marginTop: '-4px', fontWeight: 'bold' }}>
        {displayCode}
      </div>
    </div>
  );
};

export default function IncidentFeed({ incidents = [], onApprove, onOverride, onAcknowledge }) {
  const [expandedIds, setExpandedIds] = useState(new Set());
  const [logExport, setLogExport] = useState(false);
  const [activeOverrideId, setActiveOverrideId] = useState(null);
  const [overrideText, setOverrideText] = useState("");

  const toggleExpand = (id) => {
    const next = new Set(expandedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setExpandedIds(next);
  };

  const getSeverityStyles = (severity = "info") => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return { color: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)', icon: ShieldAlert };
      case 'warning':
      case 'medium':
      case 'high':
        return { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)', icon: AlertTriangle };
      default:
        return { color: '#06b6d4', bg: 'rgba(6, 182, 212, 0.1)', icon: Info };
    }
  };

  const getCoords = (incident) => {
    let station = incident.current_station || "";
    const text = `${incident.title} ${incident.description} ${station}`.toUpperCase();
    if (text.includes("KANPUR") || text.includes("CNB")) return [26.4499, 80.3319];
    if (text.includes("DELHI") || text.includes("NDLS")) return [28.6419, 77.2194];
    if (text.includes("PRAYAGRAJ") || text.includes("ALLAHABAD") || text.includes("ALD")) return [25.4358, 81.8463];
    if (text.includes("VARANASI") || text.includes("BSB")) return [25.3176, 82.9739];
    if (text.includes("BHOPAL") || text.includes("BPL")) return [23.2599, 77.4126];
    if (text.includes("NAGPUR") || text.includes("NGP")) return [21.1458, 79.0882];
    if (text.includes("VIJAYAWADA") || text.includes("BZA")) return [16.5193, 80.6305];
    if (text.includes("CHENNAI") || text.includes("MAS")) return [13.0827, 80.2707];
    if (text.includes("HOWRAH") || text.includes("HWH")) return [22.5958, 88.2636];
    if (text.includes("SEALDAH") || text.includes("SDAH")) return [22.5697, 88.3697];
    if (text.includes("BARDHAMAN") || text.includes("BWN")) return [23.2324, 87.8615];
    if (text.includes("GORAKHPUR") || text.includes("GKP")) return [26.7606, 83.3732];
    if (text.includes("LUDHIANA") || text.includes("LDH")) return [30.9010, 75.8573];
    if (text.includes("LUCKNOW") || text.includes("LKO")) return [26.8467, 80.9462];
    if (text.includes("VISAKHAPATNAM") || text.includes("VSKP")) return [17.7231, 83.2985];
    if (text.includes("MADURAI") || text.includes("MDU")) return [9.9252, 78.1198];
    return [20.5937, 78.9629];
  };

  const activeCount = incidents.filter(inc => inc.resolution_status === 'pending' || !inc.approved).length;

  return (
    <div style={{
      width: '340px',
      backgroundColor: '#090b0e',
      borderLeft: '1px solid #2b3240',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      flexShrink: 0
    }}>
      {/* Header */}
      <div style={{
        padding: '20px',
        borderBottom: '1px solid #2b3240',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: '#090b0e'
      }}>
        <div>
          <h2 style={{ fontFamily: "'Outfit', sans-serif", fontSize: '13px', fontWeight: 600, color: '#f8fafc', letterSpacing: '1px', margin: 0 }}>
            LIVE OPERATION ALERTS [{activeCount}]
          </h2>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            display: 'inline-block',
            width: '8px',
            height: '8px',
            backgroundColor: activeCount > 0 ? '#ef4444' : '#10b981',
            borderRadius: '50%',
            animation: activeCount > 0 ? 'pulse-live 1.2s infinite' : 'none'
          }}></span>
          <span className="palantir-mono" style={{ fontSize: '9px', color: '#64748b', fontWeight: 600 }}>TACTICAL FEED</span>
        </div>
      </div>

      {/* Feed list */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}>
        {incidents.length === 0 ? (
          <div className="palantir-mono" style={{
            color: '#5c7080',
            fontSize: '11px',
            textAlign: 'center',
            padding: '30px 10px',
            border: '1px dashed #1a2433'
          }}>
            [ NO ACTIVE OPERATIONS ALERTS RECORDED ]
          </div>
        ) : (
          incidents.map((incident) => {
            const isExpanded = expandedIds.has(incident.id);
            const severityStyles = getSeverityStyles(incident.severity);
            const SeverityIcon = severityStyles.icon;
            
            const trainNumber = incident.train_number || "12301";
            const trainName = incident.train_name || "Howrah Rajdhani";
            const delayMins = incident.delay_minutes || 45;
            const currentStationName = incident.current_station || "Kanpur Central";
            
            // Extract route and display code
            const displayCode = incident.current_station ? (incident.current_station.includes("(") ? incident.current_station.match(/\(([^)]+)\)/)?.[1] : incident.current_station) : "CNB";
            const routeGraphic = getRouteGraphic(trainNumber, displayCode);

            const isOverriding = activeOverrideId === incident.id;
            
            const passengersText = incident.passenger_impact || `👥 ~2,847 passengers affected`;
            const predictionText = incident.prediction || `If unresolved: 3 more trains will be delayed by 14:30`;
            const confidenceScore = incident.confidence_score || 94;

            return (
              <div 
                key={incident.id} 
                style={{
                  backgroundColor: '#11141a',
                  border: `1px solid #2b3240`,
                  borderLeft: `4px solid ${severityStyles.color}`,
                  borderRadius: '6px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
                }}
              >
                {/* Header: Severity & Timer */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <SeverityIcon size={12} style={{ color: severityStyles.color }} />
                    <span style={{
                      fontSize: '9px',
                      fontWeight: 800,
                      color: severityStyles.color,
                      letterSpacing: '0.5px'
                    }}>
                      {incident.severity?.toUpperCase()}
                    </span>
                  </div>
                  <div style={{ fontSize: '9px', color: '#5c7080' }}>
                    {getRelativeTime(incident.timestamp_iso)}
                  </div>
                </div>

                {/* Train Name & Number */}
                <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '14px', fontWeight: '700', color: '#ffffff' }}>
                  {trainNumber} {trainName}
                </div>

                {/* Delay description */}
                <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '12px', color: '#cbd5e1' }}>
                  {delayMins}min delay at {currentStationName}
                </div>

                {/* Corridor Graphic */}
                {routeGraphic}

                {/* Passengers Affected */}
                <div style={{ fontSize: '10px', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '4px', margin: '4px 0' }}>
                  {passengersText.includes("👥") ? passengersText : `👥 ~${passengersText}`}
                </div>

                {/* Memory Used (Transformation 8) */}
                {incident.memory_used && (
                  <div style={{
                    backgroundColor: 'rgba(0, 240, 255, 0.05)',
                    border: '1px solid rgba(0, 240, 255, 0.2)',
                    padding: '8px',
                    fontSize: '9px',
                    color: '#00f0ff',
                    borderRadius: '2px',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '6px'
                  }}>
                    <BrainCircuit size={12} style={{ flexShrink: 0, marginTop: '2px' }} />
                    <span>{incident.memory_used}</span>
                  </div>
                )}

                {/* Agent Decision */}
                <div style={{
                  backgroundColor: '#090b0e',
                  border: '1px solid #2b3240',
                  borderRadius: '4px',
                  padding: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #1e293b', paddingBottom: '6px' }}>
                    <span style={{ fontFamily: "'Outfit', sans-serif", fontSize: '10px', fontWeight: 700, color: '#06b6d4', letterSpacing: '0.5px' }}>
                      AGENT DECISION ({confidenceScore}% confidence)
                    </span>
                  </div>
                  <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '12px', color: '#e2e8f0', margin: 0, lineHeight: '1.5' }}>
                    {incident.reroute_plan || 'Divert via Allahabad loop line. Platform 4→1 at CNB. Est. recovery: 18 minutes.'}
                  </p>
                </div>

                {/* Prediction */}
                <div style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.05)',
                  border: '1px dashed rgba(239, 68, 68, 0.3)',
                  borderRadius: '4px',
                  padding: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px'
                }}>
                  <div style={{ fontFamily: "'Outfit', sans-serif", fontSize: '10px', fontWeight: 700, color: '#ef4444', letterSpacing: '0.5px' }}>
                    PREDICTION
                  </div>
                  <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '12px', color: '#e2e8f0', margin: 0, lineHeight: '1.5' }}>
                    {predictionText}
                  </p>
                </div>

                {/* Departments Notified */}
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  padding: '6px 8px',
                  backgroundColor: 'rgba(26, 36, 51, 0.2)',
                  border: '1px solid #1a2433'
                }}>
                  <span style={{ fontSize: '8px', color: '#5c7080', fontWeight: 700, letterSpacing: '0.5px' }}>
                    DEPARTMENTS NOTIFIED ✓✓✓
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '2px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '2px', fontSize: '9px', color: '#cbd5e1' }}>
                      <span>🔧</span> <span style={{ fontSize: '8px' }}>Maintenance</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '2px', fontSize: '9px', color: '#cbd5e1' }}>
                      <span>⚡</span> <span style={{ fontSize: '8px' }}>Operations</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '2px', fontSize: '9px', color: '#cbd5e1' }}>
                      <span>📢</span> <span style={{ fontSize: '8px' }}>Station Manager</span>
                    </div>
                  </div>
                </div>

                {/* Override input form inline if active */}
                {isOverriding && (
                  <div 
                    style={{
                      borderTop: '1px solid #1a2433',
                      paddingTop: '8px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px'
                    }}
                    onClick={e => e.stopPropagation()}
                  >
                    <input
                      type="text"
                      value={overrideText}
                      onChange={(e) => setOverrideText(e.target.value)}
                      placeholder="Type different decision..."
                      style={{
                        backgroundColor: '#05070a',
                        border: '1px solid #ffb300',
                        color: '#cbd5e1',
                        fontSize: '10px',
                        padding: '6px',
                        fontFamily: 'inherit',
                        outline: 'none',
                        borderRadius: '0px'
                      }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                      <button
                        onClick={() => {
                          setActiveOverrideId(null);
                          setOverrideText("");
                        }}
                        style={{
                          padding: '3px 8px',
                          backgroundColor: '#ff3366',
                          color: '#ffffff',
                          border: 'none',
                          fontSize: '8px',
                          fontWeight: 700,
                          cursor: 'pointer'
                        }}
                      >
                        CANCEL
                      </button>
                      <button
                        onClick={() => {
                          if (overrideText.trim()) {
                            onOverride && onOverride(incident.id, overrideText);
                            setActiveOverrideId(null);
                            setOverrideText("");
                          }
                        }}
                        style={{
                          padding: '3px 8px',
                          backgroundColor: '#00e676',
                          color: '#080a0d',
                          border: 'none',
                          fontSize: '8px',
                          fontWeight: 700,
                          cursor: 'pointer'
                        }}
                      >
                        SUBMIT
                      </button>
                    </div>
                  </div>
                )}

                {/* Footer Buttons: APPROVE / OVERRIDE / EXPAND */}
                <div style={{ display: 'flex', gap: '6px', borderTop: '1px solid #1a2433', paddingTop: '8px' }} onClick={e => e.stopPropagation()}>
                  {incident.approved ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#00e676', flex: 1, fontSize: '9px', fontWeight: 'bold' }}>
                      <CheckCircle2 size={10} /> DETOURS APPROVED
                    </div>
                  ) : (
                    <>
                      <button
                        onClick={() => onApprove && onApprove(incident.id)}
                        style={{
                          flex: 1,
                          padding: '4px 8px',
                          backgroundColor: '#00e676',
                          color: '#080a0d',
                          border: 'none',
                          fontSize: '9px',
                          fontWeight: '800',
                          cursor: 'pointer'
                        }}
                      >
                        APPROVE ✓
                      </button>
                      <button
                        onClick={() => {
                          setActiveOverrideId(incident.id);
                          setOverrideText(incident.reroute_plan || "");
                        }}
                        style={{
                          flex: 1,
                          padding: '4px 8px',
                          backgroundColor: '#ffb300',
                          color: '#080a0d',
                          border: 'none',
                          fontSize: '9px',
                          fontWeight: '800',
                          cursor: 'pointer'
                        }}
                      >
                        OVERRIDE
                      </button>
                    </>
                  )}
                  <button
                     onClick={() => toggleExpand(incident.id)}
                     style={{
                       padding: '4px 8px',
                       backgroundColor: '#1a2433',
                       color: '#cbd5e1',
                       border: 'none',
                       fontSize: '9px',
                       fontWeight: '800',
                       cursor: 'pointer'
                     }}
                   >
                     {isExpanded ? 'COLLAPSE' : 'EXPAND'}
                   </button>
                </div>

                {/* Expandable description section */}
                {isExpanded && (
                  <div style={{
                    backgroundColor: '#080a0d',
                    border: '1px solid #1a2433',
                    padding: '8px',
                    fontSize: '9px',
                    color: '#8a9ba8',
                    whiteSpace: 'pre-wrap',
                    marginTop: '4px'
                  }}>
                    {incident.situation_summary || incident.description}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Bottom Filter & Export Toggle */}
      <div style={{
        padding: '16px',
        borderTop: '1px solid #2b3240',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        backgroundColor: '#090b0e'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
          <span style={{ fontFamily: "'Outfit', sans-serif", fontSize: '11px', color: '#94a3b8', fontWeight: 600 }}>Filters</span>
          <svg style={{ width: '12px', height: '12px', color: '#94a3b8' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3}><path d="M19 9l-7 7-7-7" /></svg>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontFamily: "'Outfit', sans-serif", fontSize: '11px', color: '#64748b', fontWeight: 600 }}>Log export</span>
          <label style={{ position: 'relative', display: 'inline-block', width: '32px', height: '18px' }}>
            <input 
              type="checkbox" 
              checked={logExport}
              onChange={(e) => setLogExport(e.target.checked)}
              style={{ opacity: 0, width: 0, height: 0 }} 
            />
            <span style={{
              position: 'absolute', cursor: 'pointer', top: 0, left: 0, right: 0, bottom: 0,
              backgroundColor: logExport ? '#10b981' : '#1e293b', transition: '.2s', borderRadius: '10px'
            }}>
              <span style={{
                position: 'absolute', content: '""', height: '12px', width: '12px', left: logExport ? '16px' : '3px', bottom: '3px',
                backgroundColor: logExport ? '#090b0e' : '#94a3b8', transition: '.2s', borderRadius: '50%'
              }} />
            </span>
          </label>
        </div>
      </div>

    </div>
  );
}

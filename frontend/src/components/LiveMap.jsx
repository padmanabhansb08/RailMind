/* eslint-disable */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup, ZoomControl, Polyline, CircleMarker, useMap } from 'react-leaflet';
import L from 'leaflet';

// ─── CSS Animations injected once ────────────────────────────────────────────
const ANIMATION_CSS = `
  @keyframes shockwaveExpand {
    0%   { transform: scale(0.1); opacity: 0.9; }
    100% { transform: scale(4.5); opacity: 0; }
  }
  @keyframes dashFlow {
    from { stroke-dashoffset: 24; }
    to   { stroke-dashoffset: 0; }
  }
  @keyframes toastSlideIn {
    from { opacity: 0; transform: translateX(60px); }
    to   { opacity: 1; transform: translateX(0); }
  }
  @keyframes toastFadeOut {
    from { opacity: 1; }
    to   { opacity: 0; }
  }
  /* Smooth marker glide — Leaflet sets position via CSS transform; this animates it */
  .train-position-marker {
    transition: transform 4.8s linear !important;
  }
  .shockwave-ring {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: 3px solid #ff3366;
    background: transparent;
    position: absolute;
    left: -16px;
    top: -16px;
    pointer-events: none;
    animation: shockwaveExpand 1.8s ease-out forwards;
  }
  .shockwave-ring.warning {
    border-color: #ffb300;
  }
  .leaflet-popup-content-wrapper {
    background: #121820 !important;
    border: 1px solid #1a2433 !important;
    border-radius: 0 !important;
    box-shadow: 0 0 20px rgba(0,240,255,0.15) !important;
    padding: 0 !important;
  }
  .leaflet-popup-tip { background: #121820 !important; }
  .leaflet-popup-content { margin: 0 !important; }
`;

// ─── Station coordinate lookup ────────────────────────────────────────────────
const STATION_COORDS = {
  "NDLS": { lat: 28.6419, lng: 77.2194, name: "New Delhi" },
  "DLI":  { lat: 28.6562, lng: 77.2410, name: "Delhi Junction" },
  "CNB":  { lat: 26.4499, lng: 80.3319, name: "Kanpur Central" },
  "LKO":  { lat: 26.8467, lng: 80.9462, name: "Lucknow" },
  "ALD":  { lat: 25.4358, lng: 81.8463, name: "Prayagraj" },
  "BSB":  { lat: 25.3176, lng: 82.9739, name: "Varanasi" },
  "GKP":  { lat: 26.7606, lng: 83.3732, name: "Gorakhpur" },
  "AGC":  { lat: 27.1767, lng: 78.0081, name: "Agra Cantt" },
  "MTJ":  { lat: 27.4924, lng: 77.6737, name: "Mathura" },
  "ALJN": { lat: 27.8974, lng: 78.0880, name: "Aligarh" },
  "MB":   { lat: 28.9845, lng: 77.7064, name: "Moradabad" },
  "SRE":  { lat: 29.9691, lng: 77.5469, name: "Saharanpur" },
  "AMB":  { lat: 30.3782, lng: 76.7767, name: "Ambala" },
  "ASR":  { lat: 31.6340, lng: 74.8723, name: "Amritsar" },
  "LDH":  { lat: 30.9010, lng: 75.8573, name: "Ludhiana" },
  "UMB":  { lat: 30.9167, lng: 76.9500, name: "Ambala Cantt" },
  "HW":   { lat: 29.9457, lng: 78.1642, name: "Haridwar" },
  "DDN":  { lat: 30.3165, lng: 78.0322, name: "Dehradun" },
  "PNBE": { lat: 25.6093, lng: 85.1235, name: "Patna" },
  "RJPB": { lat: 25.6093, lng: 85.1390, name: "Rajendra Nagar" },
  "BGP":  { lat: 25.2425, lng: 86.9842, name: "Bhagalpur" },
  "MFP":  { lat: 26.1197, lng: 85.3910, name: "Muzaffarpur" },
  "DBG":  { lat: 26.1522, lng: 85.8970, name: "Darbhanga" },
  "SPJ":  { lat: 25.8645, lng: 85.7810, name: "Samastipur" },
  "DHN":  { lat: 23.7957, lng: 86.4304, name: "Dhanbad" },
  "JSME": { lat: 24.1540, lng: 86.2028, name: "Jasidih" },
  "RNC":  { lat: 23.3441, lng: 85.3096, name: "Ranchi" },
  "HWH":  { lat: 22.5958, lng: 88.2636, name: "Howrah" },
  "SDAH": { lat: 22.5697, lng: 88.3697, name: "Sealdah" },
  "KOAA": { lat: 22.5726, lng: 88.3639, name: "Kolkata" },
  "BDC":  { lat: 22.8456, lng: 88.3632, name: "Bandel" },
  "BWN":  { lat: 23.2324, lng: 87.8615, name: "Bardhaman" },
  "KGP":  { lat: 22.3460, lng: 87.3195, name: "Kharagpur" },
  "CSTM": { lat: 18.9398, lng: 72.8355, name: "Mumbai CST" },
  "BCT":  { lat: 18.9690, lng: 72.8205, name: "Mumbai Central" },
  "MMCT": { lat: 18.9690, lng: 72.8205, name: "Mumbai Central" },
  "LTT":  { lat: 19.0668, lng: 72.9244, name: "Lokmanya Tilak" },
  "PUNE": { lat: 18.5286, lng: 73.8742, name: "Pune" },
  "NGP":  { lat: 21.1458, lng: 79.0882, name: "Nagpur" },
  "AWB":  { lat: 19.8762, lng: 75.3433, name: "Aurangabad" },
  "NED":  { lat: 19.1566, lng: 77.3212, name: "Nanded" },
  "SUR":  { lat: 17.6868, lng: 75.9064, name: "Solapur" },
  "SBC":  { lat: 12.9784, lng: 77.5736, name: "Bangalore City" },
  "YPR":  { lat: 13.0148, lng: 77.5510, name: "Yesvantpur" },
  "UBL":  { lat: 15.3647, lng: 75.1240, name: "Hubli" },
  "MYS":  { lat: 12.2958, lng: 76.6394, name: "Mysuru" },
  "MAS":  { lat: 13.0827, lng: 80.2707, name: "Chennai Central" },
  "MS":   { lat: 13.0012, lng: 80.2565, name: "Chennai Egmore" },
  "TPJ":  { lat: 10.7905, lng: 78.7047, name: "Tiruchirappalli" },
  "MDU":  { lat:  9.9252, lng: 78.1198, name: "Madurai" },
  "CBE":  { lat: 11.0168, lng: 76.9558, name: "Coimbatore" },
  "NCJ":  { lat:  8.7139, lng: 77.7567, name: "Nagercoil" },
  "TVC":  { lat:  8.4855, lng: 76.9492, name: "Thiruvananthapuram" },
  "ERS":  { lat:  9.9816, lng: 76.2999, name: "Ernakulam" },
  "CLT":  { lat: 11.2588, lng: 75.7804, name: "Kozhikode" },
  "SRR":  { lat: 10.9598, lng: 75.9495, name: "Shoranur" },
  "SC":   { lat: 17.4339, lng: 78.5000, name: "Secunderabad" },
  "HYB":  { lat: 17.3850, lng: 78.4867, name: "Hyderabad" },
  "BZA":  { lat: 16.5193, lng: 80.6305, name: "Vijayawada" },
  "VSKP": { lat: 17.7231, lng: 83.2985, name: "Visakhapatnam" },
  "GNT":  { lat: 16.3067, lng: 80.4365, name: "Guntur" },
  "ADI":  { lat: 23.0225, lng: 72.5714, name: "Ahmedabad" },
  "BRC":  { lat: 22.3144, lng: 73.1932, name: "Vadodara" },
  "ST":   { lat: 21.1702, lng: 72.8311, name: "Surat" },
  "RJT":  { lat: 22.3039, lng: 70.8022, name: "Rajkot" },
  "BPL":  { lat: 23.2599, lng: 77.4126, name: "Bhopal" },
  "JBP":  { lat: 23.1815, lng: 79.9864, name: "Jabalpur" },
  "GWL":  { lat: 26.2183, lng: 78.1828, name: "Gwalior" },
  "INDB": { lat: 22.7196, lng: 75.8577, name: "Indore" },
  "ET":   { lat: 23.6611, lng: 77.7631, name: "Itarsi" },
  "JP":   { lat: 26.9124, lng: 75.7873, name: "Jaipur" },
  "AII":  { lat: 26.4499, lng: 74.6399, name: "Ajmer" },
  "JU":   { lat: 26.2389, lng: 73.0243, name: "Jodhpur" },
  "BBS":  { lat: 20.2961, lng: 85.8189, name: "Bhubaneswar" },
  "PURI": { lat: 19.8135, lng: 85.8312, name: "Puri" },
  "GHY":  { lat: 26.1445, lng: 91.7362, name: "Guwahati" },
  "8011160": { lat: 52.5256, lng: 13.3690, name: "Berlin Hbf" },
  "8000261": { lat: 48.1402, lng: 11.5600, name: "Munich Hbf" },
};

const MAP_CENTER = [21.7679, 78.8718];

const getCoords = (key) => {
  if (!key) return null;
  const k = key.trim();
  if (STATION_COORDS[k]) return [STATION_COORDS[k].lat, STATION_COORDS[k].lng];
  for (const code in STATION_COORDS) {
    if (STATION_COORDS[code].name.toLowerCase() === k.toLowerCase())
      return [STATION_COORDS[code].lat, STATION_COORDS[code].lng];
  }
  return null;
};

const getDetourCoords = (planText) => {
  if (!planText) return null;
  let routeStr = planText;
  const match = planText.match(/Dijkstra routed:\s*(.*?)\s*\(ETA/);
  if (match) routeStr = match[1];
  else if (planText.includes('Dijkstra routed:'))
    routeStr = planText.replace('Dijkstra routed:', '');
  const stops = routeStr.split('->').map(s => s.trim());
  const coords = [];
  stops.forEach(s => { const c = getCoords(s); if (c) coords.push(c); });
  return coords.length >= 2 ? coords : null;
};

const createMarkerIcon = (status, delay, isSelected = false) => {
  let color = '#00f0ff';
  if (status === 'cancelled' || delay > 60) color = '#ff3366';
  else if (status === 'delayed' || delay > 15) color = '#ffb300';
  const size = isSelected ? 16 : 10;
  const glow = isSelected ? `0 0 14px ${color}, 0 0 28px ${color}40` : `0 0 8px ${color}80`;
  return L.divIcon({
    html: `<div style="
      width:${size}px; height:${size}px;
      background:${color};
      border: 2px solid #fff;
      border-radius: 50%;
      box-shadow: ${glow};
      transition: all 0.4s ease;
    "></div>`,
    className: 'train-position-marker',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
};

const createShockwaveIcon = (severity) => {
  const cls = severity === 'warning' ? 'shockwave-ring warning' : 'shockwave-ring';
  return L.divIcon({
    html: `<div class="${cls}"></div>`,
    className: '',
    iconSize: [0, 0],
    iconAnchor: [0, 0],
  });
};

// ─── Component: Animated Polyline (flowing dashes) ───────────────────────────
function AnimatedPolyline({ positions, color = '#00f0ff', weight = 3, isDashed = false }) {
  const map = useMap();
  const polylineRef = useRef(null);

  useEffect(() => {
    if (!polylineRef.current) return;
    const path = polylineRef.current._path;
    if (!path) return;
    if (isDashed) {
      path.style.strokeDasharray = '10, 6';
      path.style.strokeDashoffset = '0';
    } else {
      path.style.strokeDasharray = '16, 8';
      path.style.animation = 'dashFlow 0.9s linear infinite';
    }
  }, [positions, isDashed]);

  return (
    <Polyline
      ref={polylineRef}
      positions={positions}
      pathOptions={{ color, weight, opacity: isDashed ? 0.85 : 1 }}
    />
  );
}

// ─── Component: Toast Overlay ─────────────────────────────────────────────────
function ToastOverlay({ toasts }) {
  return (
    <div style={{
      position: 'absolute', bottom: '80px', right: '16px',
      zIndex: 9999, display: 'flex', flexDirection: 'column', gap: '8px',
      pointerEvents: 'none',
    }}>
      {toasts.map(t => (
        <div key={t.id} style={{
          backgroundColor: '#0d1117',
          border: `1px solid ${t.color}`,
          boxShadow: `0 0 12px ${t.color}40`,
          padding: '10px 14px',
          borderLeft: `4px solid ${t.color}`,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '11px',
          color: '#e2e8f0',
          minWidth: '260px',
          animation: t.fading
            ? 'toastFadeOut 0.5s ease forwards'
            : 'toastSlideIn 0.3s ease forwards',
        }}>
          <div style={{ color: t.color, fontWeight: 700, fontSize: '9px', marginBottom: '3px', letterSpacing: '0.5px' }}>
            {t.label}
          </div>
          {t.message}
        </div>
      ))}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function LiveMap({ trains = [], incidents = [] }) {
  const [selectedTrainNo, setSelectedTrainNo] = useState(null);
  const [toasts, setToasts] = useState([]);
  const [shockwaves, setShockwaves] = useState([]);
  const [trailDots, setTrailDots] = useState({});

  const prevStationsRef    = useRef({});
  const prevIncidentIdsRef = useRef(new Set());
  const cssInjectedRef     = useRef(false);

  // Inject animation CSS once
  useEffect(() => {
    if (cssInjectedRef.current) return;
    const tag = document.createElement('style');
    tag.innerHTML = ANIMATION_CSS;
    document.head.appendChild(tag);
    cssInjectedRef.current = true;
    return () => { try { document.head.removeChild(tag); } catch(_) {} };
  }, []);

  // ── Feature D: Station Arrival Toasts ────────────────────────────────────
  useEffect(() => {
    if (!trains.length) return;
    const addToast = (id, label, message, color) => {
      const toast = { id, label, message, color, fading: false };
      setToasts(prev => [...prev.slice(-4), toast]);
      setTimeout(() => {
        setToasts(prev => prev.map(t => t.id === id ? { ...t, fading: true } : t));
      }, 3500);
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id));
      }, 4000);
    };

    trains.forEach(train => {
      const prev = prevStationsRef.current[train.train_number];
      const curr = train.current_station || train.station_code;
      if (prev && prev !== curr && curr) {
        const color = train.delay_minutes > 15 ? '#ffb300' : '#00f0ff';
        const delayStr = train.delay_minutes > 0 ? ` — ${train.delay_minutes}m delay` : ' — On Time';
        addToast(
          `${train.train_number}-${Date.now()}`,
          `🚆 ARRIVED // ${train.train_number}`,
          `${train.train_name || 'Train'} → ${curr}${delayStr}`,
          color
        );
      }
      prevStationsRef.current[train.train_number] = curr;
    });
  }, [trains]);

  // ── Feature B: Anomaly Shockwaves ────────────────────────────────────────
  useEffect(() => {
    if (!incidents.length) return;
    const newWaves = [];
    incidents.forEach(inc => {
      if (prevIncidentIdsRef.current.has(inc.id)) return;
      prevIncidentIdsRef.current.add(inc.id);
      const train = trains.find(t => t.train_number === inc.train_number);
      if (train && train.lat != null && train.lng != null) {
        const waveId = `wave-${inc.id}-${Date.now()}`;
        newWaves.push({ id: waveId, lat: Number(train.lat), lng: Number(train.lng), severity: inc.severity });
      }
    });
    if (newWaves.length) {
      setShockwaves(prev => [...prev, ...newWaves]);
      newWaves.forEach(w => {
        setTimeout(() => {
          setShockwaves(prev => prev.filter(sw => sw.id !== w.id));
        }, 2200);
      });
    }
  }, [incidents, trains]);

  // ── Feature A: Comet Trail Dots ───────────────────────────────────────────
  useEffect(() => {
    if (!trains.length) return;
    setTrailDots(prev => {
      const next = { ...prev };
      trains.forEach(train => {
        if (train.lat == null || train.lng == null) return;
        const key = train.train_number;
        const existing = next[key] || [];
        const newDot = { lat: Number(train.lat), lng: Number(train.lng), ts: Date.now() };
        const last = existing[existing.length - 1];
        if (last && Math.abs(last.lat - newDot.lat) < 0.001 && Math.abs(last.lng - newDot.lng) < 0.001) return;
        next[key] = [...existing.slice(-5), newDot];
      });
      return next;
    });
  }, [trains]);

  const activeTrains = trains.length > 0 ? trains : [
    { train_number: "12301", train_name: "Howrah Rajdhani", current_station: "New Delhi", delay_minutes: 0, status: "On Time", lat: 28.6419, lng: 77.2194, speed: "120 km/h", next_station: "Kanpur Central", distance_next: "440 KM" },
  ];

  const selectedTrain = activeTrains.find(t => t.train_number === selectedTrainNo);
  const originalCoords = selectedTrain?.route_stops?.map(s => [s.lat, s.lng]) || [];

  const approvedIncident = selectedTrain && (incidents || []).find(
    inc => inc.train_number === selectedTrain.train_number && inc.approved && inc.reroute_plan
  );
  const detourCoords = approvedIncident ? getDetourCoords(approvedIncident.reroute_plan) : null;

  return (
    <div style={{ flex: 1, height: '100%', position: 'relative', backgroundColor: '#080a0d' }}>
      <ToastOverlay toasts={toasts} />
      <LiveClockBadge />

      <MapContainer center={MAP_CENTER} zoom={5} zoomControl={false} style={{ width: '100%', height: '100%' }}>
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        />
        <ZoomControl position="bottomright" />

        {/* Feature A: Comet Trail Dots */}
        {Object.entries(trailDots).map(([trainNo, dots]) => {
          const train = activeTrains.find(t => t.train_number === trainNo);
          const color = train?.delay_minutes > 60 ? '#ff3366' : train?.delay_minutes > 15 ? '#ffb300' : '#00f0ff';
          return dots.slice(0, -1).map((dot, i) => {
            const opacity = (i + 1) / dots.length * 0.45;
            const radius  = 2 + i * 0.6;
            return (
              <CircleMarker
                key={`trail-${trainNo}-${i}`}
                center={[dot.lat, dot.lng]}
                radius={radius}
                pathOptions={{ color, fillColor: color, fillOpacity: opacity, opacity: 0, weight: 0 }}
              />
            );
          });
        })}

        {/* Feature B: Shockwave Rings */}
        {shockwaves.map(wave => (
          <Marker key={wave.id} position={[wave.lat, wave.lng]} icon={createShockwaveIcon(wave.severity)} zIndexOffset={-100} />
        ))}

        {/* Feature C: Animated Route Polylines */}
        {selectedTrain && (
          <>
            {detourCoords ? (
              <>
                {originalCoords.length > 1 && (
                  <Polyline positions={originalCoords} pathOptions={{ color: '#2a3a4a', weight: 2, dashArray: '4, 6', opacity: 0.5 }} />
                )}
                <AnimatedPolyline positions={detourCoords} color="#ff3366" weight={4} isDashed={true} />
              </>
            ) : (
              originalCoords.length > 1 && (
                <AnimatedPolyline positions={originalCoords} color="#00f0ff" weight={3} />
              )
            )}
          </>
        )}

        {/* Train Markers */}
        {activeTrains.map((train, idx) => {
          let position;
          if (train.lat != null && train.lng != null) {
            position = [Number(train.lat), Number(train.lng)];
          } else {
            const code = train.station_code || train.current_station;
            position = getCoords(code) || [28.6143, 77.2147];
          }

          const isSelected = selectedTrainNo === train.train_number;
          const delay = train.delay_minutes || 0;
          const isCritical = delay > 60 || train.status?.toLowerCase() === 'cancelled';
          const isDelayed = delay > 15;
          const statusText = isCritical ? 'CRITICAL' : isDelayed ? 'DELAYED' : 'ON TIME';
          const statusColor = isCritical ? '#ff3366' : isDelayed ? '#ffb300' : '#00f0ff';
          const hasApprovedDetour = (incidents || []).some(
            inc => inc.train_number === train.train_number && inc.approved && inc.reroute_plan
          );

          return (
            <Marker
              key={train.train_number || idx}
              position={position}
              icon={createMarkerIcon(train.status?.toLowerCase(), delay, isSelected)}
              eventHandlers={{ click: () => setSelectedTrainNo(prev => prev === train.train_number ? null : train.train_number) }}
              zIndexOffset={isSelected ? 1000 : 0}
            >
              <Popup closeButton={false} minWidth={250}>
                <div style={{
                  padding: '14px 16px',
                  backgroundColor: '#121820',
                  color: '#e2e8f0',
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <span style={{
                      fontSize: '9px', fontWeight: 700,
                      backgroundColor: `${statusColor}18`,
                      color: statusColor,
                      padding: '2px 8px',
                      border: `1px solid ${statusColor}`,
                      letterSpacing: '0.5px'
                    }}>{statusText}</span>
                    <span style={{ fontSize: '10px', color: '#5c7080' }}>#{train.train_number}</span>
                  </div>

                  <h3 style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '4px' }}>
                    {train.train_name || 'Express Train'}
                  </h3>

                  <div style={{ display: 'flex', gap: '12px', fontSize: '10px', color: '#8a9ba8', marginBottom: '10px' }}>
                    <span>⚡ {train.speed || '80 km/h'}</span>
                    <span>📍 {train.current_station || '—'}</span>
                  </div>

                  {hasApprovedDetour && (
                    <div style={{
                      marginBottom: '10px', padding: '6px 8px',
                      backgroundColor: 'rgba(255,51,102,0.1)',
                      border: '1px solid #ff3366',
                      fontSize: '10px', color: '#ff3366'
                    }}>
                      <strong>DETOUR ACTIVE</strong> — Bypassing affected track segment
                    </div>
                  )}

                  <div style={{ height: '1px', backgroundColor: '#1a2433', margin: '8px 0' }} />

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px' }}>
                    <span style={{ color: '#5c7080' }}>
                      NEXT: <strong style={{ color: '#e2e8f0' }}>{train.next_station || '—'}</strong>
                    </span>
                    <span style={{ color: '#00f0ff' }}>{train.distance_next || '—'}</span>
                  </div>

                  <div style={{ marginTop: '8px', fontSize: '9px', color: '#3a4a5a', textAlign: 'center' }}>
                    {isSelected ? 'CLICK MARKER TO DESELECT ROUTE' : 'CLICK MARKER TO SHOW ROUTE'}
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}

// ─── Live IST Clock Badge ─────────────────────────────────────────────────────
function LiveClockBadge() {
  const [time, setTime] = useState('');
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      const ist = new Date(now.getTime() + (5.5 * 3600000));
      setTime(ist.toUTCString().slice(17, 25) + ' IST');
    };
    tick();
    const iv = setInterval(tick, 1000);
    return () => clearInterval(iv);
  }, []);

  return (
    <div style={{
      position: 'absolute', top: '12px', right: '12px',
      zIndex: 1000,
      backgroundColor: 'rgba(8,10,13,0.85)',
      border: '1px solid #1a2433',
      padding: '6px 12px',
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: '11px',
      color: '#00f0ff',
      letterSpacing: '0.5px',
      backdropFilter: 'blur(6px)',
    }}>
      🕐 {time}
    </div>
  );
}

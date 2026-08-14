/* eslint-disable */
import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Folder, Train, Activity, ShieldAlert, Award, Compass } from 'lucide-react';

export default function RouteIntelligence({ trains = [] }) {
  // Route Tree States
  const [expandedSectors, setExpandedSectors] = useState(new Set(['Sector 4']));
  const [selectedTrain, setSelectedTrain] = useState('Train 402');

  const toggleSector = (sector) => {
    const next = new Set(expandedSectors);
    if (next.has(sector)) {
      next.delete(sector);
    } else {
      next.add(sector);
    }
    setExpandedSectors(next);
  };

  // Dummy / Mock active route data matching Image 2
  const activeRoute = {
    train: selectedTrain,
    sector: 'Sector 4',
    speed: selectedTrain === 'Train 402' ? '112 km/h' : selectedTrain === 'Train 403' ? '98 km/h' : '82 km/h',
    fuel: selectedTrain === 'Train 402' ? '94.2%' : '88.5%',
    delayProb: selectedTrain === 'Train 402' ? 14 : 35,
    confidence: selectedTrain === 'Train 402' ? 88 : 74,
  };

  return (
    <div style={{ display: 'flex', flex: 1, height: '100%', overflow: 'hidden' }}>
      
      {/* Route Tree Navigation (Left Column) */}
      <div style={{
        width: '240px',
        backgroundColor: '#090b0e',
        borderRight: '1px solid #2b3240',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        padding: '16px 0',
        flexShrink: 0
      }}>
        <div style={{ padding: '0 16px 12px 16px', borderBottom: '1px solid #2b3240' }}>
          <span style={{ fontFamily: "'Outfit', sans-serif", fontSize: '13px', fontWeight: 600, color: '#e2e8f0', letterSpacing: '0.5px' }}>Route Tree</span>
        </div>
        
        <div style={{ padding: '16px 8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {/* Network Root Folder */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 8px', cursor: 'pointer', color: '#e2e8f0' }}>
              <ChevronDown size={14} style={{ color: '#64748b' }} />
              <Folder size={14} style={{ color: '#06b6d4' }} />
              <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px', fontWeight: 600 }}>Rail Network</span>
            </div>
            
            {/* Sector Folders */}
            <div style={{ paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '4px' }}>
              {/* Sector 4 */}
              <div>
                <div 
                  onClick={() => toggleSector('Sector 4')}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 8px', cursor: 'pointer', color: '#94a3b8' }}
                >
                  {expandedSectors.has('Sector 4') ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  <Folder size={12} style={{ color: '#f59e0b' }} />
                  <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px' }}>Sector 4</span>
                </div>
                
                {expandedSectors.has('Sector 4') && (
                  <div style={{ paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '2px' }}>
                    {['Train 402'].map(tr => (
                      <div 
                        key={tr}
                        onClick={() => setSelectedTrain(tr)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', cursor: 'pointer',
                          backgroundColor: selectedTrain === tr ? 'rgba(6, 182, 212, 0.08)' : 'transparent',
                          color: selectedTrain === tr ? '#06b6d4' : '#94a3b8',
                          borderLeft: selectedTrain === tr ? '2px solid #06b6d4' : '2px solid transparent',
                          borderRadius: '4px'
                        }}
                      >
                        <Train size={12} />
                        <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px' }}>{tr}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Sector 5 */}
              <div>
                <div 
                  onClick={() => toggleSector('Sector 5')}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 8px', cursor: 'pointer', color: '#94a3b8' }}
                >
                  {expandedSectors.has('Sector 5') ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  <Folder size={12} style={{ color: '#f59e0b' }} />
                  <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px' }}>Sector 5</span>
                </div>
                
                {expandedSectors.has('Sector 5') && (
                  <div style={{ paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '2px' }}>
                    {['Train 403', 'Train 404'].map(tr => (
                      <div 
                        key={tr}
                        onClick={() => setSelectedTrain(tr)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', cursor: 'pointer',
                          backgroundColor: selectedTrain === tr ? 'rgba(6, 182, 212, 0.08)' : 'transparent',
                          color: selectedTrain === tr ? '#06b6d4' : '#94a3b8',
                          borderLeft: selectedTrain === tr ? '2px solid #06b6d4' : '2px solid transparent',
                          borderRadius: '4px'
                        }}
                      >
                        <Train size={12} />
                        <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px' }}>{tr}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

            </div>
          </div>
        </div>
      </div>

      {/* Center Console Workspace */}
      <div style={{
        flex: 1,
        backgroundColor: '#05070a',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden'
      }}>
        
        {/* Breadcrumb Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid #2b3240',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#090b0e'
        }}>
          <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px', color: '#94a3b8' }}>
            Rail Network &gt; {activeRoute.sector} &gt; <span style={{ color: '#06b6d4', fontWeight: 600 }}>{activeRoute.train}</span>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              fontFamily: "'Outfit', sans-serif",
              fontSize: '11px',
              backgroundColor: '#11141a',
              border: '1px solid #2b3240',
              color: '#94a3b8',
              padding: '6px 12px',
              borderRadius: '6px'
            }}>
              ⚙ Last 24h
            </span>
          </div>
        </div>

        {/* Metrics Grid (Row) */}
        <div style={{ padding: '24px 24px 12px 24px' }}>
          <div style={{ fontFamily: "'Outfit', sans-serif", fontSize: '12px', color: '#e2e8f0', fontWeight: 600, marginBottom: '16px', letterSpacing: '0.5px' }}>Metrics Grid</div>
          <div style={{ display: 'flex', gap: '16px' }}>
            
            {/* Speed Metric */}
            <div style={{
              flex: 1,
              backgroundColor: '#11141a',
              border: '1px solid #2b3240',
              padding: '20px',
              position: 'relative',
              borderRadius: '8px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#64748b' }}>
                <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 600 }}>Train Speed</span>
                <span>•••</span>
              </div>
              <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '24px', fontWeight: 700, color: '#f8fafc', margin: '12px 0 2px 0' }}>{activeRoute.speed}</div>
              <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '11px', color: '#64748b' }}>Real-time</span>
              {/* Sparkline SVG */}
              <div style={{ marginTop: '14px', height: '32px' }}>
                <svg width="100%" height="100%" viewBox="0 0 100 30" preserveAspectRatio="none">
                  <path d="M0 25 Q15 5, 30 18 T60 8 T90 20 L100 15" fill="none" stroke="#06b6d4" strokeWidth={2} />
                </svg>
              </div>
            </div>

            {/* Fuel Efficiency */}
            <div style={{
              flex: 1,
              backgroundColor: '#11141a',
              border: '1px solid #2b3240',
              padding: '20px',
              position: 'relative',
              borderRadius: '8px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#64748b' }}>
                <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 600 }}>Fuel Efficiency</span>
                <span>•••</span>
              </div>
              <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '24px', fontWeight: 700, color: '#f8fafc', margin: '12px 0 2px 0' }}>
                {activeRoute.fuel} <span style={{ color: '#10b981', fontSize: '16px' }}>↗</span>
              </div>
              <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '11px', color: '#64748b' }}>Target: 92%</span>
              {/* Green Sparkline SVG */}
              <div style={{ marginTop: '14px', height: '32px' }}>
                <svg width="100%" height="100%" viewBox="0 0 100 30" preserveAspectRatio="none">
                  <path d="M0 28 Q20 20, 40 25 T80 15 T100 8" fill="none" stroke="#10b981" strokeWidth={2} />
                </svg>
              </div>
            </div>

            {/* Delay Probability */}
            <div style={{
              flex: 1,
              backgroundColor: '#11141a',
              border: '1px solid #2b3240',
              padding: '20px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderRadius: '8px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
            }}>
              <div style={{ display: 'flex', flexDirection: 'column', justifySelf: 'flex-start' }}>
                <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '11px', color: '#64748b', fontWeight: 600 }}>Delay Probability</span>
                <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '22px', fontWeight: 700, color: '#f8fafc', marginTop: '12px' }}>{activeRoute.delayProb}% Low</span>
                <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '11px', color: '#64748b', marginTop: '6px' }}>Confidence: {activeRoute.confidence}%</span>
              </div>
              {/* Circular Progress Ring */}
              <div style={{ width: '56px', height: '56px', position: 'relative' }}>
                <svg width="100%" height="100%" viewBox="0 0 36 36">
                  <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#2b3240" strokeWidth={3} />
                  <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#10b981" strokeWidth={3} strokeDasharray={`${activeRoute.delayProb}, 100`} />
                </svg>
              </div>
            </div>

          </div>
        </div>

        {/* Route Timeline / Gantt Log Layout */}
        <div style={{ padding: '0 24px 24px 24px', flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ fontFamily: "'Outfit', sans-serif", fontSize: '12px', color: '#e2e8f0', fontWeight: 600, marginBottom: '16px', letterSpacing: '0.5px' }}>Route Timeline/Log</div>
          
          <div style={{
            flex: 1,
            backgroundColor: '#11141a',
            border: '1px solid #2b3240',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            borderRadius: '8px'
          }}>
            {/* Timeline Hour Axis Header */}
            <div style={{
              display: 'flex',
              padding: '16px',
              borderBottom: '1px solid #2b3240',
              backgroundColor: '#090b0e'
            }}>
              {['12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00'].map((hour, index) => (
                <div key={index} style={{ flex: 1, textAlign: 'center', fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '12px', color: '#64748b' }}>
                  {hour}
                </div>
              ))}
            </div>

            {/* Gantt Row Bars */}
            <div style={{ flex: 1, padding: '24px 16px', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
              
              {/* Mumbai Block */}
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ width: '100px', flexShrink: 0 }}>
                  <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px', color: '#e2e8f0' }}>Mumbai</span>
                </div>
                <div style={{ flex: 1, position: 'relative', height: '40px' }}>
                  <div style={{
                    position: 'absolute', left: '0%', width: '35%', height: '100%',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)', borderLeft: '4px solid #ef4444',
                    padding: '8px 12px', display: 'flex', flexDirection: 'column', justifyContent: 'center',
                    borderRadius: '0 4px 4px 0'
                  }}>
                    <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '12px', color: '#ef4444', fontWeight: 700 }}>Delayed</span>
                  </div>
                </div>
              </div>

              {/* Surat Block */}
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ width: '100px', flexShrink: 0 }}>
                  <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px', color: '#e2e8f0' }}>Surat</span>
                </div>
                <div style={{ flex: 1, position: 'relative', height: '40px' }}>
                  <div style={{
                    position: 'absolute', left: '35%', width: '30%', height: '100%',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)', borderLeft: '4px solid #10b981',
                    padding: '8px 12px', display: 'flex', flexDirection: 'column', justifyContent: 'center',
                    borderRadius: '0 4px 4px 0'
                  }}>
                    <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '12px', color: '#10b981', fontWeight: 700 }}>On Time</span>
                  </div>
                </div>
              </div>

              {/* Nagpur Block */}
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ width: '100px', flexShrink: 0 }}>
                  <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px', color: '#e2e8f0' }}>Nagpur</span>
                </div>
                <div style={{ flex: 1, position: 'relative', height: '40px' }}>
                  <div style={{
                    position: 'absolute', left: '65%', width: '25%', height: '100%',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)', borderLeft: '4px solid #f59e0b',
                    padding: '8px 12px', display: 'flex', flexDirection: 'column', justifyContent: 'center',
                    borderRadius: '0 4px 4px 0'
                  }}>
                    <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '12px', color: '#f59e0b', fontWeight: 700 }}>Signal Warning</span>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </div>

      </div>

      {/* AI Insights & Recommendation Panel (Right Column) */}
      <div style={{
        width: '320px',
        backgroundColor: '#090b0e',
        borderLeft: '1px solid #2b3240',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        flexShrink: 0
      }}>
        {/* Header */}
        <div style={{
          padding: '24px 20px',
          borderBottom: '1px solid #2b3240',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <h2 style={{ fontFamily: "'Outfit', sans-serif", fontSize: '14px', fontWeight: 600, color: '#e2e8f0', letterSpacing: '0.5px', margin: '0 0 4px 0' }}>AI Insights</h2>
            <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '11px', color: '#64748b' }}>Natural language summaries</span>
          </div>
          <button style={{ backgroundColor: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer' }}>
            <span style={{ fontSize: '14px', fontWeight: 700 }}>•••</span>
          </button>
        </div>

        {/* Content Details */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Performance Summary */}
          <div style={{
            backgroundColor: '#11141a',
            border: '1px solid #2b3240',
            padding: '20px',
            borderRadius: '8px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
          }}>
            <h4 style={{ fontFamily: "'Outfit', sans-serif", fontSize: '13px', color: '#06b6d4', margin: '0 0 12px 0', fontWeight: 700 }}>
              ⎎ Performance Summary
            </h4>
            <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px', color: '#cbd5e1', lineHeight: '1.6', margin: 0 }}>
              Route running within acceptable parameters despite minor delays at Mumbai and Nagpur. Fuel efficiency is slightly above target.
            </p>
          </div>

          {/* Suggested Optimizations */}
          <div style={{
            backgroundColor: '#11141a',
            border: '1px solid #2b3240',
            padding: '20px',
            borderRadius: '8px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
          }}>
            <h4 style={{ fontFamily: "'Outfit', sans-serif", fontSize: '13px', color: '#f59e0b', fontWeight: 700, margin: 0 }}>
              ↯ Suggested Optimizations
            </h4>
            <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px', color: '#cbd5e1', lineHeight: '1.6', margin: 0 }}>
              Reroute recommended due to signal maintenance at Nagpur. Suggesting alternate path via Wardha junction to avoid potential 15-minute delay.
            </p>
            <button style={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              color: '#06b6d4',
              padding: '10px 16px',
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
              alignSelf: 'flex-start',
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              borderRadius: '6px',
              transition: 'all 0.2s'
            }}>
              Review Path
            </button>
          </div>

          {/* Anomaly Detection Status block */}
          <div style={{
            backgroundColor: '#11141a',
            border: '1px solid #2b3240',
            padding: '20px',
            borderRadius: '8px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
          }}>
            <h4 style={{ fontFamily: "'Outfit', sans-serif", fontSize: '13px', color: '#64748b', margin: '0 0 12px 0', fontWeight: 700 }}>
              🛡 Anomaly Detection
            </h4>
            <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px', color: '#94a3b8', margin: 0 }}>
              No current critical anomalies detected.
            </p>
          </div>

        </div>
      </div>

    </div>
  );
}

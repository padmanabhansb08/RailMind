/* eslint-disable */
import React, { useState, useEffect } from 'react';
import { Bell, Settings } from 'lucide-react';

export default function TopBar({ loopCount = 0, incidentCount = 0, wsStatus = 'connected', onNotificationsClick, onSettingsClick, onProfileClick, activeTab = 'Dashboard', onTabChange, liveFlash = false, cycleCountdown = 30 }) {
  const tabs = ['Rail Network', 'Sensor Data', 'Timetable', 'Fleet'];
  // Keep tab mapping aligned with App.jsx
  const activeTopTab = ['Sensor Data', 'Timetable', 'Fleet'].includes(activeTab) ? activeTab : 'Rail Network';
  const isConnected = wsStatus === 'connected';

  return (
    <div style={{
      height: '64px',
      backgroundColor: '#11141a',
      borderBottom: '1px solid #2b3240',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      flexShrink: 0
    }}>
      {/* Left section: Logo & Nav tabs */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="palantir-mono" style={{
            fontSize: '18px',
            fontWeight: 800,
            color: '#ffffff', 
            letterSpacing: '1px'
          }}>RAILMIND <span style={{ color: '#94a3b8', fontWeight: 500 }}>// COMMAND CENTER</span></span>
        </div>
        
        {/* Nav tabs */}
        <div style={{ display: 'flex', gap: '24px' }}>
          {tabs.map((tab) => {
            const isActive = tab === activeTopTab;
            return (
              <button
                key={tab}
                onClick={() => onTabChange && onTabChange(tab)}
                style={{
                  backgroundColor: 'transparent',
                  border: 'none',
                  borderBottom: isActive ? '2px solid #ffffff' : '2px solid transparent',
                  color: isActive ? '#ffffff' : '#cbd5e1',
                  cursor: 'pointer',
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '13px',
                  fontWeight: isActive ? 700 : 500,
                  height: '64px',
                  padding: '0 4px',
                  textTransform: 'uppercase',
                  transition: 'all 0.2s ease'
                }}
              >
                {tab}
              </button>
            );
          })}
        </div>
      </div>

      {/* Right section: System state indicators & settings */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        
        {/* Search Bar */}
        <div style={{ display: 'flex', alignItems: 'center', position: 'relative' }}>
          <input 
            type="text" 
            placeholder="Search or Enter Command" 
            className="palantir-mono"
            style={{
              backgroundColor: '#090b0e',
              border: '1px solid #2b3240',
              borderRadius: '4px',
              color: '#ffffff',
              padding: '6px 12px 6px 28px',
              fontSize: '11px',
              width: '180px',
              outline: 'none',
              transition: 'border-color 0.2s'
            }}
            onFocus={(e) => e.target.style.borderColor = '#ffffff'}
            onBlur={(e) => e.target.style.borderColor = '#2b3240'}
          />
          <svg 
            style={{ position: 'absolute', left: '8px', width: '12px', height: '12px', color: '#94a3b8' }} 
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        {/* Live and Counts indicators box */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          backgroundColor: '#090b0e',
          border: '1px solid #2b3240',
          borderRadius: '4px',
          padding: '6px 14px',
          gap: '16px'
        }}>
          {/* LIVE/OFFLINE status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span 
              className={`${isConnected ? "pulse-dot-cyan" : ""} ${liveFlash ? "flash-active-trigger" : ""}`} 
              style={{
                display: 'inline-block',
                width: '6px',
                height: '6px',
                backgroundColor: isConnected ? '#10b981' : '#ef4444',
                borderRadius: '50%'
              }}
            ></span>
            <span className="palantir-mono" style={{ 
              fontSize: '11px', 
              fontWeight: 600, 
              color: isConnected ? '#10b981' : '#ef4444', 
              letterSpacing: '0.5px' 
            }}>
              {isConnected ? 'System Online' : 'System Offline'}
            </span>
          </div>
          
          <div style={{ width: '1px', height: '14px', backgroundColor: '#2b3240' }}></div>

          {/* LOOP COUNT */}
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
            <span className="palantir-mono" style={{ fontSize: '10px', fontWeight: 600, color: '#94a3b8', letterSpacing: '0.5px' }}>Cycles:</span>
            <span className="palantir-mono" style={{ fontSize: '13px', fontWeight: 700, color: '#ffffff' }}>[{loopCount < 10 ? '0' + loopCount : loopCount}]</span>
          </div>

          <div style={{ width: '1px', height: '14px', backgroundColor: '#2b3240' }}></div>

          {/* INCIDENTS count */}
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
            <span className="palantir-mono" style={{ fontSize: '10px', fontWeight: 600, color: '#94a3b8', letterSpacing: '0.5px' }}>Alerts:</span>
            <span className="palantir-mono" style={{ fontSize: '13px', fontWeight: 700, color: '#ef4444' }}>[{incidentCount < 10 ? '0' + incidentCount : incidentCount}]</span>
          </div>

          <div style={{ width: '1px', height: '14px', backgroundColor: '#2b3240' }}></div>

          {/* Next agent cycle countdown */}
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
            <span className="palantir-mono" style={{ fontSize: '10px', fontWeight: 600, color: '#94a3b8', letterSpacing: '0.5px' }}>NEXT CYCLE:</span>
            <span className="palantir-mono" style={{ 
              fontSize: '13px', 
              fontWeight: 700, 
              color: cycleCountdown <= 5 ? '#ef4444' : '#f59e0b',
              transition: 'color 0.3s'
            }}>{cycleCountdown}s</span>
          </div>
        </div>

        {/* Bell notification */}
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <button 
            onClick={onNotificationsClick}
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              color: '#cbd5e1',
              cursor: 'pointer',
              padding: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'color 0.2s'
            }} onMouseEnter={(e) => e.currentTarget.style.color = '#ffffff'} onMouseLeave={(e) => e.currentTarget.style.color = '#cbd5e1'}>
            <Bell size={18} />
          </button>
          {incidentCount > 0 && (
            <span style={{
              position: 'absolute',
              top: '4px',
              right: '4px',
              width: '6px',
              height: '6px',
              backgroundColor: '#ef4444',
              borderRadius: '50%'
            }} />
          )}
        </div>

        {/* Settings */}
        <button 
          onClick={onSettingsClick}
          style={{
            backgroundColor: 'transparent',
            border: 'none',
            color: '#cbd5e1',
            cursor: 'pointer',
            padding: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'color 0.2s'
          }} onMouseEnter={(e) => e.currentTarget.style.color = '#ffffff'} onMouseLeave={(e) => e.currentTarget.style.color = '#cbd5e1'}>
          <Settings size={18} />
        </button>

        {/* Profile Avatar */}
        <div 
          onClick={onProfileClick}
          style={{
            width: '28px',
            height: '28px',
            borderRadius: '4px',
            overflow: 'hidden',
            border: '1px solid #2b3240',
            cursor: 'pointer'
          }}>
          <img 
            src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&q=80" 
            alt="User profile" 
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        </div>

      </div>
    </div>
  );
}

/* eslint-disable */
import React, { useState, useEffect } from 'react';
import { Bell } from 'lucide-react';

export default function TopBar({ loopCount = 0, incidentCount = 0, wsStatus = 'connected', onNotificationsClick, activeTab = 'Dashboard', onTabChange, liveFlash = false, onSearch, searchError = null, onDismissSearchError }) {
  const tabs = ['Rail Network', 'Sensor Data', 'Timetable', 'Fleet'];
  const [searchValue, setSearchValue] = useState("");
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
      <div style={{ display: 'flex', alignItems: 'center', gap: '48px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            fontSize: '18px',
            fontWeight: 800,
            color: 'var(--text-primary)', 
            letterSpacing: '0.5px'
          }}>RailMind</span>
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
                  borderBottom: isActive ? '2px solid var(--text-primary)' : '2px solid transparent',
                  color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: '15px',
                  fontWeight: isActive ? 600 : 500,
                  height: '64px',
                  padding: '0 12px',
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
            placeholder="Search train..." 
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && onSearch) {
                onSearch(searchValue);
                setSearchValue('');
              } else if (searchError && onDismissSearchError) {
                onDismissSearchError();
              }
            }}
            style={{
              backgroundColor: 'var(--bg-main)',
              border: `1px solid ${searchError ? '#ef4444' : 'var(--border-color)'}`,
              borderRadius: '8px',
              color: 'var(--text-primary)',
              padding: '8px 12px 8px 32px',
              fontSize: '13px',
              width: '200px',
              outline: 'none',
              transition: 'border-color 0.2s, box-shadow 0.2s'
            }}
            onFocus={(e) => {
              e.target.style.borderColor = 'var(--accent-color)';
              e.target.style.boxShadow = '0 0 0 1px var(--accent-color)';
            }}
            onBlur={(e) => {
              e.target.style.borderColor = 'var(--border-color)';
              e.target.style.boxShadow = 'none';
            }}
          />
          <svg 
            style={{ position: 'absolute', left: '8px', width: '12px', height: '12px', color: '#94a3b8' }} 
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>

          {/* A search that finds nothing must say so — the alternative used to
              be a fabricated train, and before that, silence. */}
          {searchError && (
            <div style={{
              position: 'absolute',
              top: '40px',
              right: 0,
              minWidth: '240px',
              backgroundColor: '#1a1113',
              border: '1px solid #ef4444',
              borderRadius: '8px',
              padding: '10px 12px',
              fontSize: '11px',
              color: '#fca5a5',
              lineHeight: 1.5,
              zIndex: 2000,
              boxShadow: '0 8px 24px rgba(0,0,0,0.5)'
            }}>
              {searchError}
            </div>
          )}
        </div>

        {/* Live and Counts indicators box */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          backgroundColor: 'var(--bg-main)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '8px 16px',
          gap: '16px'
        }}>
          {/* LIVE/OFFLINE status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span 
              className={`${isConnected ? "pulse-dot-cyan" : ""} ${liveFlash ? "flash-active-trigger" : ""}`} 
              style={{
                display: 'inline-block',
                width: '8px',
                height: '8px',
                backgroundColor: isConnected ? 'var(--color-resolved)' : 'var(--color-critical)',
                borderRadius: '50%'
              }}
            ></span>
            <span style={{ 
              fontSize: '12px', 
              fontWeight: 600, 
              color: isConnected ? 'var(--color-resolved)' : 'var(--color-critical)'
            }}>
              {/* Names what it actually measures: the WebSocket link to the
                  backend. Overall subsystem health is the sidebar's badge, and
                  labelling both "System …" made them look contradictory. */}
              {isConnected ? 'Live feed connected' : 'Live feed lost'}
            </span>
          </div>
          
          <div style={{ width: '1px', height: '14px', backgroundColor: 'var(--border-color)' }}></div>

          {/* LOOP COUNT */}
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', padding: '0 4px' }}>
            <span style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-muted)' }}>Cycles</span>
            <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>{loopCount}</span>
          </div>

          <div style={{ width: '1px', height: '14px', backgroundColor: 'var(--border-color)' }}></div>

          {/* INCIDENTS count */}
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', padding: '0 4px' }}>
            <span style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-muted)' }}>Alerts</span>
            <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-critical)' }}>{incidentCount}</span>
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

      </div>
    </div>
  );
}

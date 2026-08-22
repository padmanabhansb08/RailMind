/* eslint-disable */
import React from 'react';
import { LayoutDashboard, Map, BellRing, ClipboardList, BarChart3, FileClock, Sliders } from 'lucide-react';
import { statusMeta, useSystemStatus, StatusDot } from '../systemStatus';

export default function Sidebar({ activeTab = 'Dashboard', setActiveTab }) {
  const { status, reachable } = useSystemStatus(15000);
  const overall = reachable ? (status?.overall || 'unknown') : 'unknown';
  const overallMeta = statusMeta(overall);
  const menuItems = [
    { id: 'Dashboard', name: 'Overview', icon: LayoutDashboard },
    { id: 'Live Map', name: 'Real-Time Map', icon: Map },
    { id: 'Incident Feed', name: 'Incident Alerts', icon: BellRing },
    { id: 'Task Board', name: 'Tasks', icon: ClipboardList },
    { id: 'Analytics', name: 'Reports', icon: BarChart3 },
    { id: 'Simulation', name: 'Simulation Portal', icon: Sliders }
  ];

  const bottomItems = [
    { id: 'Logs', name: 'System Events', icon: FileClock }
  ];

  return (
    <div style={{
      width: '240px',
      backgroundColor: 'var(--bg-panel)',
      borderRight: '1px solid var(--border-color)',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      height: '100%',
      padding: '24px 0 16px 0',
      flexShrink: 0
    }}>
      <div>
        {/* Header */}
        <div style={{ padding: '0 24px 24px 24px', borderBottom: '1px solid var(--border-color)' }}>
          <h2 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '0.5px' }}>Workspace</h2>
          <span
            title={reachable ? undefined : 'Cannot reach the RailMind API'}
            style={{ fontSize: '11px', color: overallMeta.color, fontWeight: 500, display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <StatusDot status={overall} />
            {overall === 'ok' ? 'All systems operational' : `System ${overallMeta.label.toLowerCase()}`}
          </span>
        </div>

        {/* Navigation */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '24px 12px 0 12px' }}>
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab && setActiveTab(item.id)}
                className=""
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '10px 16px',
                  backgroundColor: isActive ? 'var(--bg-card)' : 'transparent',
                  border: 'none',
                  borderRadius: '8px',
                  color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                  fontSize: '13px',
                  fontWeight: isActive ? 600 : 500,
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.2s ease',
                  width: '100%'
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)';
                    e.currentTarget.style.color = 'var(--text-primary)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = 'var(--text-secondary)';
                  }
                }}
              >
                <Icon size={16} style={{ color: isActive ? 'var(--text-primary)' : 'var(--text-muted)' }} />
                {item.name}
              </button>
            );
          })}
        </div>
      </div>

      {/* Footer Nav */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '0 12px' }}>
        {bottomItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab && setActiveTab(item.id)}
              className=""
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '10px 16px',
                backgroundColor: isActive ? 'var(--bg-card)' : 'transparent',
                border: 'none',
                borderRadius: '8px',
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontSize: '12px',
                fontWeight: isActive ? 600 : 500,
                letterSpacing: '0.2px',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.2s ease',
                width: '100%'
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)';
                  e.currentTarget.style.color = 'var(--text-primary)';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = 'var(--text-secondary)';
                }
              }}
            >
              <Icon size={16} style={{ color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)' }} />
              {item.name}
            </button>
          );
        })}
      </div>
    </div>
  );
}

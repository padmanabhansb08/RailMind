/* eslint-disable */
import React from 'react';
import { LayoutDashboard, Map, BellRing, ClipboardList, BarChart3, HelpCircle, FileClock, Sliders } from 'lucide-react';

export default function Sidebar({ activeTab = 'Dashboard', setActiveTab }) {
  const menuItems = [
    { id: 'Dashboard', name: 'Overview', icon: LayoutDashboard },
    { id: 'Live Map', name: 'Real-Time Map', icon: Map },
    { id: 'Incident Feed', name: 'Incident Alerts', icon: BellRing },
    { id: 'Task Board', name: 'Tasks', icon: ClipboardList },
    { id: 'Analytics', name: 'Reports', icon: BarChart3 },
    { id: 'Simulation', name: 'Simulation Portal', icon: Sliders }
  ];

  const bottomItems = [
    { id: 'Support', name: 'Help & Support', icon: HelpCircle },
    { id: 'Logs', name: 'System Events', icon: FileClock }
  ];

  return (
    <div style={{
      width: '240px',
      backgroundColor: '#0d1117',
      borderRight: '1px solid #1a2433',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      height: '100%',
      padding: '24px 0 16px 0',
      flexShrink: 0
    }}>
      <div>
        {/* Header */}
        <div style={{ padding: '0 24px 24px 24px', borderBottom: '1px solid #1a2433' }}>
          <h2 className="palantir-mono" style={{ fontSize: '15px', fontWeight: 600, color: '#e2e8f0', letterSpacing: '1px' }}>SYS // ALPHA</h2>
          <span className="palantir-mono" style={{ fontSize: '10px', color: '#00f0ff', fontWeight: 500 }}>Monitoring: Active</span>
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
                className="palantir-mono"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '12px 16px',
                  backgroundColor: isActive ? '#121820' : 'transparent',
                  border: 'none',
                  borderLeft: isActive ? '3px solid #00f0ff' : '3px solid transparent',
                  borderRadius: '0px',
                  color: isActive ? '#00f0ff' : '#8a9ba8',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.2s ease',
                  width: '100%'
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = '#17202b';
                    e.currentTarget.style.color = '#e2e8f0';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = '#8a9ba8';
                  }
                }}
              >
                <Icon size={16} style={{ color: isActive ? '#00f0ff' : '#5c7080' }} />
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
              className="palantir-mono"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '10px 16px',
                backgroundColor: isActive ? '#121820' : 'transparent',
                border: 'none',
                borderLeft: isActive ? '3px solid #00f0ff' : '3px solid transparent',
                borderRadius: '0px',
                color: isActive ? '#00f0ff' : '#5c7080',
                fontSize: '10px',
                fontWeight: 600,
                letterSpacing: '0.5px',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.2s ease',
                width: '100%'
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = '#17202b';
                  e.currentTarget.style.color = '#e2e8f0';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = '#5c7080';
                }
              }}
            >
              <Icon size={14} style={{ color: '#5c7080' }} />
              {item.name}
            </button>
          );
        })}
      </div>
    </div>
  );
}

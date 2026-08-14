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
      backgroundColor: '#11141a',
      borderRight: '1px solid #2b3240',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      height: '100%',
      padding: '24px 0 16px 0',
      flexShrink: 0
    }}>
      <div>
        {/* Header */}
        <div style={{ padding: '0 24px 24px 24px', borderBottom: '1px solid #2b3240' }}>
          <h2 className="palantir-mono" style={{ fontSize: '15px', fontWeight: 700, color: '#ffffff', letterSpacing: '1px' }}>SYS // ALPHA</h2>
          <span className="palantir-mono" style={{ fontSize: '10px', color: '#10b981', fontWeight: 600 }}>Monitoring: Active</span>
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
                  backgroundColor: isActive ? '#181c24' : 'transparent',
                  border: 'none',
                  borderLeft: isActive ? '3px solid #ffffff' : '3px solid transparent',
                  borderRadius: '4px',
                  color: isActive ? '#ffffff' : '#cbd5e1',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.2s ease',
                  width: '100%'
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = '#212632';
                    e.currentTarget.style.color = '#ffffff';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = '#cbd5e1';
                  }
                }}
              >
                <Icon size={16} style={{ color: isActive ? '#ffffff' : '#94a3b8' }} />
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
                backgroundColor: isActive ? '#181c24' : 'transparent',
                border: 'none',
                borderLeft: isActive ? '3px solid #ffffff' : '3px solid transparent',
                borderRadius: '4px',
                color: isActive ? '#ffffff' : '#94a3b8',
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
                  e.currentTarget.style.backgroundColor = '#212632';
                  e.currentTarget.style.color = '#ffffff';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = '#94a3b8';
                }
              }}
            >
              <Icon size={14} style={{ color: '#94a3b8' }} />
              {item.name}
            </button>
          );
        })}
      </div>
    </div>
  );
}

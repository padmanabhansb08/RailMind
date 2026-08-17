/* eslint-disable */
import React from 'react';
import { MoreHorizontal, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function TaskBoard({ tasks = [], onResolve, fullScreen = false }) {
  // Setup default mock tasks if tasks list is empty
  const activeTasks = tasks.length > 0 ? tasks : [
    {
      id: "task_001",
      department: "maintenance",
      task_description: "Engine Check - Train 402",
      urgency: "urgent",
      action_required: "DUE: 15:00",
      detail: "Anomaly detected in propulsion system. Immediate action required."
    },
    {
      id: "task_002",
      department: "operations",
      task_description: "Signal Calibration - Route 7",
      urgency: "medium",
      action_required: "ASSIGNED: ALPHA-9",
      detail: "Routine calibration needed for optimal traffic flow. No immediate impact."
    },
    {
      id: "task_003",
      department: "station_manager",
      task_description: "Platform 4 Clearance",
      urgency: "resolved",
      action_required: "COMPLETED 10:55",
      detail: "Passenger crowd dissipated, platform cleared for next service."
    }
  ];

  // Group tasks by department
  const maintenanceTasks = activeTasks.filter(t => t.department?.toLowerCase() === 'maintenance');
  const operationsTasks = activeTasks.filter(t => t.department?.toLowerCase() === 'operations');
  const stationTasks = activeTasks.filter(t =>
    t.department?.toLowerCase() === 'station_manager' ||
    t.department?.toLowerCase() === 'station'
  );

  const getUrgencyBadge = (urgency) => {
    let color = '#ef4444'; // Red
    let bg = 'rgba(239, 68, 68, 0.1)';
    let text = 'Urgent';

    if (urgency.toLowerCase() === 'medium') {
      color = '#f59e0b'; // Amber
      bg = 'rgba(245, 158, 11, 0.1)';
      text = 'Medium';
    } else if (urgency.toLowerCase() === 'resolved') {
      color = '#10b981'; // Green
      bg = 'rgba(16, 185, 129, 0.1)';
      text = 'Resolved';
    } else if (urgency.toLowerCase() === 'low') {
      color = '#0ea5e9'; // Blue
      bg = 'rgba(14, 165, 233, 0.1)';
      text = 'Low';
    } else if (urgency.toLowerCase() === 'high') {
      color = '#f59e0b'; // Orange
      bg = 'rgba(245, 158, 11, 0.1)';
      text = 'High';
    } else if (urgency.toLowerCase() === 'critical') {
      color = '#ef4444'; // Dark Red
      bg = 'rgba(239, 68, 68, 0.1)';
      text = 'Critical';
    }

    return (
      <span style={{
        fontSize: '11px',
        fontWeight: 600,
        color: color,
        backgroundColor: bg,
        padding: '4px 10px',
        borderRadius: '6px',
        letterSpacing: '0.2px'
      }}>
        {text}
      </span>
    );
  };

  const renderColumn = (title, columnTasks) => {
    return (
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        padding: '24px 20px',
        borderRight: '1px solid var(--border-color)',
        backgroundColor: 'var(--bg-main)'
      }}>
        <h3 style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: '13px',
          fontWeight: 600,
          color: '#cbd5e1',
          letterSpacing: '1px',
          textTransform: 'uppercase',
          margin: 0
        }}>
          {title}
        </h3>
        
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          overflowY: 'auto',
          paddingRight: '4px'
        }}>
          {columnTasks.map((task) => {
            const isResolved = task.status?.toLowerCase() === 'resolved' || task.urgency?.toLowerCase() === 'resolved';

            return (
              <div
                key={task.id || task._id}
                style={{
                  backgroundColor: 'var(--bg-panel)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '16px',
                  position: 'relative',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                  transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--bg-card)';
                  e.currentTarget.style.borderColor = 'var(--border-color-active)';
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = '0 6px 12px rgba(0,0,0,0.15)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--bg-panel)';
                  e.currentTarget.style.borderColor = 'var(--border-color)';
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                }}
              >
                {/* Badge & dots */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  {getUrgencyBadge(task.urgency)}
                  {isResolved ? (
                    <CheckCircle2 size={16} style={{ color: '#10b981' }} />
                  ) : (
                    <button 
                      onClick={() => onResolve && onResolve(task._id || task.id)}
                      title="Mark task as resolved"
                      style={{
                        backgroundColor: 'transparent',
                        border: 'none',
                        color: '#64748b',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        transition: 'color 0.2s'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.color = '#10b981'}
                      onMouseLeave={(e) => e.currentTarget.style.color = '#64748b'}
                    >
                      <span style={{ fontSize: '12px', fontWeight: 'bold' }}>•••</span>
                    </button>
                  )}
                </div>

                {/* Description - Using Sans Serif for better readability */}
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginTop: '4px' }}>
                  {!isResolved && task.urgency?.toLowerCase() === 'urgent' && (
                    <AlertTriangle size={16} style={{ color: '#ef4444', flexShrink: 0, marginTop: '2px' }} />
                  )}
                  <span style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: '14px',
                    fontWeight: 700,
                    lineHeight: '1.4',
                    color: isResolved ? 'var(--text-muted)' : 'var(--text-primary)',
                    textDecoration: isResolved ? 'line-through' : 'none'
                  }}>
                    {task.title || task.task_description || task.description || "Active Dispatch Task"}
                  </span>
                </div>

                <div style={{ height: '1px', backgroundColor: '#1e293b', margin: '4px 0' }} />

                {/* Short Task description */}
                <span style={{ 
                  fontFamily: "'Plus Jakarta Sans', sans-serif",
                  fontSize: '12px', 
                  color: '#94a3b8', 
                  lineHeight: '1.5' 
                }}>
                  {task.detail || task.situation_summary || "Anomaly logged. Awaiting dispatch actions."}
                </span>
                
                {/* Details */}
                <span style={{ 
                  fontSize: '11px', 
                  color: 'var(--text-muted)', 
                  fontWeight: 600,
                  marginTop: '4px'
                }}>
                  {task.action_required}
                </span>

                {/* Action Buttons */}
                {!isResolved ? (
                  <div style={{ display: 'flex', gap: '10px', marginTop: '12px' }}>
                    <button 
                      onClick={() => onResolve && onResolve(task._id || task.id)}
                      style={{
                        flex: 1,
                        backgroundColor: 'var(--accent-color)',
                        border: '1px solid var(--accent-color)',
                        color: 'var(--bg-main)',
                        fontSize: '12px',
                        padding: '10px 0',
                        cursor: 'pointer',
                        borderRadius: '6px',
                        fontWeight: 600,
                        transition: 'all 0.2s',
                        boxShadow: '0 2px 4px rgba(56, 189, 248, 0.2)'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = '#0284c7'; // Darker blue
                        e.currentTarget.style.borderColor = '#0284c7';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'var(--accent-color)';
                        e.currentTarget.style.borderColor = 'var(--accent-color)';
                      }}
                    >
                      Action
                    </button>
                    <button 
                      style={{
                        flex: 1,
                        backgroundColor: 'transparent',
                        border: '1px solid var(--border-color-active)',
                        color: 'var(--text-primary)',
                        fontSize: '12px',
                        padding: '10px 0',
                        cursor: 'pointer',
                        borderRadius: '6px',
                        fontWeight: 500,
                        transition: 'all 0.2s'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)';
                        e.currentTarget.style.borderColor = 'var(--text-muted)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent';
                        e.currentTarget.style.borderColor = 'var(--border-color-active)';
                      }}
                    >
                      Assign
                    </button>
                  </div>
                ) : (
                  <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                    <button 
                      disabled
                      style={{
                        flex: 1,
                        backgroundColor: 'rgba(52, 211, 153, 0.1)',
                        border: '1px solid rgba(52, 211, 153, 0.2)',
                        color: 'var(--color-resolved)',
                        fontSize: '12px',
                        padding: '8px 0',
                        borderRadius: '6px',
                        fontWeight: 500,
                        textAlign: 'center'
                      }}
                    >
                      Resolved ✓
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div style={{
      height: '100%',
      flex: 1,
      backgroundColor: 'var(--bg-main)',
      borderTop: '1px solid var(--border-color)',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: fullScreen ? 1 : 0
    }}>
      {/* Legend & Header */}
      <div style={{
        padding: '12px 24px',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <h2 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '0.5px' }}>
          Active Operations
        </h2>
        
        {/* Legend */}
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '6px', height: '6px', backgroundColor: 'var(--color-critical)', borderRadius: '50%' }}></span>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 500 }}>Urgent</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '6px', height: '6px', backgroundColor: 'var(--color-warning)', borderRadius: '50%' }}></span>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 500 }}>Medium</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '6px', height: '6px', backgroundColor: 'var(--color-resolved)', borderRadius: '50%' }}></span>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 500 }}>Resolved</span>
          </div>
        </div>
      </div>

      {/* Grid columns */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {renderColumn('Maintenance', maintenanceTasks)}
        {renderColumn('Operations', operationsTasks)}
        {renderColumn('Station Manager', stationTasks)}
      </div>
    </div>
  );
}

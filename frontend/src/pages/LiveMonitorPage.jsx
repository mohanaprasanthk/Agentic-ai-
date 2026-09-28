import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import SectionCard from '../components/SectionCard';
import { createSimulationWebSocket } from '../services/websocket';

function labelForStatus(status) {
  switch (status) {
    case 'connected':
      return 'Connected';
    case 'disconnected':
      return 'Disconnected';
    case 'error':
      return 'Error';
    case 'completed':
      return 'Completed';
    case 'connecting':
    default:
      return 'Connecting';
  }
}

function formatTimestamp(value) {
  if (!value) {
    return 'just now';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function normalizeEvent(event) {
  if (!event || typeof event !== 'object') {
    return {
      event_type: 'INFO',
      message: String(event ?? 'No data available'),
      timestamp: new Date().toISOString(),
      payload: {},
    };
  }

  const payload = event.payload && typeof event.payload === 'object' ? event.payload : {};

  return {
    event_type: String(event.event_type || event.type || event.stage || 'INFO').toUpperCase(),
    simulation_id: event.simulation_id || payload.simulation_id || '',
    timestamp: event.timestamp || new Date().toISOString(),
    agent_id: event.agent_id || payload.agent_id || payload.actor_id || payload.requester_id || null,
    resource_id: event.resource_id || payload.resource_id || payload.resource_name || null,
    message:
      event.message ||
      event.content ||
      event.reason ||
      payload.message ||
      payload.content ||
      payload.reason ||
      JSON.stringify(payload) ||
      'Received event.',
    payload,
  };
}

export default function LiveMonitorPage() {
  const { simulation_id } = useParams();
  const socketRef = useRef(null);
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [events, setEvents] = useState([]);
  const [eventCount, setEventCount] = useState(0);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!simulation_id) {
      setConnectionStatus('error');
      setError('Simulation ID is missing.');
      return undefined;
    }

    const socket = createSimulationWebSocket(simulation_id, {
      onOpen: () => {
        setConnectionStatus('connected');
        setError('');
      },
      onMessage: (payload) => {
        const normalized = normalizeEvent(payload);
        setEvents((current) => [normalized, ...current]);
        setEventCount((current) => current + 1);

        const type = String(normalized.event_type || '').toUpperCase();
        if (type === 'SIMULATION_COMPLETED') {
          setConnectionStatus('completed');
        } else if (type === 'SIMULATION_FAILED') {
          setConnectionStatus('error');
        } else {
          setConnectionStatus((current) => (current === 'completed' || current === 'error' ? current : 'connected'));
        }
      },
      onClose: () => {
        setConnectionStatus((current) => (current === 'completed' ? 'completed' : 'disconnected'));
      },
      onError: () => {
        setConnectionStatus('error');
        setError('Unable to connect to the live simulation stream.');
      },
    });

    socketRef.current = socket;

    return () => {
      if (socket && typeof socket.close === 'function') {
        socket.close();
      }
    };
  }, [simulation_id]);

  const connectionClass = connectionStatus === 'error' ? 'error' : connectionStatus;

  return (
    <>
      <div className="page-header">
        <div>
          <p className="eyebrow">Live stream</p>
          <h2>Live negotiation monitor</h2>
        </div>
        <span className={`status-pill ${connectionClass}`}>{labelForStatus(connectionStatus)}</span>
      </div>

      <div className="stats-grid compact">
        <div className="stat-card accent-blue">
          <p>Connection status</p>
          <strong>{labelForStatus(connectionStatus)}</strong>
        </div>
        <div className="stat-card accent-purple">
          <p>Simulation ID</p>
          <strong>{simulation_id || 'N/A'}</strong>
        </div>
        <div className="stat-card accent-green">
          <p>Simulation status</p>
          <strong>{connectionStatus === 'connected' ? 'Running' : connectionStatus === 'completed' ? 'Completed' : connectionStatus === 'error' ? 'Error' : 'Waiting'}</strong>
        </div>
        <div className="stat-card accent-orange">
          <p>Event count</p>
          <strong>{eventCount}</strong>
        </div>
      </div>

      <div className="panel-grid two-columns">
        <SectionCard title="Monitor">
          <div className="detail-stack">
            <div className="detail-row"><span>Connection status</span><strong>{labelForStatus(connectionStatus)}</strong></div>
            <div className="detail-row"><span>Simulation status</span><strong>{connectionStatus === 'connected' ? 'Running' : connectionStatus === 'completed' ? 'Completed' : connectionStatus === 'error' ? 'Error' : 'Waiting'}</strong></div>
            <div className="detail-row"><span>Event count</span><strong>{eventCount}</strong></div>
          </div>
        </SectionCard>

        <SectionCard title="Live event stream" subtitle="Actual backend events received over WebSocket">
          {error ? <div className="alert error">{error}</div> : null}
          {events.length > 0 ? (
            <div className="event-stream">
              {events.map((event, index) => {
                const type = String(event.event_type || 'INFO').toUpperCase();
                const tagClass = type.toLowerCase();
                const lifecycleClass = type.includes('COMPLETED') ? 'success' : type.includes('FAILED') ? 'failed' : '';

                return (
                  <article className="event-item" key={`${event.timestamp}-${index}`}>
                    <div className="event-header">
                      <span className={`event-tag ${tagClass} ${type.includes('SIMULATION') ? 'lifecycle' : ''} ${lifecycleClass}`.trim()}>{type}</span>
                      <span className="event-time">{formatTimestamp(event.timestamp)}</span>
                    </div>
                    <div className="event-meta">
                      {event.agent_id ? <span>Agent: {event.agent_id}</span> : null}
                      {event.resource_id ? <span>Resource: {event.resource_id}</span> : null}
                      {event.simulation_id ? <span>Simulation: {event.simulation_id}</span> : null}
                    </div>
                    <p className="event-message">{event.message || 'No message was provided.'}</p>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="empty-state-box">
              <p className="muted">Waiting for live events from the backend…</p>
            </div>
          )}
        </SectionCard>
      </div>
    </>
  );
}

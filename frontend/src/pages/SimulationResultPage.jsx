import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import SectionCard from '../components/SectionCard';
import { getSimulation } from '../services/api';
import { writeSimulationHistory } from '../utils/simulationHistory';

function formatValue(value) {
  if (Array.isArray(value)) {
    return value.length ? value.join(', ') : 'None';
  }
  if (typeof value === 'object' && value !== null) {
    return JSON.stringify(value, null, 2);
  }
  return String(value ?? 'N/A');
}

export default function SimulationResultPage() {
  const { id } = useParams();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) {
      setError('Simulation ID is missing.');
      setLoading(false);
      return;
    }

    let active = true;

    async function loadSimulation() {
      try {
        const data = await getSimulation(id);
        if (!active) {
          return;
        }
        setResult(data);
        writeSimulationHistory(data);
      } catch (err) {
        if (active) {
          setError(err.message || 'The simulation result could not be loaded.');
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadSimulation();
    return () => {
      active = false;
    };
  }, [id]);

  if (loading) {
    return <div className="loading-box">Loading simulation result…</div>;
  }

  if (error) {
    return <div className="alert error">{error}</div>;
  }

  if (!result) {
    return <div className="alert warning">No simulation result was returned.</div>;
  }

  return (
    <>
      <div className="page-header">
        <div>
          <p className="eyebrow">Simulation details</p>
          <h2>Simulation result</h2>
        </div>
        <Link to={`/metrics/${result.simulation_id}`} className="secondary-button">
          View metrics
        </Link>
      </div>

      <div className="stats-grid compact">
        <div className="stat-card accent-blue">
          <p>Architecture</p>
          <strong>{result.architecture || 'UNKNOWN'}</strong>
        </div>
        <div className="stat-card accent-green">
          <p>Success</p>
          <strong>{result.success ? 'Successful' : 'Failed'}</strong>
        </div>
        <div className="stat-card accent-purple">
          <p>Negotiation rounds</p>
          <strong>{result.negotiation_rounds ?? 0}</strong>
        </div>
        <div className="stat-card accent-orange">
          <p>Execution time</p>
          <strong>{Number(result.execution_time ?? 0).toFixed(2)}s</strong>
        </div>
      </div>

      <div className="panel-grid two-columns">
        <SectionCard title="Outcome" subtitle={`Simulation ID: ${result.simulation_id}`}>
          <div className="detail-stack">
            <div className="detail-row"><span>Success</span><strong>{String(result.success)}</strong></div>
            <div className="detail-row"><span>Successful negotiations</span><strong>{(result.successful_negotiations || []).length}</strong></div>
            <div className="detail-row"><span>Failed negotiations</span><strong>{(result.failed_negotiations || []).length}</strong></div>
            <div className="detail-row"><span>Unresolved conflicts</span><strong>{(result.unresolved_conflicts || []).length}</strong></div>
          </div>
        </SectionCard>

        <SectionCard title="Final allocation" subtitle="Resource assignments returned by the backend">
          {result.final_allocation && Object.keys(result.final_allocation).length > 0 ? (
            <div className="object-grid">
              {Object.entries(result.final_allocation).map(([key, value]) => (
                <div className="object-item" key={key}>
                  <span className="label">{key}</span>
                  <pre>{formatValue(value)}</pre>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted">No final allocation data is available.</p>
          )}
        </SectionCard>
      </div>

      <div className="panel-grid two-columns">
        <SectionCard title="Negotiation events" subtitle="Detailed backend events">
          {result.negotiation_events && result.negotiation_events.length > 0 ? (
            <ul className="list-rows">
              {result.negotiation_events.map((event, index) => (
                <li key={`${event.type || 'event'}-${index}`}>
                  {JSON.stringify(event)}
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No negotiation events recorded.</p>
          )}
        </SectionCard>

        <SectionCard title="Communication messages" subtitle="Message flow recorded by the backend">
          {result.communication_messages && result.communication_messages.length > 0 ? (
            <ul className="list-rows">
              {result.communication_messages.map((message, index) => (
                <li key={`${message.sender || 'message'}-${index}`}>
                  {JSON.stringify(message)}
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No communication messages recorded.</p>
          )}
        </SectionCard>
      </div>

      {result.errors && result.errors.length > 0 ? (
        <SectionCard title="Errors">
          <ul className="list-rows">
            {result.errors.map((message, index) => <li key={`${message}-${index}`}>{message}</li>)}
          </ul>
        </SectionCard>
      ) : null}
    </>
  );
}

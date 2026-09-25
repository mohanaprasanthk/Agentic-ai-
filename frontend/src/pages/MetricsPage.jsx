import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import SectionCard from '../components/SectionCard';
import StatCard from '../components/StatCard';
import { getMetrics } from '../services/api';

const metricCards = [
  ['Total Requests', 'total_requests'],
  ['Successful Negotiations', 'successful_negotiations'],
  ['Failed Negotiations', 'failed_negotiations'],
  ['Success Rate', 'success_rate', true],
  ['Resource Utilization', 'resource_utilization', true],
  ['Total Execution Time', 'total_execution_time'],
  ['Average Negotiation Time', 'average_negotiation_time'],
  ['Communication Overhead', 'communication_overhead'],
  ['Number of Conflicts', 'number_of_conflicts'],
  ['Average Agent Utility', 'average_agent_utility'],
  ['Fairness', 'fairness'],
  ['Negotiation Rounds', 'negotiation_rounds'],
];

function formatMetric(value, suffix = false) {
  if (value === null || value === undefined || value === '') {
    return '0';
  }
  const formatted = Number(value);
  if (Number.isNaN(formatted)) {
    return String(value);
  }
  return suffix ? `${formatted.toFixed(2)}%` : formatted.toFixed(2);
}

export default function MetricsPage() {
  const { id } = useParams();
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadMetrics() {
      try {
        const data = await getMetrics(id);
        setMetrics(data);
      } catch (err) {
        setError(err.message || 'Metrics could not be loaded.');
      } finally {
        setLoading(false);
      }
    }

    if (id) {
      loadMetrics();
    }
  }, [id]);

  if (loading) {
    return <div className="loading-box">Loading metrics…</div>;
  }

  if (error) {
    return <div className="alert error">{error}</div>;
  }

  if (!metrics) {
    return <div className="alert warning">No metrics are available for this simulation.</div>;
  }

  return (
    <>
      <div className="page-header">
        <div>
          <p className="eyebrow">Performance</p>
          <h2>Metrics</h2>
        </div>
      </div>

      <div className="stats-grid">
        {metricCards.map(([label, key, percent]) => (
          <StatCard
            key={key}
            label={label}
            value={formatMetric(metrics[key], percent)}
            accent={['blue', 'green', 'purple', 'orange'][Math.abs(key.length) % 4]}
          />
        ))}
      </div>

      <SectionCard title="Metric details" subtitle={`Simulation ID: ${metrics.simulation_id || id}`}>
        <div className="detail-stack">
          <div className="detail-row"><span>Architecture</span><strong>{metrics.architecture || 'UNKNOWN'}</strong></div>
          <div className="detail-row"><span>Simulation ID</span><strong>{metrics.simulation_id || id}</strong></div>
          {metrics.errors && metrics.errors.length > 0 ? (
            <div className="detail-row"><span>Errors</span><strong>{metrics.errors.join(', ')}</strong></div>
          ) : null}
        </div>
      </SectionCard>
    </>
  );
}

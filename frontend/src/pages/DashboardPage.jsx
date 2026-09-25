import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import SectionCard from '../components/SectionCard';
import StatCard from '../components/StatCard';
import { getAgents, getMetrics, getResources } from '../services/api';
import { getLatestSimulation, readComparisonSummary, readSimulationHistory } from '../utils/simulationHistory';

const formatPercent = (value) => `${Number(value ?? 0).toFixed(2)}%`;

export default function DashboardPage() {
  const [agents, setAgents] = useState([]);
  const [resources, setResources] = useState([]);
  const [history, setHistory] = useState([]);
  const [comparisonSummary, setComparisonSummary] = useState(null);
  const [latestMetrics, setLatestMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      try {
        setLoading(true);
        const [agentList, resourceList] = await Promise.all([getAgents(), getResources()]);
        const savedHistory = readSimulationHistory();
        const savedComparison = readComparisonSummary();

        if (!active) {
          return;
        }

        setAgents(agentList || []);
        setResources(resourceList || []);
        setHistory(savedHistory);
        setComparisonSummary(savedComparison);

        const latest = getLatestSimulation();
        if (latest?.simulation_id) {
          const metrics = await getMetrics(latest.simulation_id);
          if (active) {
            setLatestMetrics(metrics);
          }
        }
      } catch (err) {
        if (active) {
          setError(err.message || 'Unable to load dashboard data.');
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadDashboard();
    return () => {
      active = false;
    };
  }, []);

  const latestSimulation = useMemo(() => history.at(-1) || getLatestSimulation(), [history]);
  const latestSuccessRate = latestMetrics?.success_rate ?? latestSimulation?.success_rate ?? 0;

  return (
    <>
      <div className="page-header">
        <div>
          <p className="eyebrow">Overview</p>
          <h2>Dashboard</h2>
        </div>
      </div>

      {error ? <div className="alert error">{error}</div> : null}

      {loading ? (
        <div className="loading-box">Loading dashboard…</div>
      ) : (
        <>
          <div className="stats-grid">
            <StatCard label="Total Agents" value={agents.length} accent="blue" />
            <StatCard label="Total Resources" value={resources.length} accent="green" />
            <StatCard label="Total Simulations" value={history.length} accent="purple" />
            <StatCard label="Latest Success Rate" value={formatPercent(latestSuccessRate)} accent="orange" />
          </div>

          <div className="panel-grid two-columns">
            <SectionCard
              title="Latest Simulation"
              subtitle={latestSimulation ? `Simulation ${latestSimulation.simulation_id}` : 'No simulations have been recorded yet.'}
            >
              {latestSimulation ? (
                <div className="detail-stack">
                  <div className="detail-row">
                    <span>Architecture</span>
                    <strong>{latestSimulation.architecture || 'UNKNOWN'}</strong>
                  </div>
                  <div className="detail-row">
                    <span>Success</span>
                    <strong>{String(latestSimulation.success ?? false)}</strong>
                  </div>
                  <div className="detail-row">
                    <span>Simulation ID</span>
                    <strong>{latestSimulation.simulation_id}</strong>
                  </div>
                  <Link to={`/simulation/${latestSimulation.simulation_id}`} className="primary-link">
                    View result
                  </Link>
                </div>
              ) : (
                <p className="muted">Run a simulation to populate the dashboard history.</p>
              )}
            </SectionCard>

            <SectionCard title="Architecture Comparison Summary" subtitle="Latest architecture performance snapshot">
              {comparisonSummary && comparisonSummary.results ? (
                <div className="detail-stack">
                  <div className="detail-row">
                    <span>Available architectures</span>
                    <strong>{Object.keys(comparisonSummary.results).length}</strong>
                  </div>
                  <div className="detail-row">
                    <span>Latest result</span>
                    <strong>{Object.keys(comparisonSummary.results)[0] || 'Not available'}</strong>
                  </div>
                  <div className="detail-row">
                    <span>Success</span>
                    <strong>{Object.values(comparisonSummary.results).some((entry) => entry.success) ? 'Pass' : 'Review needed'}</strong>
                  </div>
                  <Link to="/comparison" className="primary-link">
                    Compare architectures
                  </Link>
                </div>
              ) : (
                <p className="muted">Run a comparison to view results here.</p>
              )}
            </SectionCard>
          </div>
        </>
      )}
    </>
  );
}

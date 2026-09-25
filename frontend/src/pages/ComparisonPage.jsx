import { useEffect, useState } from 'react';
import SectionCard from '../components/SectionCard';
import { getAgents, getResources, runComparison } from '../services/api';
import { writeComparisonSummary } from '../utils/simulationHistory';

function createDefaultComparisonScenario(agentList, resourceList) {
  const firstAgent = agentList[0];
  const resource = (resourceList[0] || { name: 'GPU Cluster' }).name;

  return {
    architecture: 'CENTRALIZED',
    agents: agentList.length ? agentList.slice(0, 2) : [
      { id: 'agent-01', name: 'Alice', type: 'researcher', capabilities: ['analysis'] },
      { id: 'agent-02', name: 'Bob', type: 'provider', capabilities: ['compute'] },
    ],
    resources: resourceList.length ? resourceList.slice(0, 1) : [{ id: 'resource-01', name: 'GPU Cluster', kind: 'compute' }],
    requests: [
      {
        id: 'request-01',
        title: 'Need GPU access',
        description: 'Support the main workload for comparison.',
        requester_id: (firstAgent && firstAgent.id) || 'agent-01',
        required_resources: [resource],
        priority: 'high',
      },
    ],
  };
}

export default function ComparisonPage() {
  const [agents, setAgents] = useState([]);
  const [resources, setResources] = useState([]);
  const [scenario, setScenario] = useState({
    architecture: 'CENTRALIZED',
    agents: [],
    resources: [],
    requests: [],
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadComparisonSetup() {
      try {
        const [agentList, resourceList] = await Promise.all([getAgents(), getResources()]);
        const initialScenario = createDefaultComparisonScenario(agentList || [], resourceList || []);
        setAgents(agentList || []);
        setResources(resourceList || []);
        setScenario(initialScenario);
      } catch (err) {
        setError(err.message || 'Unable to load comparison setup.');
      } finally {
        setLoading(false);
      }
    }

    loadComparisonSetup();
  }, []);

  async function handleRunComparison(event) {
    event.preventDefault();
    setSubmitting(true);
    setError('');

    try {
      const payload = {
        ...scenario,
        architecture: scenario.architecture,
        agents: scenario.agents.length ? scenario.agents : agents,
        resources: scenario.resources.length ? scenario.resources : resources,
      };
      const comparison = await runComparison(payload);
      writeComparisonSummary(comparison);
      setResult(comparison);
    } catch (err) {
      setError(err.message || 'The architecture comparison could not be executed.');
    } finally {
      setSubmitting(false);
    }
  }

  const rows = result && result.results ? Object.entries(result.results) : [];

  return (
    <>
      <div className="page-header">
        <div>
          <p className="eyebrow">Benchmarking</p>
          <h2>Architecture comparison</h2>
        </div>
      </div>

      {error ? <div className="alert error">{error}</div> : null}

      {loading ? (
        <div className="loading-box">Loading comparison setup…</div>
      ) : (
        <form className="stack-form panel" onSubmit={handleRunComparison}>
          <div className="field-grid two-columns">
            <label>
              <span>Architecture</span>
              <select value={scenario.architecture} onChange={(e) => setScenario({ ...scenario, architecture: e.target.value })}>
                <option value="CENTRALIZED">CENTRALIZED</option>
                <option value="HIERARCHICAL">HIERARCHICAL</option>
                <option value="DECENTRALIZED">DECENTRALIZED</option>
                <option value="SEQUENTIAL">SEQUENTIAL</option>
                <option value="PARALLEL">PARALLEL</option>
                <option value="BLACKBOARD">BLACKBOARD</option>
                <option value="PEER_TO_PEER">PEER_TO_PEER</option>
              </select>
            </label>
          </div>

          <button type="submit" className="primary-button" disabled={submitting}>
            {submitting ? 'Running comparison…' : 'Run comparison'}
          </button>
        </form>
      )}

      {result ? (
        <SectionCard title="Results table" subtitle="Values are returned directly from the backend">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Architecture</th>
                  <th>Success</th>
                  <th>Success Rate</th>
                  <th>Resource Utilization</th>
                  <th>Execution Time</th>
                  <th>Average Negotiation Time</th>
                  <th>Communication Overhead</th>
                  <th>Conflicts</th>
                  <th>Average Agent Utility</th>
                  <th>Fairness</th>
                  <th>Negotiation Rounds</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(([architecture, entry]) => (
                  <tr key={architecture}>
                    <td>{architecture}</td>
                    <td>{entry.success ? 'Yes' : 'No'}</td>
                    <td>{Number(entry.success_rate ?? 0).toFixed(2)}%</td>
                    <td>{Number(entry.resource_utilization ?? 0).toFixed(2)}%</td>
                    <td>{Number(entry.total_execution_time ?? 0).toFixed(2)}s</td>
                    <td>{Number(entry.average_negotiation_time ?? 0).toFixed(2)}s</td>
                    <td>{Number(entry.communication_overhead ?? 0)}</td>
                    <td>{Number(entry.number_of_conflicts ?? 0)}</td>
                    <td>{Number(entry.average_agent_utility ?? 0).toFixed(2)}</td>
                    <td>{Number(entry.fairness ?? 0).toFixed(2)}</td>
                    <td>{Number(entry.negotiation_rounds ?? 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      ) : null}
    </>
  );
}

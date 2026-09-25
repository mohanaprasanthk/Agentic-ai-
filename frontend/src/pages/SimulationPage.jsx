import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import SectionCard from '../components/SectionCard';
import { getAgents, getResources, runSimulation } from '../services/api';
import { writeSimulationHistory } from '../utils/simulationHistory';

function createDefaultScenario(agentList, resourceList) {
  const firstAgent = agentList[0];
  const secondAgent = agentList[1] || agentList[0];
  const firstResource = resourceList[0] || { name: 'GPU Cluster', id: 'resource-01' };

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
        description: 'Support the current workload.',
        requester_id: (firstAgent && firstAgent.id) || 'agent-01',
        required_resources: [firstResource.name],
        priority: 'high',
      },
      {
        id: 'request-02',
        title: 'Need support from provider',
        description: 'Secondary resource request.',
        requester_id: (secondAgent && secondAgent.id) || 'agent-02',
        required_resources: [firstResource.name],
        priority: 'medium',
      },
    ],
  };
}

export default function SimulationPage() {
  const navigate = useNavigate();
  const [agents, setAgents] = useState([]);
  const [resources, setResources] = useState([]);
  const [scenario, setScenario] = useState({
    architecture: 'CENTRALIZED',
    agents: [],
    resources: [],
    requests: [],
  });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    async function loadScenarioData() {
      try {
        const [agentList, resourceList] = await Promise.all([getAgents(), getResources()]);
        if (!active) {
          return;
        }

        const initialScenario = createDefaultScenario(agentList || [], resourceList || []);
        setAgents(agentList || []);
        setResources(resourceList || []);
        setScenario(initialScenario);
      } catch (err) {
        if (active) {
          setError(err.message || 'Unable to load simulation setup.');
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadScenarioData();
    return () => {
      active = false;
    };
  }, []);

  function updateRequestField(index, field, value) {
    setScenario((current) => ({
      ...current,
      requests: current.requests.map((request, idx) => (idx === index ? { ...request, [field]: value } : request)),
    }));
  }

  async function handleSubmit(event) {
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

      const result = await runSimulation(payload);
      writeSimulationHistory(result);
      navigate(`/simulation/${result.simulation_id}`);
    } catch (err) {
      setError(err.message || 'Simulation could not be executed.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <p className="eyebrow">Scenario runner</p>
          <h2>Simulation</h2>
        </div>
      </div>

      {error ? <div className="alert error">{error}</div> : null}

      {loading ? (
        <div className="loading-box">Loading simulation setup…</div>
      ) : (
        <form className="stack-form panel" onSubmit={handleSubmit}>
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

          <SectionCard title="Scenario metadata" subtitle="Agents and resources selected for this run">
            <div className="field-grid two-columns">
              <label>
                <span>Agents</span>
                <select
                  multiple
                  value={(scenario.agents || []).map((agent) => agent.id)}
                  onChange={(e) => {
                    const selected = Array.from(e.target.selectedOptions, (option) => agents.find((agent) => agent.id === option.value)).filter(Boolean);
                    setScenario({ ...scenario, agents: selected });
                  }}
                >
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                <span>Resources</span>
                <select
                  multiple
                  value={(scenario.resources || []).map((resource) => resource.name)}
                  onChange={(e) => {
                    const selected = Array.from(e.target.selectedOptions, (option) => resources.find((resource) => resource.name === option.value)).filter(Boolean);
                    setScenario({ ...scenario, resources: selected });
                  }}
                >
                  {resources.map((resource) => (
                    <option key={resource.id} value={resource.name}>
                      {resource.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </SectionCard>

          <SectionCard title="Requests" subtitle="Define the workload to negotiate">
            {scenario.requests.map((request, index) => (
              <div className="request-card" key={request.id || index}>
                <div className="field-grid three-columns">
                  <label>
                    <span>ID</span>
                    <input value={request.id} onChange={(e) => updateRequestField(index, 'id', e.target.value)} />
                  </label>
                  <label>
                    <span>Requester</span>
                    <select value={request.requester_id} onChange={(e) => updateRequestField(index, 'requester_id', e.target.value)}>
                      {agents.map((agent) => (
                        <option key={agent.id} value={agent.id}>
                          {agent.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>Priority</span>
                    <select value={request.priority} onChange={(e) => updateRequestField(index, 'priority', e.target.value)}>
                      <option value="high">high</option>
                      <option value="medium">medium</option>
                      <option value="low">low</option>
                    </select>
                  </label>
                </div>

                <div className="field-grid two-columns">
                  <label>
                    <span>Title</span>
                    <input value={request.title} onChange={(e) => updateRequestField(index, 'title', e.target.value)} />
                  </label>
                  <label>
                    <span>Required resource</span>
                    <input
                      value={request.required_resources?.join(', ') || ''}
                      onChange={(e) => updateRequestField(index, 'required_resources', e.target.value.split(',').map((value) => value.trim()).filter(Boolean))}
                    />
                  </label>
                </div>

                <label>
                  <span>Description</span>
                  <textarea value={request.description} onChange={(e) => updateRequestField(index, 'description', e.target.value)} rows="3" />
                </label>
              </div>
            ))}
          </SectionCard>

          <button type="submit" className="primary-button" disabled={submitting}>
            {submitting ? 'Running simulation…' : 'Run simulation'}
          </button>
        </form>
      )}
    </>
  );
}

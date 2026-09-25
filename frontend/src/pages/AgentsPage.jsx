import { useEffect, useState } from 'react';
import EmptyState from '../components/EmptyState';
import SectionCard from '../components/SectionCard';
import { createAgent, getAgents } from '../services/api';

const buildAgentPayload = (form) => ({
  id: form.id || `agent-${Date.now()}`,
  name: form.name,
  type: form.type,
  capabilities: form.capabilities
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean),
});

export default function AgentsPage() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    id: '',
    name: '',
    type: 'researcher',
    capabilities: 'analysis, negotiation',
  });

  async function fetchAgents() {
    setLoading(true);
    try {
      const data = await getAgents();
      setAgents(data || []);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load agents.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAgents();
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!form.name.trim()) {
      setError('Agent name is required.');
      return;
    }

    setSubmitting(true);
    try {
      await createAgent(buildAgentPayload(form));
      setForm({ id: '', name: '', type: 'researcher', capabilities: 'analysis, negotiation' });
      await fetchAgents();
    } catch (err) {
      setError(err.message || 'Agent could not be created.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <p className="eyebrow">Registry</p>
          <h2>Agents</h2>
        </div>
      </div>

      {error ? <div className="alert error">{error}</div> : null}

      <div className="panel-grid two-columns">
        <SectionCard title="Create agent" subtitle="Add a new negotiation participant">
          <form className="stack-form" onSubmit={handleSubmit}>
            <div className="field-grid two-columns">
              <label>
                <span>ID</span>
                <input
                  type="text"
                  value={form.id}
                  onChange={(e) => setForm({ ...form, id: e.target.value })}
                  placeholder="Optional"
                />
              </label>
              <label>
                <span>Type</span>
                <input
                  type="text"
                  value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value })}
                />
              </label>
            </div>

            <label>
              <span>Name</span>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Agent name"
              />
            </label>

            <label>
              <span>Capabilities</span>
              <input
                type="text"
                value={form.capabilities}
                onChange={(e) => setForm({ ...form, capabilities: e.target.value })}
                placeholder="analysis, compute, negotiation"
              />
            </label>

            <button type="submit" className="primary-button" disabled={submitting}>
              {submitting ? 'Creating…' : 'Create agent'}
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Agent list" subtitle={loading ? 'Loading agents…' : `${agents.length} agents available`}>
          {loading ? (
            <div className="loading-box">Loading agents…</div>
          ) : agents.length === 0 ? (
            <EmptyState title="No agents found" description="Create your first agent to start a simulation." />
          ) : (
            <div className="resource-list">
              {agents.map((agent) => (
                <div className="list-item" key={agent.id || agent.name}>
                  <div>
                    <strong>{agent.name}</strong>
                    <p>{agent.type}</p>
                  </div>
                  <div className="chip-row">
                    {(agent.capabilities || []).map((capability) => (
                      <span className="chip" key={`${agent.id}-${capability}`}>
                        {capability}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>
    </>
  );
}

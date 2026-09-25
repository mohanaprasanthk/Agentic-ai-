import { useEffect, useState } from 'react';
import EmptyState from '../components/EmptyState';
import SectionCard from '../components/SectionCard';
import { createResource, getResources } from '../services/api';

const buildResourcePayload = (form) => ({
  id: form.id || `resource-${Date.now()}`,
  name: form.name,
  kind: form.kind,
  url: form.url,
});

export default function ResourcesPage() {
  const [resources, setResources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    id: '',
    name: '',
    kind: 'compute',
    url: '',
  });

  async function fetchResources() {
    setLoading(true);
    try {
      const data = await getResources();
      setResources(data || []);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load resources.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchResources();
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!form.name.trim() || !form.kind.trim()) {
      setError('Resource name and kind are required.');
      return;
    }

    setSubmitting(true);
    try {
      await createResource(buildResourcePayload(form));
      setForm({ id: '', name: '', kind: 'compute', url: '' });
      await fetchResources();
    } catch (err) {
      setError(err.message || 'Resource could not be created.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <p className="eyebrow">Inventory</p>
          <h2>Resources</h2>
        </div>
      </div>

      {error ? <div className="alert error">{error}</div> : null}

      <div className="panel-grid two-columns">
        <SectionCard title="Create resource" subtitle="Add a new resource to the negotiation pool">
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
                <span>Kind</span>
                <input
                  type="text"
                  value={form.kind}
                  onChange={(e) => setForm({ ...form, kind: e.target.value })}
                />
              </label>
            </div>

            <label>
              <span>Name</span>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="GPU Cluster"
              />
            </label>

            <label>
              <span>URL</span>
              <input
                type="url"
                value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
                placeholder="https://example.com"
              />
            </label>

            <button type="submit" className="primary-button" disabled={submitting}>
              {submitting ? 'Creating…' : 'Create resource'}
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Resource list" subtitle={loading ? 'Loading resources…' : `${resources.length} resources available`}>
          {loading ? (
            <div className="loading-box">Loading resources…</div>
          ) : resources.length === 0 ? (
            <EmptyState title="No resources found" description="Add a resource before starting a scenario." />
          ) : (
            <div className="resource-list">
              {resources.map((resource) => (
                <div className="list-item" key={resource.id || resource.name}>
                  <div>
                    <strong>{resource.name}</strong>
                    <p>{resource.kind}</p>
                  </div>
                  {resource.url ? <span className="monospace">{resource.url}</span> : null}
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>
    </>
  );
}

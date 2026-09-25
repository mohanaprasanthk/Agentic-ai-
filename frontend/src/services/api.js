const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  const payload = await response.text();
  let data = null;

  if (payload) {
    try {
      data = JSON.parse(payload);
    } catch {
      data = payload;
    }
  }

  if (!response.ok) {
    const detail = data?.detail;
    if (Array.isArray(detail)) {
      const first = detail[0];
      throw new Error(first?.msg || 'Request failed.');
    }
    if (typeof detail === 'string') {
      throw new Error(detail);
    }
    if (typeof data === 'string' && data.trim()) {
      throw new Error(data);
    }
    throw new Error(`Request failed with status ${response.status}.`);
  }

  return data;
}

export async function getAgents() {
  return request('/api/agents');
}

export async function createAgent(agent) {
  return request('/api/agents', {
    method: 'POST',
    body: JSON.stringify(agent),
  });
}

export async function getResources() {
  return request('/api/resources');
}

export async function createResource(resource) {
  return request('/api/resources', {
    method: 'POST',
    body: JSON.stringify(resource),
  });
}

export async function runSimulation(payload) {
  return request('/api/simulation/run', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getSimulation(simulationId) {
  return request(`/api/simulation/${simulationId}`);
}

export async function getMetrics(simulationId) {
  return request(`/api/simulation/${simulationId}/metrics`);
}

export async function runComparison(payload) {
  return request('/api/comparison/run', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export { API_BASE_URL };

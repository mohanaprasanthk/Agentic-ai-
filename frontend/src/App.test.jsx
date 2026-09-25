import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import App from './App';

const mockFetch = vi.fn(async (input, init) => {
  const url = String(input);
  const method = init?.method || 'GET';

  if (url.endsWith('/api/agents') && method === 'GET') {
    return {
      ok: true,
      text: async () => JSON.stringify([
        { id: 'agent-01', name: 'Alice', type: 'researcher', capabilities: ['analysis'] },
      ]),
    };
  }

  if (url.endsWith('/api/resources') && method === 'GET') {
    return {
      ok: true,
      text: async () => JSON.stringify([
        { id: 'resource-01', name: 'GPU Cluster', kind: 'compute', url: 'https://example.com/gpu' },
      ]),
    };
  }

  if (url.endsWith('/api/simulation/run') && method === 'POST') {
    return {
      ok: true,
      text: async () => JSON.stringify({
        simulation_id: 'sim-123',
        architecture: 'CENTRALIZED',
        success: true,
        final_allocation: { 'request-01': { resource_name: 'GPU Cluster' } },
        successful_negotiations: ['request-01'],
        failed_negotiations: [],
        unresolved_conflicts: [],
        negotiation_events: [{ type: 'agreement', status: 'accepted' }],
        negotiation_rounds: 1,
        communication_messages: [{ sender: 'agent-01', receiver: 'agent-02' }],
        execution_time: 0.5,
        errors: [],
      }),
    };
  }

  if (url.includes('/api/simulation/sim-123') && method === 'GET') {
    return {
      ok: true,
      text: async () => JSON.stringify({
        simulation_id: 'sim-123',
        architecture: 'CENTRALIZED',
        success: true,
        final_allocation: { 'request-01': { resource_name: 'GPU Cluster' } },
        successful_negotiations: ['request-01'],
        failed_negotiations: [],
        unresolved_conflicts: [],
        negotiation_events: [{ type: 'agreement', status: 'accepted' }],
        negotiation_rounds: 1,
        communication_messages: [{ sender: 'agent-01', receiver: 'agent-02' }],
        execution_time: 0.5,
        errors: [],
      }),
    };
  }

  if (url.includes('/api/simulation/sim-123/metrics') && method === 'GET') {
    return {
      ok: true,
      text: async () => JSON.stringify({
        architecture: 'CENTRALIZED',
        simulation_id: 'sim-123',
        total_requests: 1,
        successful_negotiations: 1,
        failed_negotiations: 0,
        success_rate: 100,
        resource_utilization: 100,
        total_execution_time: 0.5,
        average_negotiation_time: 0.2,
        communication_overhead: 2,
        number_of_conflicts: 0,
        average_agent_utility: 90,
        fairness: 1,
        negotiation_rounds: 1,
        errors: [],
      }),
    };
  }

  if (url.endsWith('/api/comparison/run') && method === 'POST') {
    return {
      ok: true,
      text: async () => JSON.stringify({
        results: {
          CENTRALIZED: {
            architecture: 'CENTRALIZED',
            success: true,
            success_rate: 100,
            resource_utilization: 100,
            total_execution_time: 0.5,
            average_negotiation_time: 0.2,
            communication_overhead: 2,
            number_of_conflicts: 0,
            average_agent_utility: 90,
            fairness: 1,
            negotiation_rounds: 1,
          },
        },
      }),
    };
  }

  return {
    ok: true,
    text: async () => JSON.stringify([]),
  };
});

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch);
  window.localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('One Credit frontend', () => {
  it('renders the dashboard and loads summary data', async () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>,
    );

    expect(await screen.findByRole('heading', { name: /^Dashboard$/i })).toBeInTheDocument();
    expect(screen.getByText(/Total Agents/i)).toBeInTheDocument();
    expect(screen.getByText(/Total Resources/i)).toBeInTheDocument();
  });

  it('navigates to agents page and shows fetched agent data', async () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>,
    );

    fireEvent.click(screen.getByRole('link', { name: /agents/i }));

    expect(await screen.findByText(/Agent list/i)).toBeInTheDocument();
    expect(await screen.findByText(/Alice/i)).toBeInTheDocument();
  });

  it('runs a simulation and navigates to result page', async () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>,
    );

    fireEvent.click(await screen.findByRole('link', { name: /simulation/i }));
    fireEvent.click(await screen.findByRole('button', { name: /^Run simulation$/i }));

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /^Simulation result$/i })).toBeInTheDocument();
    });
  });

  it('renders the metrics page for a simulation id', async () => {
    window.history.pushState({}, '', '/metrics/sim-123');
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>,
    );

    expect(await screen.findByText(/Metrics/i)).toBeInTheDocument();
    expect(await screen.findByText(/Total Requests/i)).toBeInTheDocument();
  });

  it('renders the comparison page and result table', async () => {
    window.history.pushState({}, '', '/comparison');
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>,
    );

    fireEvent.click(await screen.findByRole('button', { name: /^Run comparison$/i }));

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /^Architecture comparison$/i })).toBeInTheDocument();
    });
  });
});

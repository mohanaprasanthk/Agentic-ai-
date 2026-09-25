const STORAGE_KEY = 'one-credit-simulation-history';
const COMPARISON_KEY = 'one-credit-comparison-summary';

export function readSimulationHistory() {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

export function writeSimulationHistory(simulation) {
  if (!simulation || !simulation.simulation_id) {
    return [];
  }

  const existing = readSimulationHistory();
  const next = [
    ...existing.filter((item) => item.simulation_id !== simulation.simulation_id),
    simulation,
  ].slice(-12);

  if (typeof window !== 'undefined') {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }

  return next;
}

export function getLatestSimulation() {
  const history = readSimulationHistory();
  return history.at(-1) || null;
}

export function readComparisonSummary() {
  try {
    const stored = window.localStorage.getItem(COMPARISON_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

export function writeComparisonSummary(summary) {
  if (!summary) {
    return null;
  }

  if (typeof window !== 'undefined') {
    window.localStorage.setItem(COMPARISON_KEY, JSON.stringify(summary));
  }

  return summary;
}

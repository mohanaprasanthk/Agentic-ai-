const BASE_WS_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';

export function createSimulationWebSocket(simulationId, handlers = {}) {
  if (!simulationId) {
    return null;
  }

  const socket = new WebSocket(`${BASE_WS_URL}/ws/simulation/${simulationId}`);

  const onOpen = handlers.onOpen || (() => {});
  const onMessage = handlers.onMessage || (() => {});
  const onClose = handlers.onClose || (() => {});
  const onError = handlers.onError || (() => {});

  socket.addEventListener('open', onOpen);
  socket.addEventListener('message', (event) => {
    try {
      const payload = JSON.parse(event.data);
      onMessage(payload);
    } catch {
      onMessage({ event_type: 'INFO', message: String(event.data || 'No data') });
    }
  });
  socket.addEventListener('close', onClose);
  socket.addEventListener('error', onError);

  return socket;
}

export default createSimulationWebSocket;

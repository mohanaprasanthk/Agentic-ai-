import { Navigate, NavLink, Route, Routes } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import AgentsPage from './pages/AgentsPage';
import ResourcesPage from './pages/ResourcesPage';
import SimulationPage from './pages/SimulationPage';
import SimulationResultPage from './pages/SimulationResultPage';
import MetricsPage from './pages/MetricsPage';
import ComparisonPage from './pages/ComparisonPage';

function AppLayout() {
  const navItems = [
    { to: '/', label: 'Dashboard' },
    { to: '/agents', label: 'Agents' },
    { to: '/resources', label: 'Resources' },
    { to: '/simulation', label: 'Simulation' },
    { to: '/comparison', label: 'Comparison' },
  ];

  return (
    <>
      <header className="topbar">
        <div className="brand-wrap">
          <div className="brand-mark">OC</div>
          <div>
            <p className="eyebrow">Project dashboard</p>
            <h1>One Credit</h1>
          </div>
        </div>
        <div className="topbar-meta">
          <span className="status-pill">Live backend</span>
        </div>
      </header>

      <div className="shell">
        <aside className="sidebar">
          <nav className="nav">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </aside>

        <main className="content-area">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/agents" element={<AgentsPage />} />
            <Route path="/resources" element={<ResourcesPage />} />
            <Route path="/simulation" element={<SimulationPage />} />
            <Route path="/simulation/:id" element={<SimulationResultPage />} />
            <Route path="/metrics/:id" element={<MetricsPage />} />
            <Route path="/comparison" element={<ComparisonPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </>
  );
}

export default function App() {
  return <AppLayout />;
}

export default function StatCard({ label, value, accent = 'blue' }) {
  return (
    <div className={`stat-card accent-${accent}`}>
      <p>{label}</p>
      <strong>{value}</strong>
    </div>
  );
}

const fmtDate = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  })

export default function HealthCards({ summary }) {
  if (!summary) return null
  const range = summary.date_range
  return (
    <div className="stats">
      <div className="card stat">
        <div className="label">Rows</div>
        <div className="value">{summary.rows.toLocaleString()}</div>
      </div>
      <div className="card stat">
        <div className="label">Metrics</div>
        <div className="value">{summary.metrics.length}</div>
      </div>
      <div className="card stat">
        <div className="label">Anomalies at |z| ≥ {summary.z_threshold}</div>
        <div className={`value${summary.total_anomalies > 0 ? ' alert' : ''}`}>
          {summary.total_anomalies}
        </div>
      </div>
      <div className="card stat">
        <div className="label">Date range</div>
        <div className="value small">
          {range ? `${fmtDate(range.start)} – ${fmtDate(range.end)}` : '—'}
        </div>
      </div>
    </div>
  )
}

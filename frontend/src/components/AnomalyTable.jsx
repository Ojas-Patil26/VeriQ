const fmtDate = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  })

export default function AnomalyTable({ anomalies, zThreshold }) {
  if (!anomalies.length) {
    return <div className="empty">No anomalies at |z| ≥ {zThreshold}. Try lowering the threshold.</div>
  }
  return (
    <div className="table-wrap">
      <table className="anomalies">
        <thead>
          <tr>
            <th>Date</th>
            <th className="num">Value</th>
            <th className="num">z-score</th>
            <th>Direction</th>
          </tr>
        </thead>
        <tbody>
          {anomalies.map((a) => (
            <tr key={a.date}>
              <td>{fmtDate(a.date)}</td>
              <td className="num">{a.value.toLocaleString()}</td>
              <td className="num">{a.z_score > 0 ? '+' : ''}{a.z_score.toFixed(2)}</td>
              <td>
                <span className="dir-pill">
                  {a.direction === 'high' ? '▲' : '▼'} {a.direction}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

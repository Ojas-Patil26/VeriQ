import { useCallback, useEffect, useState } from 'react'
import TopBar from './components/TopBar'
import HealthCards from './components/HealthCards'
import MetricChart from './components/MetricChart'
import AnomalyTable from './components/AnomalyTable'
import ChatPanel from './components/ChatPanel'
import { getSummary, getTimeseries, getAnomalies, uploadCSV, resetData, reportURL } from './api'

const clamp = (v, lo, hi, fallback) =>
  Number.isFinite(v) ? Math.min(hi, Math.max(lo, v)) : fallback

export default function App() {
  const [summary, setSummary] = useState(null)
  const [metric, setMetric] = useState(null)
  const [windowSize, setWindowSize] = useState(14)
  const [zThreshold, setZThreshold] = useState(2.0)
  const [points, setPoints] = useState([])
  const [anomalies, setAnomalies] = useState([])
  const [refetching, setRefetching] = useState(false)
  const [apiDown, setApiDown] = useState(false)
  const [notice, setNotice] = useState(null)
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID())

  const refreshSummary = useCallback(async () => {
    try {
      const s = await getSummary(windowSize, zThreshold)
      setApiDown(false)
      setSummary(s)
      if (s.status === 'success') {
        setMetric((m) => (m && s.metrics.includes(m) ? m : s.metrics[0] ?? null))
      }
    } catch {
      setApiDown(true)
    }
  }, [windowSize, zThreshold])

  useEffect(() => { refreshSummary() }, [refreshSummary])

  useEffect(() => {
    if (!metric) { setPoints([]); setAnomalies([]); return }
    let cancelled = false
    setRefetching(true)
    Promise.all([
      getTimeseries(metric),
      getAnomalies(metric, windowSize, zThreshold),
    ])
      .then(([ts, an]) => {
        if (cancelled) return
        const anomalyByDate = {}
        if (an.status === 'success') {
          for (const a of an.anomalies) anomalyByDate[a.date] = a
        }
        const merged = ts.status === 'success'
          ? ts.points.map((p) => ({
              ...p,
              anomaly: anomalyByDate[p.date] ?? null,
              anomalyValue: anomalyByDate[p.date]?.value,
            }))
          : []
        setPoints(merged)
        setAnomalies(an.status === 'success' ? an.anomalies : [])
      })
      .catch(() => { if (!cancelled) setApiDown(true) })
      .finally(() => { if (!cancelled) setRefetching(false) })
    return () => { cancelled = true }
  }, [metric, windowSize, zThreshold])

  async function handleUpload(file) {
    setNotice(null)
    try {
      await uploadCSV(file)
      setSessionId(crypto.randomUUID())
      await refreshSummary()
    } catch (err) {
      setNotice(err.message)
    }
  }

  async function handleReset() {
    setNotice(null)
    try {
      await resetData()
      setSessionId(crypto.randomUUID())
      await refreshSummary()
    } catch (err) {
      setNotice(err.message)
    }
  }

  const metrics = summary?.status === 'success' ? summary.metrics : []
  const anomalyCount = anomalies.length

  return (
    <div className="app">
      <TopBar
        source={summary?.status === 'success' ? summary.source : null}
        onUpload={handleUpload}
        onReset={handleReset}
        reportHref={reportURL(windowSize, zThreshold)}
        disabled={apiDown}
      />

      {apiDown && (
        <div className="banner">
          <strong>API unreachable.</strong> Start the backend with{' '}
          <code>python api.py</code> (port 8080) and reload.
        </div>
      )}
      {notice && (
        <div className="banner"><strong>Upload problem.</strong> {notice}</div>
      )}

      <div className="layout">
        <main>
          {summary?.status === 'error' && (
            <div className="card"><div className="empty">{summary.message}</div></div>
          )}

          {metrics.length > 0 && (
            <>
              {/* One filter row scopes everything below it */}
              <div className="filter-row">
                <div className="metric-tabs" role="tablist" aria-label="Metrics">
                  {metrics.map((m) => (
                    <button
                      key={m}
                      role="tab"
                      aria-selected={m === metric}
                      className={`metric-tab${m === metric ? ' active' : ''}`}
                      onClick={() => setMetric(m)}
                    >
                      {m}
                    </button>
                  ))}
                </div>
                <label className="control">
                  Window (days)
                  <input
                    type="number" min="2" max="90" value={windowSize}
                    onChange={(e) => setWindowSize(clamp(e.target.valueAsNumber, 2, 90, 14))}
                  />
                </label>
                <label className="control">
                  z threshold
                  <input
                    type="number" min="0.5" max="10" step="0.5" value={zThreshold}
                    onChange={(e) => setZThreshold(clamp(e.target.valueAsNumber, 0.5, 10, 2.0))}
                  />
                </label>
              </div>

              <HealthCards summary={summary?.status === 'success' ? summary : null} />

              <section className="card chart-card" aria-label={`${metric} time series`}>
                <div className="chart-head">
                  <div>
                    <div className="card-title">{metric}</div>
                    <div className="card-sub">
                      {anomalyCount > 0
                        ? `${anomalyCount} anomal${anomalyCount === 1 ? 'y' : 'ies'} · ${windowSize}-day rolling z-score`
                        : `No anomalies · ${windowSize}-day rolling z-score`}
                    </div>
                  </div>
                  <span className="chart-key">
                    <span className="swatch" /> {metric}
                    <span className="adot" /> anomaly
                  </span>
                </div>
                <MetricChart points={points} refetching={refetching} />
              </section>

              <section className="card" aria-label="Anomaly details">
                <div className="card-title">Anomaly details</div>
                <AnomalyTable anomalies={anomalies} zThreshold={zThreshold} />
              </section>
            </>
          )}

          {summary?.status === 'success' && metrics.length === 0 && (
            <div className="card">
              <div className="empty">
                No numeric metric columns found in this file. Upload a CSV with a
                date column and at least one numeric column, or reset to the sample data.
              </div>
            </div>
          )}
        </main>

        <ChatPanel sessionId={sessionId} metrics={metrics} />
      </div>
    </div>
  )
}

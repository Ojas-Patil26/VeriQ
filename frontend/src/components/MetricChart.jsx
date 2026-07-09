import {
  ComposedChart, Line, Scatter, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

const fmtTick = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

const fmtNum = (v) =>
  Math.abs(v) >= 1000 ? v.toLocaleString(undefined, { maximumFractionDigits: 0 }) : `${v}`

function ChartTip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  if (p.value == null) return null
  return (
    <div className="chart-tip">
      <div className="tip-date">
        {new Date(`${p.date}T00:00:00`).toLocaleDateString(undefined, {
          weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
        })}
      </div>
      <div className="tip-value">{p.value.toLocaleString()}</div>
      {p.anomaly && (
        <div className="tip-anom">
          Anomaly · z = {p.anomaly.z_score > 0 ? '+' : ''}{p.anomaly.z_score.toFixed(2)} ({p.anomaly.direction})
        </div>
      )}
    </div>
  )
}

// Anomaly marker: status red with a 2px surface ring so it stays legible on the line.
function AnomalyDot({ cx, cy, payload }) {
  if (cx == null || cy == null || !payload?.anomaly) return null
  return (
    <circle cx={cx} cy={cy} r={5} fill="var(--critical)" stroke="var(--surface)" strokeWidth={2} />
  )
}

export default function MetricChart({ points, refetching }) {
  return (
    <div className={`chart-body${refetching ? ' refetching' : ''}`}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--grid)" strokeWidth={1} />
          <XAxis
            dataKey="date"
            tickFormatter={fmtTick}
            tick={{ fill: 'var(--muted)', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: 'var(--baseline)' }}
            minTickGap={48}
          />
          <YAxis
            tickFormatter={fmtNum}
            tick={{ fill: 'var(--muted)', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={52}
            domain={['auto', 'auto']}
          />
          <Tooltip content={<ChartTip />} cursor={{ stroke: 'var(--baseline)', strokeWidth: 1 }} />
          <Line
            type="linear"
            dataKey="value"
            stroke="var(--series)"
            strokeWidth={2}
            strokeLinecap="round"
            dot={false}
            activeDot={{ r: 4, fill: 'var(--series)', stroke: 'var(--surface)', strokeWidth: 2 }}
            isAnimationActive={false}
            connectNulls
          />
          <Scatter dataKey="anomalyValue" shape={<AnomalyDot />} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

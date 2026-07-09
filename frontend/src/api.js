// API client. In dev the Vite proxy forwards /api to localhost:8080;
// in production VITE_API_URL points at the deployed backend.
const API = import.meta.env.VITE_API_URL || ''

async function getJSON(path) {
  const res = await fetch(`${API}${path}`)
  if (!res.ok) throw new Error(`Server returned ${res.status}`)
  return res.json()
}

export const getSummary = (window, z) =>
  getJSON(`/api/summary?window=${window}&z=${z}`)

export const getTimeseries = (metric) =>
  getJSON(`/api/timeseries?metric=${encodeURIComponent(metric)}`)

export const getAnomalies = (metric, window, z) =>
  getJSON(
    `/api/anomalies?metric=${encodeURIComponent(metric)}&window=${window}&z=${z}`,
  )

export async function uploadCSV(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API}/api/upload`, { method: 'POST', body: form })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `Upload failed (${res.status})`)
  return data
}

export async function resetData() {
  const res = await fetch(`${API}/api/upload`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Reset failed (${res.status})`)
  return res.json()
}

export const reportURL = (window, z) =>
  `${API}/api/report/pdf?window=${window}&z=${z}`

// Streams the agent's reply. Yields text chunks; throws on server error events.
export async function* chatStream(message, sessionId) {
  const res = await fetch(`${API}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  })
  if (!res.ok) throw new Error(`Server returned ${res.status}`)

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let pending = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    pending += decoder.decode(value, { stream: true })
    // SSE events end with a blank line; hold incomplete events in `pending`.
    const events = pending.split('\n\n')
    pending = events.pop()
    for (const evt of events) {
      for (const line of evt.split('\n')) {
        if (!line.startsWith('data: ')) continue
        const payload = line.slice(6)
        if (payload === '[DONE]') return
        const data = JSON.parse(payload)
        if (data.error) throw new Error(data.error)
        if (data.text) yield data.text
      }
    }
  }
}

import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github.css'
import { chatStream } from '../api'

export default function ChatPanel({ sessionId, metrics }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const logRef = useRef(null)

  useEffect(() => {
    const el = logRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages])

  // New dataset -> new conversation
  useEffect(() => setMessages([]), [sessionId])

  async function send(text) {
    const trimmed = text.trim()
    if (!trimmed || streaming) return
    setInput('')
    setStreaming(true)
    setMessages((m) => [
      ...m,
      { role: 'user', content: trimmed },
      { role: 'assistant', content: '' },
    ])
    try {
      for await (const chunk of chatStream(trimmed, sessionId)) {
        setMessages((m) => {
          const next = m.slice()
          const last = next[next.length - 1]
          next[next.length - 1] = { ...last, content: last.content + chunk }
          return next
        })
      }
    } catch (err) {
      setMessages((m) => {
        const next = m.slice()
        next[next.length - 1] = { role: 'assistant', error: true, content: `Error: ${err.message}` }
        return next
      })
    }
    setStreaming(false)
  }

  const suggestions = [
    'What metrics are available?',
    metrics?.length ? `Check ${metrics[0]} for anomalies` : null,
    metrics?.length ? `Why might ${metrics[0]} have anomalies?` : null,
    'Write an incident report for the issues you found',
  ].filter(Boolean)

  return (
    <section className="card chat-panel" aria-label="Assistant">
      <div className="chat-head">
        <div className="card-title">Assistant</div>
        <div className="card-sub">Five agents: catalog, anomaly detection, root cause, incident reports</div>
      </div>

      <div className="chat-log" ref={logRef}>
        {messages.length === 0 && (
          <div className="suggestions">
            {suggestions.map((s) => (
              <button key={s} className="suggestion" onClick={() => send(s)}>{s}</button>
            ))}
          </div>
        )}
        {messages.map((msg, i) =>
          msg.role === 'user' ? (
            <div key={i} className="msg user">{msg.content}</div>
          ) : (
            <div key={i} className={`msg assistant${msg.error ? ' error' : ''}`}>
              {msg.content === '' && streaming && i === messages.length - 1 ? (
                <span className="typing"><span /><span /><span /></span>
              ) : msg.error ? (
                msg.content
              ) : (
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                  {msg.content}
                </ReactMarkdown>
              )}
            </div>
          ),
        )}
      </div>

      <div className="chat-input">
        <textarea
          rows={1}
          placeholder="Ask about your data quality…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send(input)
            }
          }}
        />
        <button className="btn primary" onClick={() => send(input)} disabled={streaming || !input.trim()}>
          Send
        </button>
      </div>
    </section>
  )
}

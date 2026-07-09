import { useRef } from 'react'

export default function TopBar({ source, onUpload, onReset, reportHref, disabled }) {
  const fileRef = useRef(null)

  return (
    <header className="topbar">
      <div className="brand">
        <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
          <rect width="32" height="32" rx="7" fill="#2a78d6" />
          <polyline
            points="6,20 12,20 15,10 19,24 22,16 26,16"
            fill="none" stroke="#fff" strokeWidth="2.5"
            strokeLinecap="round" strokeLinejoin="round"
          />
        </svg>
        <div>
          <div className="brand-name">VeriQ</div>
          <div className="brand-tag">Data quality monitor</div>
        </div>
      </div>

      {source && (
        <span className={`source-badge${source.is_sample ? '' : ' uploaded'}`} title={source.name}>
          <span className="dot" />
          {source.is_sample ? 'Sample dataset' : source.name}
        </span>
      )}

      <input
        ref={fileRef}
        type="file"
        accept=".csv"
        hidden
        onChange={(e) => {
          const file = e.target.files[0]
          if (file) onUpload(file)
          e.target.value = ''
        }}
      />
      <button className="btn primary" onClick={() => fileRef.current.click()} disabled={disabled}>
        Upload CSV
      </button>
      {source && !source.is_sample && (
        <button className="btn" onClick={onReset}>Reset to sample</button>
      )}
      <a className="btn" href={reportHref} download aria-disabled={disabled}>
        Download PDF report
      </a>
    </header>
  )
}

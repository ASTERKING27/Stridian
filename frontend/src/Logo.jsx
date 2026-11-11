// The Stridian lockup: the S-runner mark in ink (never the accent) and the wide, tracked
// wordmark, exactly as the phone app draws them.
export const MARK = 'M8.0 52.3L58.8 58.1L27.1 83.3L4.7 78.8L4.2 79.2L28.6 94.7L97.0 47.9L27.7 39.6L32.0 24.0L53.0 20.7L68.6 7.6L22.6 12.9ZM81.8 16.0L88.0 25.3L88.7 24.6L88.5 5.3L72.9 7.1L57.6 19.9Z'

export function Mark({ size = 30 }) {
  return (
    <svg className="logo-mark" viewBox="0 0 100 100" width={size} height={size} aria-hidden="true">
      <path d={MARK} />
    </svg>
  )
}

export default function Logo({ size = 30, onClick, label = 'Stridian home' }) {
  const inner = <><Mark size={size} /><span className="wm" style={{ fontSize: Math.round(size * 0.54) }}>STRIDIAN</span></>
  return onClick
    ? <a className="logo" href="#" aria-label={label} onClick={e => { e.preventDefault(); onClick() }}>{inner}</a>
    : <span className="logo">{inner}</span>
}

// Small stroked icon set. An icon library would be a dependency; a dozen paths are not.
const PATHS = {
  student: 'M12 3 2 8l10 5 10-5-10-5ZM5 11v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5',
  clipboard: 'M9 4h6M9 4a2 2 0 0 0-2 2v0H6a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-1v0a2 2 0 0 0-2-2M8 12h8M8 16h5',
  chart: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  sliders: 'M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0M14 4v4M8 10v4M16 16v4',
  logout: 'M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 16l-4-4 4-4M6 12h10',
  film: 'M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6ZM3 10h18M3 15h18M8 4v16M16 4v16',
  back: 'M15 18l-6-6 6-6',
  card: 'M5 3h10l4 4v14H5V3ZM15 3v4h4M8 11h8M8 15h8M8 19h5',
  plus: 'M12 5v14M5 12h14',
  cpu: 'M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3M7 6h10a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1ZM10 10h4v4h-4Z',
  // the second coach's messages and milestones (backend/coach.py names them)
  shield: 'M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z',
  check: 'M5 12.5 10 17 19 7',
  medal: 'M8 3h8l-2 6h-4L8 3Zm4 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12Zm0 3 1.2 2.4 2.6.4-1.9 1.8.5 2.6-2.4-1.3-2.4 1.3.5-2.6-1.9-1.8 2.6-.4L12 12Z',
  star: 'M12 3.5 14.6 9l6 .6-4.5 4 1.3 6-5.4-3.2L6.6 19.6l1.3-6-4.5-4 6-.6L12 3.5Z',
  trend: 'M3 17 9 11l4 4 8-8M15 7h6v6',
  down: 'M3 7l6 6 4-4 8 8M15 17h6v-6',
  l1: 'M6 20V14M12 20V9M18 20V4',
  l2: 'M4 20h16M7 20v-6h3v6M14 20V9h3v11',
  l3: 'M12 3l2.5 5 5.5.8-4 3.9.9 5.5-4.9-2.6-4.9 2.6.9-5.5-4-3.9L9.5 8 12 3Z',
  bolt: 'M13 2 4 14h7l-1 8 9-12h-7l1-8Z',
  flame: 'M12 3c1 3.5 5 5.5 5 10a5 5 0 0 1-10 0c0-2 1-3.5 2-4.5 0 2 1 3 2 3 0-3-1-5.5 1-8.5Z',
  whistle: 'M3 10h10a5 5 0 1 1-5 5V10M13 10l7-3',
  target: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-4a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0-4a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z',
  // the four "dots" are zero-length strokes: round caps draw them as dots
  palette: 'M12 3a9 9 0 1 0 0 18c1 0 1.8-.8 1.8-1.8 0-.5-.2-.9-.5-1.2-.3-.3-.5-.7-.5-1.2 0-1 .8-1.8 1.8-1.8H17a4 4 0 0 0 4-4c0-4.4-4-8-9-8ZM7.5 11.5h.01M9.5 7.5h.01M14.5 7.5h.01M16.5 11h.01',
}

export default function Icon({ name, size = 17 }) {
  const d = PATHS[name]
  if (!d) return null
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
         stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"
         aria-hidden="true">
      <path d={d} />
    </svg>
  )
}

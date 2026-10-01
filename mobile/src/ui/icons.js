// The Stridian icon set (design: code/icons.py) — 24 grid, 1.6 stroke, butt ends, mitred.
export const LOGO_D = 'M8.0 52.3L58.8 58.1L27.1 83.3L4.7 78.8L4.2 79.2L28.6 94.7L97.0 47.9L27.7 39.6L32.0 24.0L53.0 20.7L68.6 7.6L22.6 12.9ZM81.8 16.0L88.0 25.3L88.7 24.6L88.5 5.3L72.9 7.1L57.6 19.9Z'

// the logo is straight lines only, so its outline length is a sum of segments
export const LOGO_LEN = (() => {
  let total = 0
  for (const sub of LOGO_D.split('M').filter(Boolean)) {
    const pts = sub.replace('Z', '').split('L').map(p => p.trim().split(' ').map(Number))
    pts.push(pts[0])
    for (let i = 1; i < pts.length; i++) total += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
  }
  return total
})()

export const SPORT_ICONS = {
  Football: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 8l3.8 2.8-1.5 4.4H9.7l-1.5-4.4L12 8ZM12 8V3M15.8 10.8l4.4-1.5M14.3 15.2l2.8 3.9M9.7 15.2l-2.8 3.9M8.2 10.8 3.8 9.3',
  Basketball: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM3 12h18M12 3v18M5.6 5.6c2.4 2.4 2.4 10.4 0 12.8M18.4 5.6c-2.4 2.4-2.4 10.4 0 12.8',
  Volleyball: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 12c0-4 2-7 5.2-8.2M12 12c-3.5 2-7 2.3-9 1M12 12c3.5 2 5.4 5 5.7 7.7',
  Cricket: 'M15 3.8 20.2 9 11 18.2 5.8 13 15 3.8ZM8.4 15.6 3.5 20.5M6.5 8.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z',
  Badminton: 'M9 17h6v1.5a3 3 0 0 1-6 0V17ZM9 17 5 4M15 17l4-13M12 17V4M5 4h14M6.7 9.5h10.6',
  Tennis: 'M14 15a6 6 0 1 0 0-12 6 6 0 0 0 0 12ZM9.8 13.2 3.5 19.5M11 6.5l6 5M11 11l5.5-5M19.5 21a1.8 1.8 0 1 0 0-3.6 1.8 1.8 0 0 0 0 3.6Z',
  'Kho-Kho': 'M4 3v18M20 3v18M2 21h4M18 21h4M7 15l3-3 3 3 3-3M14 9h3v3',
}

export const I = {
  dashboard: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-4a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0-4a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z',
  report: 'M5 3h10l4 4v14H5V3ZM15 3v4h4M8 11h8M8 15h8M8 19h5',
  achievements: 'M8 3h8l-2 6h-4L8 3Zm4 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12Z',
  profile: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4.5 20.5c.8-3.6 3.8-6 7.5-6s6.7 2.4 7.5 6',
  entry: 'M9 4h6M9 4a2 2 0 0 0-2 2H6a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-1a2 2 0 0 0-2-2M8 12h8M8 16h5',
  footage: 'M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6ZM3 10h18M3 15h18M8 4v16M16 4v16',
  squad: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  weights: 'M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M14 4v4M8 10v4M16 16v4',
  ai: 'M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3M7 6h10a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1ZM10 10h4v4h-4Z',
  add: 'M12 5v14M5 12h14',
  back: 'M15 18l-6-6 6-6',
  next: 'M9 6l6 6-6 6',
  close: 'M6 6l12 12M18 6 6 18',
  check: 'M5 12.5 10 17 19 7',
  search: 'M10.5 17a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13ZM15.5 15.5 20 20',
  filter: 'M3 5h18l-7 8v6l-4 2v-8L3 5Z',
  edit: 'M4 20h4L19 9l-4-4L4 16v4ZM13 7l4 4',
  delete: 'M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14M10 11v6M14 11v6',
  upload: 'M12 16V4M7 9l5-5 5 5M4 15v5h16v-5',
  download: 'M12 4v12M7 11l5 5 5-5M4 15v5h16v-5',
  share: 'M12 3v12M7 8l5-5 5 5M5 12v9h14v-9',
  camera: 'M4 8h3l2-3h6l2 3h3v11H4V8Zm8 9a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z',
  gallery: 'M4 5h16v14H4V5Zm0 10 5-5 4 4 3-3 4 4M15.5 9.5h.01',
  bell: 'M6 17V11a6 6 0 1 1 12 0v6l2 2H4l2-2ZM10 21h4',
  calendar: 'M4 5h16v16H4V5ZM4 10h16M8 3v4M16 3v4',
  lock: 'M6 11h12v10H6V11ZM8.5 11V7.5a3.5 3.5 0 0 1 7 0V11',
  show: 'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Zm10 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z',
  settings: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM10 2h4l.7 3 2.6 1.5 2.9-1 2 3.5-2.2 2v3l2.2 2-2 3.5-2.9-1-2.6 1.5-.7 3h-4l-.7-3-2.6-1.5-2.9 1-2-3.5 2.2-2v-3l-2.2-2 2-3.5 2.9 1L9.3 5 10 2Z',
  light: 'M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9 7 7M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1',
  dark: 'M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z',
  motion: 'M3 8h6M5 12h6M3 16h6M13 6l6 6-6 6',
  signout: 'M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 16l-4-4 4-4M6 12h10',
  info: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 11v6M12 7.5v.5',
  warning: 'M12 3 2 21h20L12 3ZM12 10v5M12 17.5v.5',
  retry: 'M4 12a8 8 0 0 1 14-5.3M20 4v4h-4M20 12a8 8 0 0 1-14 5.3M4 20v-4h4',
  offline: 'M2 8.5a15 15 0 0 1 20 0M5.5 12a10 10 0 0 1 13 0M9 15.5a5 5 0 0 1 6 0M12 19h.01M3 3l18 18',
  verified: 'M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3ZM8.5 12l2.5 2.5 4.5-5',
  streak: 'M12 3c1 3.5 5 5.5 5 10a5 5 0 0 1-10 0c0-2 1-3.5 2-4.5 0 2 1 3 2 3 0-3-1-5.5 1-8.5Z',
  levelup: 'M3 17 9 11l4 4 8-8M15 7h6v6',
  whistle: 'M3 10h10a5 5 0 1 1-5 5V10M13 10l7-3',
  student: 'M12 3 2 8l10 5 10-5-10-5ZM5 11v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5',
}

// the badges' glyphs (backend coach.py BADGES names them)
export const BADGE_ICONS = {
  clipboard: 'M9 4h6M9 4a2 2 0 0 0-2 2H6a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-1a2 2 0 0 0-2-2M8 12h8M8 16h5',
  shield: 'M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z',
  student: 'M12 3 2 8l10 5 10-5-10-5ZM5 11v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5',
  card: 'M5 3h10l4 4v14H5V3ZM15 3v4h4M8 11h8M8 15h8M8 19h5',
  whistle: 'M3 10h10a5 5 0 1 1-5 5V10M13 10l7-3',
  l1: 'M6 20V14M12 20V9M18 20V4',
  l2: 'M4 20h16M7 20v-6h3v6M14 20V9h3v11',
  l3: 'M12 3l2.5 5 5.5.8-4 3.9.9 5.5-4.9-2.6-4.9 2.6.9-5.5-4-3.9L9.5 8 12 3Z',
  trend: 'M3 17 9 11l4 4 8-8M15 7h6v6',
  target: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-4a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0-4a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z',
  flame: 'M12 3c1 3.5 5 5.5 5 10a5 5 0 0 1-10 0c0-2 1-3.5 2-4.5 0 2 1 3 2 3 0-3-1-5.5 1-8.5Z',
  bolt: 'M13 2 4 14h7l-1 8 9-12h-7l1-8Z',
  medal: 'M8 3h8l-2 6h-4L8 3Zm4 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12Zm0 3 1.2 2.4 2.6.4-1.9 1.8.5 2.6-2.4-1.3-2.4 1.3.5-2.6-1.9-1.8 2.6-.4L12 12Z',
}

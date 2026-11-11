/* What the document AI read off a photo of a match card, folded into the card as the
   website's editor does it — then sent back as a draft for the coach to check. Nothing
   here imports the app, so scripts/check.mjs can run it.

   A cell the AI couldn't read comes back null; it is saved as 0 and counted, so the
   phone can say how many to check against the paper. */
export function mergeReading(card, reading) {
  const header = { ...card.header }
  for (const [k, v] of Object.entries(reading.header ?? {})) {
    if (k === 'score') {
      const now = header.score ?? []
      // a part of the score already typed in stays; an empty one takes the reading
      header.score = v.map((pair, i) => (now[i]?.some(x => x != null) ? now[i] : pair)).concat(now.slice(v.length))
    } else if (v != null && v !== '' && !header[k]) {
      header[k] = v
    }
  }
  const lines = card.lines.map(({ id, ...l }) => ({ ...l, tallies: { ...l.tallies }, fields: { ...l.fields } }))
  let unread = 0
  for (const p of reading.players) {
    unread += Object.values(p.tallies).flat().filter(x => x == null).length
    const tallies = Object.fromEntries(Object.entries(p.tallies).map(([k, v]) => [k, v.map(x => x ?? 0)]))
    const fields = Object.fromEntries(Object.entries(p.fields).filter(([, v]) => v != null))
    const same = lines.find(l => (p.student_id ? l.student_id === p.student_id
      : !l.student_id && l.jersey != null && l.jersey === p.jersey))
    if (same) {
      Object.assign(same.tallies, tallies)
      Object.assign(same.fields, fields)
    } else {
      lines.push({ student_id: p.student_id ?? null, jersey: p.jersey ?? null, name: p.name ?? null, position: null,
                   tallies, fields, zones: {}, coord: null, overall: null, strength: null, improve: null, remarks: null })
    }
  }
  return {
    body: { category: reading.category && !card.lines.length ? reading.category : card.category, format: card.format,
            header, team: card.team, lines, final: false },
    players: reading.players.length,
    unmatched: reading.players.filter(p => !p.student_id).length,
    unread,
  }
}

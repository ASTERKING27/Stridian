import assert from 'node:assert'
import { measure } from '../src/lib/pose.js'
import { check, parseValue } from '../src/lib/entry.js'
import { changes, shares, toDraft, unfinished } from '../src/lib/weights.js'
import { mergeReading } from '../src/lib/cards.js'
import { formatValue } from '../src/lib/format.js'

/* The app's pure logic, checked without a phone:  node scripts/check.mjs  (Node 22+). */

// --- pose: a side-on countermovement jump, frame by frame
const J = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
// a side-on countermovement jump: stand, squat (hips drop, knee bends), fly (hips rise), land
const frame = (hipY, kneeBend, lift) => {
  const pts = {}
  for (const j of J) pts[j] = [0.5, 0.5]
  const hip = [0.5, hipY], knee = [0.5 + kneeBend, hipY + 0.2 - lift * 0], ankle = [0.5, 0.9 - lift]
  Object.assign(pts, { 0: [0.5, hipY - 0.35], 11: [0.5, hipY - 0.28], 12: [0.5, hipY - 0.28], 23: hip, 24: hip,
    25: [0.5 + kneeBend, (hipY + 0.9 - lift) / 2], 26: [0.5 + kneeBend, (hipY + 0.9 - lift) / 2], 27: ankle, 28: ankle })
  return J.flatMap(j => pts[j])
}
const seq = [...Array(10).fill(0).map(() => frame(0.5, 0, 0)),
  frame(0.55, 0.05, 0), frame(0.6, 0.1, 0), frame(0.65, 0.15, 0), frame(0.6, 0.1, 0), frame(0.5, 0.02, 0),
  frame(0.4, 0, 0.1), frame(0.32, 0, 0.18), frame(0.4, 0, 0.1), frame(0.5, 0, 0), null, frame(0.5, 0, 0)]
const m = measure({ fps: 10, aspect: 1, near: 'left', frames: seq })
assert.equal(m.frames.length, 21)
assert.equal(m.knee[0], 180)                                   // standing straight
assert.ok(m.knee[12] < 120, m.knee[12])                         // deepest squat bends the knee
assert.equal(m.phase[0], 'STANDING')
assert.equal(m.phase[11], 'LOADING')
assert.equal(m.phase[16], 'IN THE AIR')
assert.equal(m.stills[0].f, 12)                                 // loading = deepest knee bend
assert.equal(m.stills[2].f, 16)                                 // peak = highest hips
assert.equal(m.ticks.length, 16)
assert.equal(m.frames[19], null)

// --- coach entry: typed results
const sprint = { key: 'sprint30m', unit: 'sec', poor: 5.2, elite: 3.9 }
const trial = { key: 'timeTrial2km', unit: 'sec', poor: 600, elite: 450 }
assert.equal(parseValue(''), null)
assert.equal(parseValue('8:30'), 510)
assert.equal(parseValue('4,38'), 4.38)
assert.ok(Number.isNaN(parseValue('8:75')))
assert.equal(check(sprint, '4.38'), null)
assert.equal(check(sprint, '').kind, 'blank')
assert.equal(check(sprint, '', { skipped: true }), null)
assert.equal(check(sprint, 'abc').kind, 'nan')
assert.equal(check(sprint, '38').fix, '3.8')                    // the slipped decimal point
assert.equal(check(sprint, '38', { kept: true }), null)
assert.equal(check(trial, '8:30'), null)
assert.equal(formatValue(599.6, trial), '10:00')

// --- weights: whole percentages per source, only changed groups sent back
const metrics = [{ key: 'a', source: 'test' }, { key: 'b', source: 'test' }, { key: 'c', source: 'profile' },
                 { key: 'm1', source: 'match' }, { key: 'm2', source: 'match' }, { key: 'm3', source: 'match' }]
assert.deepEqual(shares({ m1: 1, m2: 1, m3: 1 }, ['m1', 'm2', 'm3']), { m1: 34, m2: 33, m3: 33 })
const draft = toDraft({ Winger: { a: 0.4, b: 0.3, c: 0.3, m1: 0.133, m2: 0.133, m3: 0.134 } }, metrics)
assert.deepEqual(draft.Winger.test, { a: 40, b: 30, c: 30 })
assert.equal(Object.values(draft.Winger.match).reduce((x, y) => x + y), 100)
const edited = { Winger: { ...draft.Winger, test: { a: 50, b: 30, c: 20 } } }
assert.deepEqual(changes(edited, draft), { Winger: { a: 0.5, b: 0.3, c: 0.2 } })
assert.deepEqual(unfinished({ Winger: { ...draft.Winger, test: { a: 50, b: 30, c: 30 } } }, draft), [['Winger', 'test', 110]])

// --- match cards: an AI reading folded into the card
const card = { category: 'M', format: null, team: {}, header: { tournament: 'Inter-dept', score: [[2, null]] },
               lines: [{ id: 9, student_id: 1, jersey: 7, name: 'Aarav', tallies: { passing: [1, 0, 0] }, fields: {} }] }
const merged = mergeReading(card, {
  header: { tournament: 'Wrong', opponent: 'ECE', score: [[3, 1]] }, category: 'W',
  players: [{ student_id: 1, jersey: 7, tallies: { passing: [4, null, 1] }, fields: {} },
            { student_id: null, jersey: 11, name: 'R. Das', tallies: { chance: [1, 0, 0] }, fields: { minutes: null } }],
})
assert.equal(merged.body.header.tournament, 'Inter-dept')         // what's typed stays
assert.equal(merged.body.header.opponent, 'ECE')                  // what's empty is filled
assert.deepEqual(merged.body.header.score, [[2, null]])
assert.equal(merged.body.category, 'M')                           // players already on it: the team stays
assert.deepEqual(merged.body.lines[0].tallies.passing, [4, 0, 1])
assert.equal(merged.body.lines[0].id, undefined)
assert.equal(merged.body.lines.length, 2)
assert.deepEqual([merged.unread, merged.unmatched, merged.body.final], [1, 1, false])
assert.deepEqual(card.lines[0].tallies.passing, [1, 0, 0])        // the card itself is untouched

console.log('logic: ok')

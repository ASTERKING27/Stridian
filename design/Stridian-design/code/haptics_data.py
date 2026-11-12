# Stridian haptics plan — shared data for both boards.
# Times are ms from the start of each animation, taken from the canvas boards' own timelines.

# ---------- rich tier vocabulary: (name, events, duration_ms, iphone, android, used_for)
# events: ('t', time, intensity) transient · ('c', start, end, i0, i1, curve) continuous
def dive_pts():
    return ('c', 0, 850, .2, .85, 'accel')

RICH_VOCAB = [
  ('Spark', [('t', 20, .5)], 120, 'Transient · intensity 0.3–0.6 · sharpness 0.9–1.0', 'PRIMITIVE_TICK · scale 0.3–0.6', 'Every spark that flies off the logo, a badge or a counter'),
  ('Crackle', [('t', x, i) for x, i in [(10, .3), (120, .4), (190, .25), (300, .45), (370, .35), (460, .5), (520, .3), (590, .55), (650, .4), (710, .6), (760, .45), (820, .6), (870, .5)]], 900,
     '13 Sparks, 50–120 ms apart, denser and stronger towards the end', '7 × PRIMITIVE_TICK, ≥ 90 ms apart, scale 0.3 → 0.5', 'Launch: sparks flying out of the logo'),
  ('Charge', [('c', 0, 560, .08, .35, 'lin')], 600, 'Continuous · intensity 0.08 → 0.35 · sharpness 0.25 → 0.55', 'PRIMITIVE_SLOW_RISE · scale 0.35', 'Launch: the logo building up before it fires'),
  ('Ignite', [('t', 140, 1.0)], 300, 'Transient · intensity 1.0 · sharpness 0.35 — after 140 ms of silence', 'PRIMITIVE_THUD · scale 1.0 (else EFFECT_HEAVY_CLICK)', 'Launch: the logo turns into the huge spark'),
  ('Dive', [dive_pts()], 900, 'Continuous · intensity 0.2 → 0.85 on an accelerating curve · sharpness 0.3 → 0.9 · cut dead at the end', 'PRIMITIVE_SLOW_RISE 0.55, then PRIMITIVE_QUICK_RISE 1.0', 'Launch: the “S” zooming in to fill the screen'),
  ('Land', [('t', 20, .45)], 150, 'Transient · intensity 0.45 · sharpness 0.55', 'PRIMITIVE_CLICK · scale 0.5', 'Launch: arriving inside the app'),
  ('Tick', [('t', 20, .28)], 120, 'UISelectionFeedbackGenerator', 'SEGMENT_TICK (Android 14+) · else CLOCK_TICK', 'Tabs, chips, segments, slider steps, count-up steps, scrub stills'),
  ('Tap', [('t', 20, .5)], 120, 'UIImpactFeedbackGenerator .rigid · intensity 0.5 · on touch-down', 'VIRTUAL_KEY', 'Primary buttons that commit something'),
  ('Sweep', [('t', 20, .3), ('t', 80, .2), ('t', 140, .12)], 200, '3 transients · 0.3 / 0.2 / 0.12 · sharpness 0.8 · 60 ms apart', 'PRIMITIVE_TICK × 3 · 0.3 / 0.2 / 0.12', 'The diagonal lines crossing on a tab change or a card'),
  ('Snap', [('t', 20, .8)], 150, 'UIImpactFeedbackGenerator .rigid · intensity 0.8', 'GESTURE_THRESHOLD_ACTIVATE (14+) · else CLICK 0.7', 'Pull-to-refresh armed · weights reach exactly 100%'),
  ('Stamp', [('t', 20 + i * 55, .35 + i * .05) for i in range(5)], 300, '5 transients · 0.35 → 0.55 · sharpness 0.85 · one per letter', 'PRIMITIVE_TICK × 5 · 0.35 → 0.55', 'Level name letters landing: S · T · A · T · E'),
  ('Rise', [('c', 0, 500, .1, .5, 'lin')], 520, 'Continuous · intensity 0.1 → 0.5 · sharpness 0.4 → 0.7 · as long as the fill', 'PRIMITIVE_SLOW_RISE · scale 0.45', 'Ladder, badge, week-bar and restored-gap fills'),
  ('Draw', [('c', 0, 420, .12, .12, 'lin')], 450, 'Continuous · intensity 0.12 · sharpness 0.7 · while the outline draws', 'PRIMITIVE_LOW_TICK · scale 0.3', 'A badge outline drawing itself'),
  ('Refresh', [('t', 20, .5), ('t', 110, .3)], 180, '2 transients · 0.5 then 0.3 · sharpness 0.5 · 90 ms apart', 'PRIMITIVE_CLICK 0.5 + PRIMITIVE_TICK 0.35', 'The black-and-white flash when a refresh lands'),
  ('Fall', [('c', 0, 600, .4, 0, 'lin')], 620, 'Continuous · intensity 0.4 → 0 · sharpness 0.6 → 0.2', 'PRIMITIVE_QUICK_FALL · scale 0.5', 'Streak broken: the count dropping to 0 — soft, never harsh'),
  ('Success', [('t', 20, .45), ('t', 130, .75)], 200, 'UINotificationFeedbackGenerator .success', 'CONFIRM (Android 11+)', 'Saved, verified, assigned, uploaded, levels, badges, streaks'),
  ('Warning', [('t', 20, .5), ('t', 110, .5)], 180, 'UINotificationFeedbackGenerator .warning', 'PRIMITIVE_TICK 0.5 × 2 · 80 ms apart', 'Streak about to break (once a day) · a retry that failed'),
  ('Error', [('t', 20, .6), ('t', 90, .6), ('t', 160, .8)], 220, 'UINotificationFeedbackGenerator .error', 'REJECT (Android 11+)', 'Validation failed, upload failed, wrong code'),
  ('Toggle', [('t', 20, .45), ('t', 130, .22)], 180, 'On: impact .light · Off: impact .soft 0.5', 'TOGGLE_ON / TOGGLE_OFF (14+) · else CLOCK_TICK', 'Switches in Settings'),
  ('Nope', [('t', 20, .3), ('t', 90, .3)], 150, '2 transients · 0.3 · sharpness 0.6 · 70 ms apart', 'PRIMITIVE_TICK 0.35 × 2', 'Tapping a disabled button'),
]

# ---------- launch timeline (from the Launch board: sparks 400–1360, charge 820–1380,
# squash 1380–1520, ignite 1520, zoom 1520–2420, tab bar 2200–2720)
LAUNCH_PHASES = [  # (label, start, end, lane)
  ('Icon grows', 0, 360, 0), ('Sparks fly out', 400, 1360, 0), ('Squash', 1380, 1520, 1), ('“S” zooms in', 1520, 2420, 0),
  ('Charge', 820, 1380, 1), ('Tab bar rises', 2200, 2720, 1)]
LAUNCH_IOS = ([('t', x, i) for x, i in [(430, .30), (540, .40), (610, .25), (720, .45), (790, .35), (880, .5), (940, .3), (1010, .55), (1070, .4), (1130, .6), (1180, .45), (1240, .6), (1290, .5)]]
  + [('c', 820, 1380, .08, .35, 'lin'), ('t', 1520, 1.0), ('t', 1535, .55), ('t', 1560, .45), ('t', 1590, .35),
     ('c', 1560, 2400, .2, .85, 'accel'), ('t', 2420, .45), ('t', 2680, .18)])
LAUNCH_ANDROID = [  # (primitive, time, scale, length-for-drawing)
  ('TICK', 430, .30, 0), ('TICK', 560, .40, 0), ('TICK', 680, .30, 0), ('TICK', 790, .45, 0), ('TICK', 900, .40, 0), ('TICK', 1000, .50, 0), ('TICK', 1090, .45, 0),
  ('SLOW_RISE', 1140, .35, 240), ('THUD', 1520, 1.0, 0), ('TICK', 1570, .5, 0), ('SLOW_RISE', 1620, .55, 520), ('QUICK_RISE', 2200, 1.0, 200),
  ('CLICK', 2420, .5, 0), ('LOW_TICK', 2680, .2, 0)]
LAUNCH_LABELS_IOS = [(430, 'Crackle — 13 sparks'), (820, 'Charge'), (1450, 'silence'), (1520, 'Ignite + 3 sparks'), (1900, 'Dive — accelerating'), (2420, 'Land'), (2680, 'Settle')]

# ---------- level-reached timeline (Achievement board). One change asked of the animation:
# count-up starts at 1400 ms instead of 1250 so its ticks don't pile onto the letter stamps.
LEVEL_PHASES = [('Card sweeps in', 180, 900, 0), ('Logo pops', 760, 1120, 1), ('S T A T E rise', 900, 1500, 0), ('4.38 → 4.33', 1400, 2100, 1), ('Ladder fills', 1750, 2070, 0), ('Details', 2080, 2400, 0)]
LEVEL_IOS = ([('t', 480, .3), ('t', 540, .2), ('t', 600, .12), ('t', 820, .6), ('t', 850, .45), ('t', 885, .35)]
  + [('t', 1100 + i * 55, .35 + i * .05) for i in range(5)]
  + [('t', x, .28) for x in (1424, 1478, 1544, 1631, 1775)]
  + [('c', 1790, 2070, .1, .5, 'lin'), ('t', 2070, .45), ('t', 2180, .75), ('t', 2240, .4), ('t', 2280, .3)])
LEVEL_LABELS = [(480, 'Sweep'), (820, 'Pop + sparks'), (1100, 'Stamp × 5'), (1424, 'Tick per step'), (1790, 'Rise'), (2070, 'Success + sparks')]

# ---------- placement table: (moment, when, rich pattern, iPhone call, Android call, budget)
PLACEMENT = [
  ('NAVIGATION AND REFRESH', [
    ('Tab tapped', 'touch-down', 'Tick', 'selection', 'SEGMENT_TICK', 'Tick'),
    ('Tab change — lines cross', '300–420 ms', 'Sweep', '3 transients', 'TICK × 3', '—'),
    ('Pull — outline drawing', 'every 25% of the pull', 'Tick', 'selection', 'SEGMENT_FREQUENT_TICK', '—'),
    ('Pull — past the release point', 'as the logo fills', 'Snap', 'impact .rigid 0.8', 'GESTURE_THRESHOLD_ACTIVATE', 'Tap'),
    ('Pull — back under it', 'as it empties', 'soft', 'impact .soft 0.4', 'GESTURE_THRESHOLD_DEACTIVATE', '—'),
    ('Refresh lands', 'with the flash', 'Refresh', '2 transients', 'CLICK + TICK', 'Pulse'),
    ('Back, close, scrolling', '—', 'none', '—', '—', '—'),
  ]),
  ('BUTTONS AND CONTROLS', [
    ('Primary button (Save, Assign, Add…)', 'touch-down', 'Tap', 'impact .rigid 0.5', 'VIRTUAL_KEY', 'Tap'),
    ('Secondary and text buttons', '—', 'none', '—', '—', '—'),
    ('Disabled button tapped', 'on tap', 'Nope', '2 transients', 'TICK × 2', '—'),
    ('Switch on / off', 'as the knob lands', 'Toggle', 'impact .light / .soft', 'TOGGLE_ON / TOGGLE_OFF', 'Tap (on only)'),
    ('Chips, segments, filters, pickers', 'on select', 'Tick', 'selection', 'SEGMENT_TICK', 'Tick'),
    ('Weight slider', 'each 5% step', 'Tick', 'selection', 'SEGMENT_TICK', '—'),
    ('Weights reach exactly 100%', 'when the total hits 100', 'Snap', 'impact .rigid 0.8', 'CLICK 0.7', 'Tap'),
    ('Undo on a toast', 'on tap', 'Tap', 'impact .light', 'CLOCK_TICK', '—'),
    ('Theme switched', 'as the screen flips', 'Tap', 'impact .medium', 'CLICK 0.6', 'Tap'),
  ]),
  ('CONFIRMATIONS AND ERRORS', [
    ('Saved · verified · assigned', 'when the tick finishes drawing', 'Success', '.success', 'CONFIRM', 'Confirm'),
    ('Save blocked by errors', 'as the error summary appears', 'Error', '.error', 'REJECT', 'Reject'),
    ('Upload finished', 'at 100%', 'Success', '.success', 'CONFIRM', 'Confirm'),
    ('Upload failed', 'as the error shows', 'Error', '.error', 'REJECT', 'Reject'),
    ('Retry failed (server down)', 'only after the user tapped Retry', 'Warning', '.warning', 'TICK × 2', '—'),
    ('Offline bar, empty states, loading', '—', 'none', '—', '—', '—'),
  ]),
  ('ACHIEVEMENTS', [
    ('Level reached', 'see the timeline', 'Sweep → Spark → Stamp → Tick → Rise → Success', 'one AHAP file', 'one Composition', 'Pulse at pop · Confirm at end'),
    ('Badge — outline draws', '0–420 ms', 'Draw', 'continuous 0.12', 'LOW_TICK 0.3', '—'),
    ('Badge — ink fills', '300–750 ms', 'Rise', 'continuous ramp', 'SLOW_RISE 0.45', '—'),
    ('Badge — icon pops, sparks', '600 / 700 ms', 'Tap + 3 Sparks', 'transients', 'CLICK 0.6 + TICK × 3', 'Confirm at 600'),
  ]),
  ('FOCUS STREAK', [
    ('Session ticked off', 'on tap', 'Tap', 'impact .medium', 'CLICK 0.7', 'Tap'),
    ('Week bar fills', '1000–1520 ms', 'Rise', 'continuous ramp', 'SLOW_RISE 0.45', '—'),
    ('Counter rolls up', 'lands ≈ 1950 · done 2060', 'Tap + Success', '.rigid 0.5 + .success', 'CLICK 0.5 + CONFIRM', 'Confirm'),
    ('About to break', 'first open that day only', 'Warning', '.warning', 'TICK × 2', 'Pulse'),
    ('Broken', 'as 4 drops to 0', 'Fall', 'continuous fade', 'QUICK_FALL 0.5', '—'),
    ('Restored', 'fill 600 · roll 1850 · sparks 1800', 'Rise → Tap → Success', 'one AHAP file', 'one Composition', 'Confirm'),
  ]),
  ('VIDEO AND COACH', [
    ('Record · choose from gallery', 'on tap', 'Tap', 'impact .rigid 0.5', 'VIRTUAL_KEY', 'Tap'),
    ('Upload pieces, processing', '—', 'none', '—', '—', '—'),
    ('Pose timeline scrub', 'each of the 16 stills', 'Tick', 'selection', 'SEGMENT_FREQUENT_TICK', '—'),
    ('Play / pause', 'on tap', 'Tap', 'impact .light', 'CLOCK_TICK', '—'),
    ('Tap a player in footage', 'as the brackets snap', 'Tap', 'impact .rigid 0.6', 'CLICK 0.6', 'Tap'),
    ('“Use 3.8” suggestion', 'on tap', 'Tick', 'selection', 'SEGMENT_TICK', '—'),
  ]),
  ('ONBOARDING', [
    ('Role picked', 'on select', 'Tick', 'selection', 'SEGMENT_TICK', 'Tick'),
    ('Wrong 6-digit code', 'as the error shows', 'Error', '.error', 'REJECT', 'Reject'),
    ('Code accepted', 'on sign-in', 'Success', '.success', 'CONFIRM', 'Confirm'),
    ('Permission screens', 'system dialog', 'none', '—', '—', '—'),
  ]),
]

# ---------- budget tier
BUDGET_VOCAB = [  # (name, system constant, on/off timings, strength version, used for)
  ('Tap', 'VIRTUAL_KEY', '20 ms', '20 ms at 140', 'Primary buttons, record, player pick, switches on'),
  ('Tick', 'CLOCK_TICK', 'skip — too short to feel', '12 ms at 90', 'Tabs, chips, role pick (only where the system gives one)'),
  ('Confirm', 'CONFIRM (Android 11+)', '25 on · 90 off · 45 on', '25 at 140 · 90 off · 45 at 220', 'Saved, uploaded, verified, levels, badges, streaks'),
  ('Reject', 'REJECT (Android 11+)', '40 on · 80 off · 40 on · 80 off · 40 on', '40 at 200 × 3, 80 off', 'Errors that come with a message'),
  ('Pulse', '—', '25–30 ms', '12 ms spike at 100–150', 'Sparks, refresh landing, logo pop, streak warning'),
  ('Thump', 'LONG_PRESS as fallback', '60 ms', '50 ms at 255', 'Launch ignite only'),
]
BUDGET_ONOFF = [(600, 25), (950, 25), (1250, 25), (1520, 60), (1760, 30), (2000, 30), (2180, 30), (2300, 30), (2420, 45)]
BUDGET_STRENGTH = ([('t', x, a) for x, a in [(430, .35), (560, .45), (680, .35), (790, .5), (900, .45), (1000, .55), (1090, .5)]]
  + [('s', 1140 + i * 60, 60, .12 + i * .08) for i in range(4)] + [('t', 1520, 1.0)]
  + [('s', 1560 + i * 60, 60, .16 + (i / 13) ** 2 * .84) for i in range(14)] + [('t', 2420, .6)])

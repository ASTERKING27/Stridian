/* The Stridian sport kit: every court drawn to its official proportions, the squad's spots
   on it, and one signature motion per sport.
   Court units are metres, long axis horizontal, origin at the top-left corner of the playing
   area (cricket: of the boundary oval's bounding box). Every shape is a path; circles are arc
   pairs. Paint order and tokens (CSS classes from kitLayers, coloured in site/court.css):
     texture  kt / ktl  fill or 1px line in --court-fill (faint pattern)
     fills    kf        fill --court-fill (zones, keys, boxes)
     lines    kl        1px stroke --court
     dashed   kd        1px dashed stroke --court
     strong   ks        1.25px stroke --court-strong (boundary, net, frames)
     marks    km        fill --court-strong (spots, stumps, posts, crossing squares)
     key      kk / kkm  the ONE signature element, 1.5px stroke (and fill) --court-key
   Spots: { pos (the exact position name from backend/sports_config.py), x, y (metres),
     lab: label side b|t|l|r (default b), face: -1|1 seated kho-kho chaser facing y 0 or y 16,
     active: the one active chaser }. Every squad attacks left to right. */
function kitN(v) { var r = Math.round(v * 100) / 100; return String(r === 0 ? 0 : r); }
function kitP(x, y) { return kitN(x) + ' ' + kitN(y); }
function kitRect(x, y, w, h) { return 'M' + kitP(x, y) + 'H' + kitN(x + w) + 'V' + kitN(y + h) + 'H' + kitN(x) + 'Z'; }
function kitLine(x1, y1, x2, y2) { return 'M' + kitP(x1, y1) + 'L' + kitP(x2, y2); }
function kitPoly(pts, close) { return pts.map(function (p, i) { return (i ? 'L' : 'M') + kitP(p[0], p[1]); }).join('') + (close ? 'Z' : ''); }
function kitPt(cx, cy, r, deg) { var t = deg * Math.PI / 180; return [cx + r * Math.cos(t), cy + r * Math.sin(t)]; }
/* Arc from angle a0 to a1 in degrees (0 = +x, positive = clockwise on screen). cont = continue the current subpath (no M). */
function kitArc(cx, cy, r, a0, a1, cont) {
  var p0 = kitPt(cx, cy, r, a0), p1 = kitPt(cx, cy, r, a1);
  return (cont ? '' : 'M' + kitP(p0[0], p0[1])) + 'A' + kitN(r) + ' ' + kitN(r) + ' 0 ' + (Math.abs(a1 - a0) > 180 ? 1 : 0) + ' ' + (a1 > a0 ? 1 : 0) + ' ' + kitP(p1[0], p1[1]);
}
/* Circles and ellipses take their radius from the ROUNDED endpoints (floored to 3 decimals) so each half
   is an exact semicircle; a radius rounded on its own can bulge small circles into ovals. */
function kitHalf(v) { return String(Math.floor(v * 1000 + 1e-6) / 1000); }
function kitCircle(cx, cy, r) {
  var x0 = +kitN(cx - r), x1 = +kitN(cx + r), y = +kitN(cy), h = kitHalf((x1 - x0) / 2), a = 'A' + h + ' ' + h + ' 0 1 0 ';
  return 'M' + kitP(x0, y) + a + kitP(x1, y) + a + kitP(x0, y) + 'Z';
}
function kitEllipse(cx, cy, rx, ry, rot) {
  var t = (rot || 0) * Math.PI / 180, dx = rx * Math.cos(t), dy = rx * Math.sin(t);
  var x0 = +kitN(cx - dx), y0 = +kitN(cy - dy), x1 = +kitN(cx + dx), y1 = +kitN(cy + dy), k = Math.hypot(x1 - x0, y1 - y0) / 2 / rx;
  var a = 'A' + kitHalf(rx * k) + ' ' + kitHalf(ry * k) + ' ' + kitN(rot || 0) + ' 1 0 ';
  return 'M' + kitP(x0, y0) + a + kitP(x1, y1) + a + kitP(x0, y0) + 'Z';
}
function kitDeg(rad) { return rad * 180 / Math.PI; }
function kitMirror(d, w) { /* mirror an absolute M/L/H/V/A/Z path across x = w/2 */
  return d.replace(/([MLHVAZ])([^MLHVAZ]*)/g, function (m, c, a) {
    var n = a.trim() ? a.trim().split(/[\s,]+/).map(Number) : [];
    if (c === 'M' || c === 'L') return c + kitP(w - n[0], n[1]);
    if (c === 'H') return c + kitN(w - n[0]);
    if (c === 'A') return c + n[0] + ' ' + n[1] + ' ' + kitN(n[2] ? -n[2] : 0) + ' ' + n[3] + ' ' + (1 - n[4]) + ' ' + kitP(w - n[5], n[6]);
    return c + a.trim();
  });
}
function kitBoth(d, w) { return [d, kitMirror(d, w)]; }
function kitCat(a) { return [].concat.apply([], a); }
/* Paint-ordered layer list for one sport: [{ d, c }] where c is the CSS class above. */
function kitLayers(k) {
  var c = k.court, out = [];
  function add(list, cls) { (list || []).forEach(function (d) { out.push({ d: d, c: cls }); }); }
  add(c.texture, c.textureMode === 'line' ? 'ktl' : 'kt'); add(c.fills, 'kf'); add(c.lines, 'kl'); add(c.dashed, 'kd');
  add(c.strong, 'ks'); add(c.marks, 'km'); add(c.key, 'kk'); add(c.keyMarks, 'kkm');
  return out;
}

const SPORTKIT = (function () {
  /* ---------- Football: 105 x 68 ---------- */
  var fb = (function () {
    var W = 105, H = 68, cy = 34, pa = Math.acos(5.5 / 9.15) * 180 / Math.PI;
    var stripes = []; for (var i = 1; i < 10; i += 2) stripes.push(kitRect(i * 10.5, 0, 10.5, H));
    var half = function (d) { return kitBoth(d, W); };
    return {
      icon: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 8l3.8 2.8-1.5 4.4H9.7l-1.5-4.4L12 8ZM12 8V3M15.8 10.8l4.4-1.5M14.3 15.2l2.8 3.9M9.7 15.2l-2.8 3.9M8.2 10.8 3.8 9.3',
      court: {
        w: W, h: H, viewBox: '-3 -3 111 74',
        texture: stripes, textureMode: 'fill',
        fills: kitCat([half(kitRect(-2, cy - 3.66, 2, 7.32))]),
        lines: kitCat([
          [kitLine(52.5, 0, 52.5, H)],
          half(kitPoly([[0, cy - 20.16], [16.5, cy - 20.16], [16.5, cy + 20.16], [0, cy + 20.16]])),
          half(kitPoly([[0, cy - 9.16], [5.5, cy - 9.16], [5.5, cy + 9.16], [0, cy + 9.16]])),
          half(kitArc(11, cy, 9.15, -pa, pa)),
          [kitArc(0, 0, 1, 0, 90), kitArc(W, 0, 1, 90, 180), kitArc(W, H, 1, 180, 270), kitArc(0, H, 1, 270, 360)]
        ]),
        strong: kitCat([[kitRect(0, 0, W, H)], half(kitPoly([[0, cy - 3.66], [-2, cy - 3.66], [-2, cy + 3.66], [0, cy + 3.66]]))]),
        marks: [kitCircle(52.5, cy, 0.3), kitCircle(11, cy, 0.3), kitCircle(94, cy, 0.3)],
        key: [kitCircle(52.5, cy, 9.15)]
      },
      crop: '-3 22.75 67.5 22.5',
      squadView: '-3 -3 111 74',
      spots: [
        { pos: 'Goalkeeper', x: 5.5, y: 34 },
        { pos: 'Centre-back', x: 18.5, y: 24.5 }, { pos: 'Centre-back', x: 18.5, y: 43.5 },
        { pos: 'Full-back', x: 26, y: 8.5 }, { pos: 'Full-back', x: 26, y: 59.5 },
        { pos: 'Central Midfielder', x: 37, y: 34 }, { pos: 'Central Midfielder', x: 47, y: 19.5 }, { pos: 'Central Midfielder', x: 47, y: 48.5 },
        { pos: 'Winger', x: 72, y: 9 }, { pos: 'Winger', x: 72, y: 59 },
        { pos: 'Striker', x: 82, y: 34 }
      ],
      motion: 'roll',
      move: {
        view: '32.5 20.67 40 26.67', dur: 3.6,
        path: 'M52.5 23.2V44.8',
        obj: kitCircle(0, 0, 0.75) + kitPoly([[0, -0.36], [0.34, -0.11], [0.21, 0.29], [-0.21, 0.29], [-0.34, -0.11]], true),
        shadow: kitCircle(0.22, 0.26, 0.72),
        hit: '', props: []
      }
    };
  })();

  /* ---------- Basketball (FIBA): 28 x 15 ---------- */
  var bb = (function () {
    var W = 28, H = 15, cy = 7.5, bx = 1.575, t3 = kitDeg(Math.asin(6.6 / 6.75)), x3 = bx + 6.75 * Math.cos(t3 * Math.PI / 180);
    var boards = []; for (var y = 0.5; y < H; y += 0.5) boards.push(kitLine(0, y, W, y));
    var half = function (d) { return kitBoth(d, W); };
    return {
      icon: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM3 12h18M12 3v18M5.6 5.6c2.4 2.4 2.4 10.4 0 12.8M18.4 5.6c-2.4 2.4-2.4 10.4 0 12.8',
      court: {
        w: W, h: H, viewBox: '-1 -1 30 17',
        texture: boards, textureMode: 'line',
        fills: half(kitRect(0, cy - 2.45, 5.8, 4.9)),
        lines: kitCat([
          [kitLine(14, 0, 14, H), kitCircle(14, cy, 1.8)],
          half(kitPoly([[0, cy - 2.45], [5.8, cy - 2.45], [5.8, cy + 2.45], [0, cy + 2.45]])),
          half(kitArc(5.8, cy, 1.8, -90, 90)),
          half('M0 0.9H' + kitN(x3) + kitArc(bx, cy, 6.75, -t3, t3, true) + 'H0'),
          half('M1.2 6.25H' + kitN(bx) + kitArc(bx, cy, 1.25, -90, 90, true) + 'H1.2')
        ]),
        dashed: half(kitArc(5.8, cy, 1.8, 90, 270)),
        strong: kitCat([[kitRect(0, 0, W, H)], half(kitLine(1.2, cy - 0.9, 1.2, cy + 0.9)), half(kitLine(1.2, cy, bx - 0.225, cy))]),
        marks: [],
        key: half(kitCircle(bx, cy, 0.225))
      },
      crop: '11 4.5 18 6',
      squadView: '-1 -1 30 17',
      spots: [ /* half-court set at the right-hand basket: the squad attacks left to right */
        { pos: 'Point Guard', x: 18.3, y: 7.5 },
        { pos: 'Shooting Guard', x: 20.1, y: 2 },
        { pos: 'Small Forward', x: 20.7, y: 12.9, lab: 't' },
        { pos: 'Power Forward', x: 25.7, y: 4.2, lab: 't' },
        { pos: 'Centre', x: 25.7, y: 10.8 }
      ],
      motion: 'bounce',
      move: {
        view: '17 3.5 12 8', dur: 0.8,
        path: 'M21.7 7.5H21.71',
        obj: kitCircle(0, 0, 0.24),
        shadow: kitCircle(0.06, 0.08, 0.23),
        hit: kitCircle(21.7, 7.5, 0.34), props: []
      }
    };
  })();

  /* ---------- Volleyball: 18 x 9, net at 9, 3 m free zone ---------- */
  var vb = {
    icon: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 12c0-4 2-7 5.2-8.2M12 12c-3.5 2-7 2.3-9 1M12 12c3.5 2 5.4 5 5.7 7.7',
    court: {
      w: 18, h: 9, viewBox: '-3.6 -3.6 25.2 16.2',
      texture: [], textureMode: 'fill',
      fills: [kitRect(6, 0, 6, 9)],
      lines: [kitLine(6, 0, 6, 9), kitLine(12, 0, 12, 9), kitLine(9, 0, 9, 9)],
      dashed: [kitRect(-3, -3, 24, 15)],
      strong: [kitRect(0, 0, 18, 9)],
      marks: [kitCircle(9, -1, 0.12), kitCircle(9, 10, 0.12)],
      key: [kitLine(9, -1, 9, 10)]
    },
    crop: '2 -1.6 14 4.67',
    squadView: '-1.4 -1.15 20.8 11.3',
    spots: [
      { pos: 'Outside Hitter', x: 6.6, y: 1.5 },
      { pos: 'Middle Blocker', x: 6.6, y: 4.5 },
      { pos: 'Opposite / Server', x: 6.6, y: 7.5 },
      { pos: 'Setter', x: 2, y: 7.5 },
      { pos: 'Libero', x: 2, y: 1.5 },
      { pos: 'Outside Hitter', x: 2, y: 4.5 }
    ],
    motion: 'arc',
    move: {
      view: '1.5 -0.5 15 10', dur: 2.4,
      path: 'M3.6 6.4L14.4 2.6',
      obj: kitCircle(0, 0, 0.3),
      shadow: kitCircle(0, 0, 0.28),
      hit: '', props: []
    }
  };

  /* ---------- Cricket: oval rx 70 ry 64, pitch 20.12 x 3.05 between the stumps ---------- */
  var ck = (function () {
    var cx = 70, cy = 64, RX = 70, RY = 64, s1 = cx - 10.06, s2 = cx + 10.06, R = 27.43;
    function band(y1, y2) { /* horizontal mowing band clipped to the oval */
      var hx = function (y) { var t = 1 - Math.pow((y - cy) / RY, 2); return RX * Math.sqrt(Math.max(0, t)); };
      var a = hx(y1), b = hx(y2), arc = 'A' + RX + ' ' + RY + ' 0 0 1 ';
      return 'M' + kitP(cx - a, y1) + 'H' + kitN(cx + a) + arc + kitP(cx + b, y2) + 'H' + kitN(cx - b) + arc + kitP(cx - a, y1) + 'Z';
    }
    /* 8 m bands every 16 m, one centred on the pitch so the pattern is symmetric about it */
    var bands = []; for (var y = cy - 4 - 64; y < 128; y += 16) { var b0 = Math.max(0, y), b1 = Math.min(128, y + 8); if (b1 > b0) bands.push(band(b0, b1)); }
    function end(s, dir) { /* creases at one end; dir = +1 for the left end (popping crease towards +x) */
      var pc = s + 1.22 * dir;
      return [kitLine(s, cy - 1.32, s, cy + 1.32), kitLine(pc, cy - 1.83, pc, cy + 1.83),
        kitLine(pc, cy - 1.32, pc - 2.44 * dir, cy - 1.32), kitLine(pc, cy + 1.32, pc - 2.44 * dir, cy + 1.32)];
    }
    return {
      icon: 'M15 3.8 20.2 9 11 18.2 5.8 13 15 3.8ZM8.4 15.6 3.5 20.5M6.5 8.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z',
      court: {
        w: 140, h: 128, viewBox: '-2 -2 144 132',
        texture: bands, textureMode: 'fill',
        fills: [kitRect(s1, cy - 1.525, 20.12, 3.05)],
        lines: kitCat([end(s1, 1), end(s2, -1)]),
        dashed: ['M' + kitP(s1, cy - R) + 'H' + kitN(s2) + kitArc(s2, cy, R, -90, 90, true) + 'H' + kitN(s1) + kitArc(s1, cy, R, 90, 270, true) + 'Z'],
        strong: [kitEllipse(cx, cy, RX, RY)],
        marks: [kitRect(s1 - 0.06, cy - 0.23, 0.12, 0.46), kitRect(s2 - 0.06, cy - 0.23, 0.12, 0.46)],
        key: [kitRect(s1, cy - 1.525, 20.12, 3.05)]
      },
      crop: '25 49 90 30',
      squadView: '-1 25.4 142 77.2',
      spots: [
        { pos: 'Wicketkeeper', x: 88.5, y: 62.6, lab: 'r' },
        { pos: 'Fast Bowler', x: 33, y: 64 },
        { pos: 'Spin Bowler', x: 50, y: 74 },
        { pos: 'Opening Batsman', x: 79.6, y: 66.4 },
        { pos: 'Middle-order Batsman', x: 60.5, y: 61.4, lab: 't' },
        { pos: 'All-rounder', x: 70, y: 38.5 }
      ],
      motion: 'bowl',
      move: {
        view: '55 54 30 20', dur: 2.6,
        path: 'M60.7 64.7L79.94 64.04',
        obj: kitCircle(0, 0, 0.5),
        shadow: kitCircle(0.1, 0.14, 0.46),
        hit: kitRect(s2 + 0.08, cy - 0.5, 0.26, 1), props: []
      }
    };
  })();

  /* ---------- Badminton: 13.4 x 6.1, net at 6.7 ---------- */
  var bd = (function () {
    var W = 13.4, H = 6.1, n = 6.7;
    var half = function (d) { return kitBoth(d, W); };
    return {
      icon: 'M9 17h6v1.5a3 3 0 0 1-6 0V17ZM9 17 5 4M15 17l4-13M12 17V4M5 4h14M6.7 9.5h10.6',
      court: {
        w: W, h: H, viewBox: '-0.8 -0.9 15 7.9',
        texture: [], textureMode: 'fill',
        fills: [kitRect(n - 1.98, 0, 3.96, H)],
        lines: kitCat([
          [kitLine(0, 0.46, W, 0.46), kitLine(0, H - 0.46, W, H - 0.46)],
          half(kitLine(n - 1.98, 0, n - 1.98, H)),
          half(kitLine(0.76, 0, 0.76, H)),
          half(kitLine(0, H / 2, n - 1.98, H / 2))
        ]),
        strong: [kitRect(0, 0, W, H)],
        marks: [kitCircle(n, 0, 0.07), kitCircle(n, H, 0.07)],
        key: [kitLine(n, -0.2, n, H + 0.2)]
      },
      crop: '0.4 -0.7 12.6 4.2',
      squadView: '-0.8 -0.9 15 7.9',
      spots: [
        { pos: 'Attacking / Power player', x: 5.8, y: 1.5, lab: 'l' },
        { pos: 'All-court / Balanced', x: 3.4, y: 3.1 },
        { pos: 'Defensive / Counter player', x: 0.5, y: 5, lab: 'r' }
      ],
      motion: 'shuttle',
      move: {
        view: '-0.3 -1.62 14 9.33', dur: 2.8,
        path: 'M1.6 4.3C4.5 0.6 9 0.2 11.8 1.8C8.9 5.5 4.4 5.9 1.6 4.3Z',
        obj: kitCircle(0.19, 0, 0.1) + kitPoly([[0.08, -0.07], [-0.36, -0.2], [-0.36, 0.2], [0.08, 0.07]], true),
        shadow: kitPoly([[0.2, -0.06], [-0.34, -0.17], [-0.34, 0.17], [0.2, 0.06]], true),
        hit: '', props: []
      }
    };
  })();

  /* ---------- Tennis: 23.77 x 10.97, net at 11.885 ---------- */
  var tn = (function () {
    var W = 23.77, H = 10.97, n = W / 2, s = 1.37, sv = 6.4;
    return {
      icon: 'M14 15a6 6 0 1 0 0-12 6 6 0 0 0 0 12ZM9.8 13.2 3.5 19.5M11 6.5l6 5M11 11l5.5-5M19.5 21a1.8 1.8 0 1 0 0-3.6 1.8 1.8 0 0 0 0 3.6Z',
      court: {
        w: W, h: H, viewBox: '-1.5 -1.6 26.77 14.17',
        texture: [], textureMode: 'fill',
        fills: [kitRect(n - sv, s, 2 * sv, H - 2 * s)],
        lines: [kitLine(0, s, W, s), kitLine(0, H - s, W, H - s),
          kitLine(n - sv, s, n - sv, H - s), kitLine(n + sv, s, n + sv, H - s),
          kitLine(n - sv, H / 2, n + sv, H / 2),
          kitLine(0, H / 2, 0.1, H / 2), kitLine(W, H / 2, W - 0.1, H / 2)],
        strong: [kitRect(0, 0, W, H)],
        marks: [kitCircle(n, -0.914, 0.08), kitCircle(n, H + 0.914, 0.08)],
        key: [kitLine(n, -0.914, n, H + 0.914)]
      },
      crop: '2.5 -0.5 18.77 6.26',
      squadView: '-1.5 -1.6 26.77 14.17',
      spots: [
        { pos: 'Attacking / Power player', x: 9.8, y: 2.4, lab: 'l' },
        { pos: 'All-court / Balanced', x: 5.4, y: 5.5 },
        { pos: 'Defensive / Counter player', x: 0.3, y: 8.9, lab: 'r' }
      ],
      motion: 'rally',
      move: {
        view: '-0.5 -2.77 24.77 16.51', dur: 2.6,
        path: 'M1.2 7.4L22.6 2.6',
        obj: kitCircle(0, 0, 0.42),
        shadow: kitCircle(0.1, 0.14, 0.4),
        hit: kitEllipse(19, 3.41, 0.62, 0.3, -12.64), props: []
      }
    };
  })();

  /* ---------- Kho-Kho: 27 x 16, post lines at 1.5 and 25.5 ---------- */
  var kk = (function () {
    var W = 27, H = 16, cy = 8, p1 = 1.5, p2 = 25.5, lane = [], sq = [], spots = [], props = [];
    var names = [];
    for (var i = 0; i < 8; i++) lane.push(p1 + 2.5 + i * (p2 - p1 - 5) / 7);
    var lines = [kitLine(p1, 0, p1, H), kitLine(p2, 0, p2, H), kitLine(p1, cy - 0.15, p2, cy - 0.15), kitLine(p1, cy + 0.15, p2, cy + 0.15)];
    lane.forEach(function (c, i) {
      lines.push(kitLine(c - 0.175, 0, c - 0.175, H), kitLine(c + 0.175, 0, c + 0.175, H));
      sq.push(kitRect(c - 0.175, cy - 0.15, 0.35, 0.3));
      /* seated chasers alternate facing (face -1 = towards y 0, +1 = towards y 16); the label sits on the side they turn their back to */
      spots.push({ pos: 'Chaser', x: Math.round(c * 100) / 100, y: cy, lab: i % 2 ? 'b' : 't', face: i % 2 ? -1 : 1 });
      props.push(kitCircle(c, cy, 0.28));
    });
    spots.push({ pos: 'Chaser', x: 1.1, y: 9.3, active: true });
    spots.push({ pos: 'Runner / Dodger', x: 11.6, y: 2.4 }, { pos: 'Runner / Dodger', x: 16.6, y: 12.2 }, { pos: 'Runner / Dodger', x: 22.6, y: 2.4 });
    return {
      icon: 'M4 3v18M20 3v18M2 21h4M18 21h4M7 15l3-3 3 3 3-3M14 9h3v3',
      court: {
        w: W, h: H, viewBox: '-1 -1 29 18',
        texture: [], textureMode: 'fill',
        fills: [kitRect(0, 0, p1, H), kitRect(p2, 0, W - p2, H)],
        lines: lines,
        strong: [kitRect(0, 0, W, H)],
        marks: sq,
        key: [kitCircle(p1, cy, 0.15), kitCircle(p2, cy, 0.15)],
        keyMarks: [kitCircle(p1, cy, 0.15), kitCircle(p2, cy, 0.15)]
      },
      crop: '12.5 5.5 15 5',
      squadView: '-1 -1 29 18',
      spots: spots,
      motion: 'chase',
      move: {
        view: '-0.5 3 15 10', dur: 3.2,
        path: 'M1.9 9C3.2 10.7 5.3 10.6 6.62 8.55',
        obj: kitCircle(0, 0, 0.3) + kitPoly([[0.42, 0], [0.18, -0.2], [0.18, 0.2]], true),
        shadow: '',
        hit: kitCircle(lane[1], cy, 0.62), props: props
      }
    };
  })();

  return { Football: fb, Basketball: bb, Volleyball: vb, Cricket: ck, Badminton: bd, Tennis: tn, 'Kho-Kho': kk };
})();

export { SPORTKIT, kitLayers }

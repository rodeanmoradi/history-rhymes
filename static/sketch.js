// Draws a lesson scene (see Scene in app/lesson.py) as a hand-drawn stick-figure panel.
// Everything is black ink plus one spot colour, with a seeded wobble so a drawing is identical on every load.

const Sketch = (() => {
  const NS = "http://www.w3.org/2000/svg";
  const W = 600, H = 270, GROUND = 222;
  const INK = "#1d1b18", SPOT = "#b8432f", PAPER = "#fffdf6";
  const SPOTS = { left: 80, center_left: 190, center: 300, center_right: 410, right: 520 };
  const SKY = new Set(["sun", "cloud"]);
  const VESSELS = { ship: 22, boat: 10 };  // deck height above the waterline

  // ---- seeded randomness -------------------------------------------------------------

  function hash(text) {
    let h = 2166136261;
    for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 16777619);
    return h >>> 0;
  }

  function mulberry32(seed) {
    return () => {
      seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // ---- pen: wobbly primitives ---------------------------------------------------------

  function makePen(svg, seed) {
    const rand = mulberry32(seed);
    const j = (amount) => (rand() - 0.5) * 2 * amount;
    const f = (n) => n.toFixed(1);

    function el(tag, attrs, parent = svg) {
      const node = document.createElementNS(NS, tag);
      for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
      parent.appendChild(node);
      return node;
    }

    function stroke(d, opts = {}) {
      return el("path", {
        d,
        fill: opts.fill || "none",
        stroke: opts.color || INK,
        "stroke-width": opts.width || 2.2,
        "stroke-linecap": "round",
        "stroke-linejoin": "round",
        opacity: opts.opacity || 1,
      });
    }

    function line(x1, y1, x2, y2, opts) {
      const len = Math.hypot(x2 - x1, y2 - y1);
      const wob = Math.min(2.2, 0.6 + len / 90);
      const mx = (x1 + x2) / 2 + j(wob), my = (y1 + y2) / 2 + j(wob);
      return stroke(`M${f(x1 + j(0.8))} ${f(y1 + j(0.8))} Q${f(mx)} ${f(my)} ${f(x2 + j(0.8))} ${f(y2 + j(0.8))}`, opts);
    }

    function poly(points, opts = {}) {
      // Closed shapes are drawn as one path so they can be filled with paper and hide what is behind them.
      const p = points.map(([x, y]) => [x + j(1), y + j(1)]);
      let d = `M${f(p[0][0])} ${f(p[0][1])}`;
      for (let i = 1; i < p.length; i++) {
        const [ax, ay] = p[i - 1], [bx, by] = p[i];
        d += ` Q${f((ax + bx) / 2 + j(1.2))} ${f((ay + by) / 2 + j(1.2))} ${f(bx)} ${f(by)}`;
      }
      if (opts.closed) d += " Z";
      return stroke(d, { fill: opts.closed ? opts.fill || PAPER : "none", ...opts });
    }

    function rect(x, y, w, h, opts = {}) {
      return poly([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], { closed: true, ...opts });
    }

    function blob(cx, cy, rx, ry, opts = {}) {
      // A hand-drawn ellipse: radius jitters a little and the stroke overshoots its start.
      const n = 10, start = rand() * Math.PI * 2, pts = [];
      for (let i = 0; i <= n + 1; i++) {
        const a = start + (i / n) * Math.PI * 2;
        const k = 1 + j(opts.rough ?? 0.05);
        pts.push([cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]);
      }
      let d = `M${f(pts[0][0])} ${f(pts[0][1])}`;
      for (let i = 1; i < pts.length - 1; i++) {
        const [x0, y0] = pts[i - 1], [x1, y1] = pts[i], [x2, y2] = pts[i + 1];
        d += ` C${f(x1 - (x2 - x0) / 6)} ${f(y1 - (y2 - y0) / 6)} ${f(x1 + (x2 - x0) / 6)} ${f(y1 + (y2 - y0) / 6)} ${f(x1)} ${f(y1)}`;
      }
      return stroke(d, { fill: opts.fill || PAPER, ...opts });
    }

    function text(x, y, value, opts = {}) {
      const node = el("text", {
        x: f(x), y: f(y),
        "text-anchor": opts.anchor || "middle",
        "font-size": opts.size || 15,
        "font-family": "'Patrick Hand', 'Comic Sans MS', cursive",
        fill: opts.color || INK,
      });
      node.textContent = value;
      return node;
    }

    return { el, stroke, line, poly, rect, blob, text, rand, j };
  }

  // ---- figures ------------------------------------------------------------------------

  // Joint positions for a figure facing right with its feet at (0, 0); y grows downward.
  const STAND_LEGS = { kneeL: [-5, -15], footL: [-8, 0], kneeR: [5, -15], footR: [8, 0] };
  const STAND_ARMS = { elbowL: [-8, -49], handL: [-11, -35], elbowR: [8, -49], handR: [11, -35] };
  const POSES = {
    stand: { hip: [0, -30], neck: [0, -64], ...STAND_ARMS, ...STAND_LEGS },
    walk: {
      hip: [0, -30], neck: [2, -64],
      elbowL: [-9, -50], handL: [-15, -39], elbowR: [9, -50], handR: [16, -41],
      kneeL: [-6, -15], footL: [-14, 0], kneeR: [7, -16], footR: [11, 0],
    },
    run: {
      hip: [0, -31], neck: [9, -62],
      elbowL: [-5, -52], handL: [-16, -47], elbowR: [19, -53], handR: [23, -64],
      kneeL: [-10, -18], footL: [-23, -9], kneeR: [14, -20], footR: [14, 0],
    },
    point: { hip: [0, -30], neck: [0, -64], ...STAND_ARMS, elbowR: [15, -59], handR: [32, -61], ...STAND_LEGS },
    cheer: {
      hip: [0, -30], neck: [0, -64], elbowL: [-12, -76], handL: [-17, -91], elbowR: [12, -76], handR: [17, -91],
      ...STAND_LEGS,
    },
    think: { hip: [0, -30], neck: [0, -64], ...STAND_ARMS, elbowR: [13, -53], handR: [6, -68], ...STAND_LEGS },
    shrug: {
      hip: [0, -30], neck: [0, -63], elbowL: [-15, -55], handL: [-21, -66], elbowR: [15, -55], handR: [21, -66],
      ...STAND_LEGS, tilt: -4,
    },
    sit: {
      hip: [0, -22], neck: [-2, -56],
      elbowL: [4, -38], handL: [14, -29], elbowR: [6, -38], handR: [17, -28],
      kneeL: [14, -25], footL: [14, 0], kneeR: [17, -23], footR: [18, 0],
    },
    kneel: {
      hip: [0, -22], neck: [3, -56],
      elbowL: [9, -45], handL: [17, -50], elbowR: [10, -45], handR: [18, -52],
      kneeL: [-4, -2], footL: [-20, 0], kneeR: [13, -19], footR: [13, 0],
    },
    fall: {
      hip: [-15, -6], neck: [19, -10], head: [32, -13],
      elbowL: [15, -22], handL: [23, -33], elbowR: [11, -3], handR: [2, -1],
      kneeL: [-28, -4], footL: [-42, -1], kneeR: [-27, -10], footR: [-41, -15],
    },
    fight: {
      hip: [0, -28], neck: [7, -62],
      elbowL: [-8, -52], handL: [-17, -58], elbowR: [19, -58], handR: [33, -66],
      kneeL: [-12, -14], footL: [-21, 0], kneeR: [14, -15], footR: [19, 0], sword: true,
    },
    hold: {
      hip: [0, -30], neck: [0, -64], elbowL: [8, -50], handL: [19, -53], elbowR: [10, -49], handR: [21, -50],
      ...STAND_LEGS,
    },
    wave: { hip: [0, -30], neck: [0, -64], ...STAND_ARMS, elbowR: [13, -71], handR: [19, -86], ...STAND_LEGS },
  };
  const SIZES = { small: 0.72, normal: 1, big: 1.3 };

  function drawFigure(pen, fig, x, base) {
    const pose = POSES[fig.pose] || POSES.stand;
    const s = SIZES[fig.size] || 1;
    const dir = fig.facing === "left" ? -1 : 1;
    const at = ([px, py]) => [x + px * dir * s, base + py * s];
    const seg = (a, b) => pen.line(...at(pose[a]), ...at(pose[b]), { width: 2.4 });

    seg("hip", "neck");
    seg("neck", "elbowL"); seg("elbowL", "handL");
    seg("neck", "elbowR"); seg("elbowR", "handR");
    seg("hip", "kneeL"); seg("kneeL", "footL");
    seg("hip", "kneeR"); seg("kneeR", "footR");

    if (pose.sword) {
      const [hx, hy] = at(pose.handR);
      pen.line(hx, hy, hx + 24 * dir * s, hy - 22 * s, { width: 2 });
      pen.line(hx - 4 * dir * s, hy - 5 * s, hx + 5 * dir * s, hy + 5 * s, { width: 2 });
    }

    const r = 11 * s;
    let head = pose.head ? at(pose.head) : null;
    if (!head) {
      const [nx, ny] = at(pose.neck);
      const tilt = (pose.tilt || 0) * dir * s;
      head = [nx + tilt, ny - r - 1];
    }
    pen.blob(head[0], head[1], r, r);
    drawHat(pen, fig.hat, head[0], head[1], r, dir);
    return { head, r, top: head[1] - r - (fig.hat && fig.hat !== "none" ? r * 1.1 : 0) };
  }

  function drawHat(pen, hat, cx, cy, r, dir) {
    const k = r / 11;
    const p = (dx, dy) => [cx + dx * k, cy + dy * k];
    switch (hat) {
      case "crown":
        pen.poly([p(-9, -7), p(-10, -21), p(-5, -14), p(0, -23), p(5, -14), p(10, -21), p(9, -7)],
          { closed: true, fill: SPOT, width: 1.8 });
        break;
      case "helmet":
        pen.poly([p(-12, -2), p(-11, -10), p(-5, -15), p(5, -15), p(11, -10), p(12, -2)], { closed: true, width: 2 });
        pen.line(...p(-14, -2), ...p(14, -2), { width: 2 });
        pen.line(...p(0, -15), ...p(-4 * dir, -24), { width: 3, color: SPOT });
        break;
      case "bicorne":
        pen.poly([p(-20, -6), p(-8, -17), p(0, -21), p(8, -17), p(20, -6)], { closed: true, fill: INK, width: 1.8 });
        break;
      case "tophat":
        pen.rect(...p(-8, -30), 16 * k, 21 * k, { fill: INK, width: 1.8 });
        pen.line(...p(-15, -9), ...p(15, -9), { width: 2.4 });
        break;
      case "cap":
        pen.poly([p(-11, -4), p(-9, -12), p(0, -15), p(9, -12), p(11, -4)], { closed: true, width: 2 });
        pen.line(...p(4 * dir, -5), ...p(19 * dir, -4), { width: 2.4 });
        break;
      case "laurel":
        for (let i = -3; i <= 3; i++) {
          if (i === 0) continue;
          const a = -Math.PI / 2 + i * 0.42, x = cx + Math.cos(a) * r * 1.02, y = cy + Math.sin(a) * r * 1.02;
          pen.blob(x, y, 3.2 * k, 1.8 * k, { width: 1.4, fill: "#6f7d4f", rough: 0.1 });
        }
        break;
      case "hood":
        pen.poly([p(-14, 14), p(-15, -4), p(-9, -15), p(0, -18), p(9, -15), p(15, -4), p(14, 14)], { width: 2 });
        break;
      case "turban":
        pen.blob(cx, cy - 9 * k, 13 * k, 8 * k, { width: 2 });
        pen.line(...p(-11, -6), ...p(9, -14), { width: 1.4 });
        pen.line(...p(-10, -11), ...p(11, -8), { width: 1.4 });
        break;
    }
  }

  // ---- props --------------------------------------------------------------------------

  const PROPS = {
    ship(pen, x, y) {
      pen.line(x, y - 20, x, y - 118);
      pen.poly([[x - 32, y - 108], [x + 32, y - 108], [x + 28, y - 50], [x - 28, y - 50]], { closed: true });
      pen.poly([[x, y - 118], [x + 18, y - 112], [x, y - 106]], { closed: true, fill: SPOT, width: 1.6 });
      pen.poly([[x - 66, y - 22], [x + 66, y - 22], [x + 48, y + 4], [x - 46, y + 4]], { closed: true });
      for (const dx of [-30, -10, 10, 30]) pen.blob(x + dx, y - 10, 3, 3, { width: 1.5 });
    },
    boat(pen, x, y) {
      pen.poly([[x - 32, y - 10], [x + 32, y - 10], [x + 22, y + 3], [x - 22, y + 3]], { closed: true });
      pen.line(x + 18, y - 18, x + 40, y + 8, { width: 2 });
    },
    castle(pen, x, y) {
      pen.rect(x - 58, y - 84, 116, 84);
      for (let i = 0; i < 6; i++) pen.rect(x - 58 + i * 21, y - 96, 11, 12);
      pen.poly([[x - 15, y], [x - 15, y - 28], [x, y - 40], [x + 15, y - 28], [x + 15, y]], { closed: true, fill: INK });
      pen.line(x + 40, y - 96, x + 40, y - 126, { width: 1.8 });
      pen.poly([[x + 40, y - 126], [x + 60, y - 120], [x + 40, y - 113]], { closed: true, fill: SPOT, width: 1.4 });
      pen.rect(x - 38, y - 64, 8, 14, { fill: INK, width: 1.4 });
    },
    tower(pen, x, y) {
      pen.rect(x - 19, y - 124, 38, 124);
      for (let i = 0; i < 3; i++) pen.rect(x - 19 + i * 14, y - 134, 9, 10);
      pen.rect(x - 3, y - 98, 6, 16, { fill: INK, width: 1.4 });
      pen.rect(x - 3, y - 58, 6, 16, { fill: INK, width: 1.4 });
    },
    wall(pen, x, y) {
      pen.rect(x - 62, y - 46, 124, 46);
      for (let row = 1; row < 3; row++) pen.line(x - 62, y - row * 15, x + 62, y - row * 15, { width: 1.3 });
      for (let row = 0; row < 3; row++)
        for (let col = 0; col < 5; col++) {
          const bx = x - 50 + col * 25 + (row % 2) * 12;
          pen.line(bx, y - row * 15, bx, y - row * 15 - 15, { width: 1.3 });
        }
    },
    house(pen, x, y) {
      pen.rect(x - 32, y - 52, 64, 52);
      pen.poly([[x - 40, y - 50], [x, y - 86], [x + 40, y - 50]], { closed: true });
      pen.rect(x - 9, y - 26, 18, 26, { width: 1.8 });
      pen.rect(x + 14, y - 42, 11, 11, { width: 1.6 });
    },
    tent(pen, x, y) {
      pen.poly([[x - 44, y], [x, y - 64], [x + 44, y]], { closed: true });
      pen.poly([[x - 12, y], [x, y - 30], [x + 12, y]], { closed: true, fill: INK, width: 1.6 });
      pen.line(x, y - 64, x, y - 78, { width: 1.8 });
      pen.poly([[x, y - 78], [x + 14, y - 74], [x, y - 70]], { closed: true, fill: SPOT, width: 1.2 });
    },
    factory(pen, x, y) {
      pen.rect(x + 22, y - 104, 14, 60);
      pen.poly([[x - 58, y], [x - 58, y - 44], [x - 38, y - 62], [x - 38, y - 44], [x - 18, y - 62], [x - 18, y - 44],
        [x + 2, y - 62], [x + 2, y - 44], [x + 58, y - 44], [x + 58, y]], { closed: true });
      pen.blob(x + 34, y - 116, 8, 6, { width: 1.5 });
      pen.blob(x + 46, y - 128, 11, 8, { width: 1.5 });
      for (const dx of [-42, -14, 18, 40]) pen.rect(x + dx, y - 30, 10, 12, { width: 1.5 });
    },
    throne(pen, x, y) {
      pen.poly([[x - 22, y - 34], [x - 22, y - 100], [x - 10, y - 112], [x + 10, y - 112], [x + 22, y - 100], [x + 22, y - 34]],
        { closed: true });
      pen.rect(x - 28, y - 38, 56, 10, { fill: SPOT, width: 1.8 });
      pen.line(x - 24, y - 28, x - 24, y);
      pen.line(x + 24, y - 28, x + 24, y);
    },
    desk(pen, x, y) {
      pen.line(x - 48, y - 46, x + 48, y - 46, { width: 2.6 });
      pen.line(x - 42, y - 46, x - 42, y);
      pen.line(x + 42, y - 46, x + 42, y);
      pen.poly([[x - 26, y - 47], [x - 22, y - 53], [x + 6, y - 53], [x + 2, y - 47]], { closed: true, width: 1.4 });
      pen.line(x + 20, y - 47, x + 28, y - 64, { width: 1.6 });
    },
    flag(pen, x, y) {
      pen.line(x, y, x, y - 118);
      pen.poly([[x, y - 116], [x + 22, y - 120], [x + 48, y - 112], [x + 48, y - 86], [x + 22, y - 94], [x, y - 90]],
        { closed: true, fill: SPOT, width: 1.8 });
    },
    cannon(pen, x, y) {
      pen.poly([[x - 34, y - 28], [x + 36, y - 46], [x + 39, y - 34], [x - 30, y - 14]], { closed: true, fill: INK });
      pen.blob(x - 8, y - 14, 14, 14, { width: 2.2 });
      pen.blob(x - 8, y - 14, 3, 3, { fill: INK, width: 1.4 });
      for (const [dx, dy] of [[34, -6], [46, -6], [40, -16]]) pen.blob(x + dx, y + dy, 5.5, 5.5, { fill: INK, width: 1.2 });
    },
    shield(pen, x, y) {
      pen.poly([[x - 22, y - 74], [x + 22, y - 74], [x + 20, y - 40], [x, y - 14], [x - 20, y - 40]], { closed: true });
      pen.line(x, y - 72, x, y - 18, { color: SPOT, width: 3 });
      pen.line(x - 19, y - 52, x + 19, y - 52, { color: SPOT, width: 3 });
    },
    coins(pen, x, y) {
      for (const [dx, n] of [[-24, 4], [0, 7], [24, 3]]) {
        for (let i = 0; i < n; i++) pen.line(x + dx - 10, y - 4 - i * 5, x + dx + 10, y - 4 - i * 5, { width: 1.6 });
        pen.blob(x + dx, y - 4 - n * 5, 10, 3.5, { fill: SPOT, width: 1.5 });
      }
    },
    scroll(pen, x, y) {
      pen.rect(x - 24, y - 92, 48, 56);
      pen.blob(x, y - 92, 28, 4.5, { width: 1.8 });
      pen.blob(x, y - 36, 28, 4.5, { width: 1.8 });
      for (let i = 0; i < 5; i++) pen.line(x - 16, y - 82 + i * 9, x + 14 - (i === 4 ? 12 : 0), y - 82 + i * 9, { width: 1.1 });
    },
    barrel(pen, x, y) {
      pen.poly([[x - 18, y], [x - 23, y - 22], [x - 18, y - 46], [x + 18, y - 46], [x + 23, y - 22], [x + 18, y]], { closed: true });
      pen.line(x - 21, y - 12, x + 21, y - 12, { width: 1.5 });
      pen.line(x - 21, y - 34, x + 21, y - 34, { width: 1.5 });
    },
    sack(pen, x, y) {
      pen.poly([[x - 20, y], [x - 25, y - 22], [x - 12, y - 42], [x - 6, y - 50], [x + 6, y - 50], [x + 12, y - 42],
        [x + 25, y - 22], [x + 20, y]], { closed: true });
      pen.line(x - 10, y - 42, x + 10, y - 42, { width: 2 });
    },
    tree(pen, x, y) {
      pen.line(x - 4, y, x - 3, y - 54, { width: 2.6 });
      pen.line(x + 4, y, x + 3, y - 54, { width: 2.6 });
      for (const [dx, dy, r] of [[-18, -66, 16], [16, -68, 17], [0, -86, 19], [-4, -62, 15]]) pen.blob(x + dx, y + dy, r, r * 0.85);
    },
    hill(pen, x, y) {
      pen.poly([[x - 95, y], [x - 50, y - 42], [x, y - 58], [x + 48, y - 40], [x + 95, y]], { width: 2 });
    },
    sun(pen, x) {
      pen.blob(x, 46, 17, 17, { fill: SPOT, width: 1.8 });
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * Math.PI * 2;
        pen.line(x + Math.cos(a) * 24, 46 + Math.sin(a) * 24, x + Math.cos(a) * 32, 46 + Math.sin(a) * 32, { width: 1.8 });
      }
    },
    cloud(pen, x) {
      for (const [dx, dy, r] of [[-20, 52, 14], [0, 44, 18], [22, 52, 13], [4, 56, 14]]) pen.blob(x + dx, dy, r * 1.2, r * 0.9);
    },
    crowd(pen, x, y) {
      const heads = [[-46, -40], [-30, -46], [-14, -42], [2, -47], [18, -41], [34, -45], [50, -40], [-38, -26], [-20, -28], [-2, -25], [16, -27], [34, -26]];
      for (const [dx, dy] of heads) {
        pen.stroke(`M${x + dx - 9} ${y + dy + 22} Q${x + dx} ${y + dy + 6} ${x + dx + 9} ${y + dy + 22}`, { fill: PAPER, width: 1.8 });
        pen.blob(x + dx, y + dy, 6.5, 6.5, { width: 1.8 });
      }
    },
    chart_up(pen, x, y) { chart(pen, x, y, [[-30, -40], [-12, -52], [4, -48], [24, -82]]); },
    chart_down(pen, x, y) { chart(pen, x, y, [[-30, -86], [-12, -70], [4, -76], [24, -42]]); },
    ballot_box(pen, x, y) {
      pen.poly([[x - 6, y - 46], [x - 9, y - 72], [x + 11, y - 74], [x + 10, y - 46]], { closed: true, width: 1.6 });
      pen.rect(x - 30, y - 50, 60, 50);
      pen.line(x - 14, y - 50, x + 14, y - 50, { width: 4 });
      pen.line(x - 10, y - 30, x + 10, y - 30, { color: SPOT, width: 2 });
    },
    train(pen, x, y) {
      pen.rect(x - 62, y - 42, 50, 32);
      pen.rect(x - 6, y - 50, 60, 40);
      pen.rect(x + 28, y - 72, 26, 22);
      pen.rect(x - 2, y - 66, 12, 16, { fill: INK, width: 1.4 });
      for (const dx of [-52, -24, 6, 38]) pen.blob(x + dx, y - 8, 8, 8, { width: 2 });
      pen.blob(x - 6, y - 78, 6, 5, { width: 1.5 });
    },
    rocket(pen, x, y) {
      pen.poly([[x - 11, y - 14], [x - 11, y - 96], [x, y - 122], [x + 11, y - 96], [x + 11, y - 14]], { closed: true });
      pen.poly([[x - 11, y - 34], [x - 24, y - 8], [x - 11, y - 14]], { closed: true, fill: INK, width: 1.4 });
      pen.poly([[x + 11, y - 34], [x + 24, y - 8], [x + 11, y - 14]], { closed: true, fill: INK, width: 1.4 });
      pen.line(x - 11, y - 96, x + 11, y - 96, { color: SPOT, width: 3 });
    },
  };

  function chart(pen, x, y, points) {
    pen.line(x - 34, y, x - 26, y - 22, { width: 1.8 });
    pen.line(x + 34, y, x + 26, y - 22, { width: 1.8 });
    pen.rect(x - 42, y - 98, 84, 76);
    const pts = points.map(([dx, dy]) => [x + dx, y + dy]);
    pen.poly(pts, { color: SPOT, width: 2.6 });
    const [ax, ay] = pts[pts.length - 1], [bx, by] = pts[pts.length - 2];
    const a = Math.atan2(ay - by, ax - bx);
    for (const da of [2.6, -2.6]) pen.line(ax, ay, ax + Math.cos(a + da) * 10, ay + Math.sin(a + da) * 10, { color: SPOT, width: 2.6 });
  }

  // ---- settings -----------------------------------------------------------------------

  function drawGround(pen, setting, land) {
    if (setting === "indoors") {
      pen.line(0, GROUND, W, GROUND, { width: 2 });
      pen.line(0, 150, W, 150, { width: 1, opacity: 0.35 });
      return;
    }
    if (setting === "city") {
      const skyline = [[0, 150], [40, 150], [40, 118], [78, 118], [78, 140], [120, 140], [120, 96], [150, 96], [150, 132],
        [205, 132], [205, 110], [250, 110], [250, 142], [330, 142], [330, 104], [362, 104], [362, 126], [420, 126],
        [420, 90], [446, 90], [446, 138], [500, 138], [500, 114], [548, 114], [548, 146], [600, 146]];
      pen.poly(skyline, { width: 1.4, opacity: 0.35 });
    }
    // Sea scenes still need dry land wherever someone is standing off the boats.
    for (let x = 0; x < W; x += 30) {
      if (setting === "sea" && !land(x + 15)) {
        pen.stroke(`M${x} ${GROUND + 3} q7.5 -7 15 0 q7.5 7 15 0`, { width: 1.8 });
      } else {
        pen.line(x, GROUND + pen.j(1), x + 30, GROUND + pen.j(1), { width: 2 });
        if (pen.rand() < 0.25) pen.line(x + 12, GROUND, x + 14, GROUND - 5, { width: 1.2 });
      }
    }
  }

  // ---- layout -------------------------------------------------------------------------

  function layout(scene) {
    // Things that share a spot are spread out around it; people on a ship's spot stand on its deck.
    const groups = {};
    const add = (item) => (groups[item.spot] ||= []).push(item);
    scene.props.filter((p) => !SKY.has(p.kind)).forEach((p) => add({ ...p, type: "prop" }));
    scene.figures.forEach((f) => add({ ...f, type: "figure" }));

    const placed = [];
    for (const [spot, items] of Object.entries(groups)) {
      const cx = SPOTS[spot] ?? SPOTS.center;
      const vessel = items.find((i) => i.type === "prop" && i.kind in VESSELS);
      const crew = vessel ? items.filter((i) => i.type === "figure") : [];
      const rest = items.filter((i) => i !== vessel && !crew.includes(i));
      if (vessel) {
        placed.push({ ...vessel, x: cx });
        crew.forEach((f, i) => placed.push({ ...f, x: cx + (i - (crew.length - 1) / 2) * 30, deck: VESSELS[vessel.kind] }));
      }
      const offset = vessel ? 80 : 0;
      rest.forEach((item, i) => {
        const dx = vessel ? offset * (i % 2 ? -1 : 1) * (1 + Math.floor(i / 2)) : (i - (rest.length - 1) / 2) * 70;
        placed.push({ ...item, x: Math.max(36, Math.min(W - 36, cx + dx)) });
      });
    }
    return placed;
  }

  function wrap(text, width = 18) {
    const lines = [];
    let line = "";
    for (const word of text.split(/\s+/)) {
      if (line && (line + " " + word).length > width) { lines.push(line); line = word; }
      else line = line ? line + " " + word : word;
    }
    if (line) lines.push(line);
    return lines;
  }

  function drawBubbles(pen, bubbles) {
    const boxes = [];
    for (const b of bubbles) {
      const lines = wrap(b.text);
      const w = Math.max(...lines.map((l) => l.length)) * 7.4 + 22, h = lines.length * 17 + 12;
      let x = Math.max(6, Math.min(W - w - 6, b.head[0] + b.dir * 14 - (b.dir < 0 ? w : 0)));
      let y = Math.max(6, b.top - h - 18);
      for (const other of boxes) {
        const overlaps = x < other.x + other.w + 6 && other.x < x + w + 6 && y < other.y + other.h + 6 && other.y < y + h + 6;
        if (!overlaps) continue;
        // Stack above the other bubble if there's room, otherwise below it.
        y = other.y - h - 8 >= 6 ? other.y - h - 8 : other.y + other.h + 8;
      }
      boxes.push({ x, y, w, h });
      const tx = Math.max(x + 10, Math.min(x + w - 10, b.head[0] + b.dir * 6));
      pen.poly([[tx - 6, y + h - 1], [b.head[0] + b.dir * 8, b.top - 2], [tx + 6, y + h - 1]], { width: 1.6 });
      pen.blob(x + w / 2, y + h / 2, w / 2 + 4, h / 2 + 3, { width: 1.8, rough: 0.025 });
      lines.forEach((l, i) => pen.text(x + w / 2, y + 20 + i * 17, l, { size: 15 }));
    }
  }

  // ---- entry point --------------------------------------------------------------------

  function draw(scene, seedText) {
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", scene.caption);
    const pen = makePen(svg, hash(seedText));

    const placed = layout(scene);
    const standing = placed.filter((p) => p.type === "figure" && !p.deck).map((p) => p.x);
    drawGround(pen, scene.setting, (x) => standing.some((sx) => Math.abs(sx - x) < 45));

    scene.props.filter((p) => SKY.has(p.kind)).forEach((p) => PROPS[p.kind](pen, SPOTS[p.spot] ?? SPOTS.center));
    const props = placed.filter((p) => p.type === "prop" && PROPS[p.kind]);
    props.filter((p) => p.kind === "hill").forEach((p) => PROPS.hill(pen, p.x, GROUND));
    props.filter((p) => p.kind !== "hill").forEach((p) => PROPS[p.kind](pen, p.x, GROUND + (p.kind in VESSELS ? 6 : 0)));

    const bubbles = [];
    for (const fig of placed.filter((p) => p.type === "figure")) {
      const base = GROUND - (fig.deck || 0) + (fig.deck ? 6 : 0);
      const { head, top } = drawFigure(pen, fig, fig.x, base);
      if (fig.says) bubbles.push({ text: fig.says, head, top, dir: fig.facing === "left" ? -1 : 1 });
    }

    const labels = placed.filter((p) => p.label);
    labels.sort((a, b) => a.x - b.x).forEach((p, i) => {
      const prev = labels[i - 1];
      const y = prev && Math.abs(prev.x - p.x) < 70 && prev.y === GROUND + 24 ? GROUND + 42 : GROUND + 24;
      p.y = y;
      pen.text(p.x, y, p.label, { size: 15 });
    });

    drawBubbles(pen, bubbles);
    return svg;
  }

  return { draw };
})();

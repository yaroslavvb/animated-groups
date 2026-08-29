/* Symmetric Brownian hard discs on a wallpaper quotient.
 *
 * Only the asymmetric-unit representatives below carry state.  A visible ball
 * is A(x_i) for a wallpaper operation A and a lattice translation, so the
 * rendered configuration is exactly invariant at every frame; no independently
 * integrated clone is allowed to drift away from its orbit.
 *
 * A collision is likewise solved on the quotient.  For two representatives,
 * the contact constraint between x_i and A(x_j) has velocity gradient
 *
 *     J = (n, -Q^T n),
 *
 * where Q is A's Cartesian orthogonal part.  For a representative meeting its
 * own image, the two entries refer to the same degree of freedom and combine to
 * J = n - Q^T n.  Applying impulses through those gradients makes mirrors act
 * like walls and rotation images exchange momentum without ever breaking the
 * selected wallpaper symmetry.
 */
"use strict";

export const DENSITIES = {
  sparse:   { label: "Sparse", target: 11, packing: 0.105 },
  balanced: { label: "Balanced", target: 17, packing: 0.155 },
  lively:   { label: "Lively", target: 23, packing: 0.195 },
};

const TWO_PI = Math.PI * 2;
const EPS = 1e-9;
const RESTITUTION = 0.94;
const SOLVER_PASSES = 3;
const SPEED_FACTORS = [0.20, 0.31, 0.45, 0.65, 0.95, 1.35];

const clamp = (x, lo, hi) => (x < lo ? lo : x > hi ? hi : x);

export const applyM = (M, u) => [
  M[0][0] * u[0] + M[0][1] * u[1],
  M[1][0] * u[0] + M[1][1] * u[1],
];

export const cart = (B, u) => [
  u[0] * B[0][0] + u[1] * B[1][0],
  u[0] * B[0][1] + u[1] * B[1][1],
];

export function latticeOf(B, p) {
  const det = B[0][0] * B[1][1] - B[0][1] * B[1][0];
  return [
    (p[0] * B[1][1] - p[1] * B[1][0]) / det,
    (p[1] * B[0][0] - p[0] * B[0][1]) / det,
  ];
}

const applyR = (R, p) => [
  R[0][0] * p[0] + R[0][1] * p[1],
  R[1][0] * p[0] + R[1][1] * p[1],
];

const applyRT = (R, p) => [
  R[0][0] * p[0] + R[1][0] * p[1],
  R[0][1] * p[0] + R[1][1] * p[1],
];

const det2 = (M) => M[0][0] * M[1][1] - M[0][1] * M[1][0];

const inverseInteger = (M) => {
  const d = det2(M);
  return [[M[1][1] / d, -M[0][1] / d],
          [-M[1][0] / d, M[0][0] / d]];
};

const isIdentityM = (M) => (
  M[0][0] === 1 && M[0][1] === 0 && M[1][0] === 0 && M[1][1] === 1
);

const rounded = (x) => Math.round(x * 1e9);
const affineKey = (M, w) => [
  M[0][0], M[0][1], M[1][0], M[1][1], rounded(w[0]), rounded(w[1]),
].join(",");

/* One of A and A^-1 represents a self-image contact orbit.  Equality is kept:
 * reflections and half-turns can be their own inverse and are real contacts. */
function canonicalSelf(M, w) {
  const Mi = inverseInteger(M);
  const z = applyM(Mi, w);
  const wi = [-z[0], -z[1]];
  return affineKey(M, w) <= affineKey(Mi, wi);
}

/* Small deterministic generator: regeneration links a visible seed to the
 * exact candidate the optimizer tested, while remaining independent of the
 * browser's global Math.random state. */
export class Random {
  constructor(seed = 1) {
    this.state = (seed >>> 0) || 0x6d2b79f5;
    this.spare = null;
  }

  uniform() {
    let t = this.state += 0x6d2b79f5;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    const out = ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    this.state >>>= 0;
    return out;
  }

  normal() {
    if (this.spare !== null) {
      const z = this.spare;
      this.spare = null;
      return z;
    }
    const u = Math.max(1e-12, this.uniform());
    const a = TWO_PI * this.uniform();
    const r = Math.sqrt(-2 * Math.log(u));
    this.spare = r * Math.sin(a);
    return r * Math.cos(a);
  }

  clone() {
    const out = new Random(1);
    out.state = this.state >>> 0;
    out.spare = this.spare;
    return out;
  }
}

/* Convert a catalog product group to the metric used by the simulator.  The
 * catalog bases vary in area because their aspect ratios were optimized for
 * motifs; a uniform normalization makes density and speed comparable while
 * preserving every isometry and affine operation. */
export function prepareWallpaper(raw, meta = {}) {
  const render = raw.render || raw;
  const sourceB = render.basis;
  const sourceArea = Math.abs(det2(sourceB));
  const scale = 1 / Math.sqrt(sourceArea);
  const basis = sourceB.map((row) => row.map((x) => x * scale));

  const ex = latticeOf(basis, [1, 0]);
  const ey = latticeOf(basis, [0, 1]);
  const ops = render.ops.map((source, index) => {
    const cx = cart(basis, applyM(source.M, ex));
    const cy = cart(basis, applyM(source.M, ey));
    const R = [[cx[0], cy[0]], [cx[1], cy[1]]];
    const residual = Math.max(
      Math.abs(R[0][0] * R[0][0] + R[1][0] * R[1][0] - 1),
      Math.abs(R[0][1] * R[0][1] + R[1][1] * R[1][1] - 1),
      Math.abs(R[0][0] * R[0][1] + R[1][0] * R[1][1]),
    );
    return {
      M: source.M,
      v: source.v,
      s: source.s ?? 1,
      tau: source.tau ?? 0,
      R,
      index,
      identity: isIdentityM(source.M) &&
        Math.abs(source.v[0] - Math.round(source.v[0])) < EPS &&
        Math.abs(source.v[1] - Math.round(source.v[1])) < EPS,
      residual,
    };
  });

  const identity = ops.findIndex((op) => op.identity);
  if (identity < 0) throw new Error(`brownian: ${meta.hm || raw.base} has no identity operation`);
  const residual = Math.max(...ops.map((op) => op.residual));
  if (residual > 1e-8) {
    throw new Error(`brownian: ${meta.hm || raw.base} basis is not isometric (${residual})`);
  }

  return {
    id: raw.id,
    hm: meta.hm || raw.base,
    orb: meta.orb || raw.symbol,
    note: meta.note || "",
    basis,
    area: 1,
    ops,
    identity,
    residual,
  };
}

function nearestImages(group, target, source, visit) {
  for (const op of group.ops) {
    const base = applyM(op.M, source);
    base[0] += op.v[0];
    base[1] += op.v[1];
    const c0 = Math.round(target[0] - base[0]);
    const c1 = Math.round(target[1] - base[1]);
    for (let a = -1; a <= 1; a++) {
      for (let b = -1; b <= 1; b++) visit(op, base, c0 + a, c1 + b);
    }
  }
}

function roomFor(group, u, seated) {
  const p = cart(group.basis, u);
  let room = Infinity;

  nearestImages(group, u, u, (op, base, m0, m1) => {
    if (op.identity && !m0 && !m1) return;
    const q = cart(group.basis, [base[0] + m0, base[1] + m1]);
    room = Math.min(room, Math.hypot(p[0] - q[0], p[1] - q[1]));
  });

  for (const other of seated) {
    nearestImages(group, u, other, (_op, base, m0, m1) => {
      const q = cart(group.basis, [base[0] + m0, base[1] + m1]);
      room = Math.min(room, Math.hypot(p[0] - q[0], p[1] - q[1]));
    });
  }
  return room;
}

function cloneParticles(particles) {
  return particles.map((p) => ({ u: [...p.u], v: [...p.v], colour: p.colour }));
}

export class BrownianWorld {
  constructor(group, opts = {}) {
    this.group = group;
    this.density = opts.density || "balanced";
    this.temperature = opts.temperature ?? 1;
    this.damping = 0.72;
    this.elapsed = 0;
    this.liveElapsed = 0;
    this.collisionTimes = [];
    this.flashes = [];
    this.history = [];
    this.historyTick = 0;
    this.optimizedRate = 0;
    this.optimizedMs = 0;
    this.seed = 1;
    this.particles = [];
  }

  setTemperature(value) {
    this.temperature = clamp(Number(value) || 1, 0.35, 1.9);
  }

  setDensity(name) {
    if (DENSITIES[name]) this.density = name;
  }

  /* Best-candidate seating followed by invisible dynamics probes.  Every speed
   * trial starts from the same positions, velocity directions and random-noise
   * stream, so the comparison measures the thermostat rather than six lucky
   * layouts.  After burn-in, keep the speed nearest a density-scaled impact
   * rate; persisting that speed makes the live motion remain representative
   * after Brownian forcing has forgotten the initial frame. */
  regenerate(seed = 1) {
    const started = typeof performance === "object" ? performance.now() : Date.now();
    this.seed = (seed >>> 0) || 1;
    const density = DENSITIES[this.density];
    const copies = this.group.ops.length;
    const count = clamp(Math.round(density.target / copies), 1, 20);
    const nominalBalls = count * copies;
    const desiredRadius = Math.sqrt(density.packing / (Math.PI * nominalBalls));
    const candidates = [];
    const rng = new Random(this.seed);
    const seated = [];
    let tightest = Infinity;
    for (let i = 0; i < count; i++) {
      let best = null;
      let bestRoom = -1;
      for (let k = 0; k < 84; k++) {
        const u = [rng.uniform(), rng.uniform()];
        const room = roomFor(this.group, u, seated);
        if (room > bestRoom) {
          bestRoom = room;
          best = u;
        }
      }
      seated.push(best);
      tightest = Math.min(tightest, bestRoom);
    }

    const radius = Math.min(desiredRadius, tightest / 2.16);
    const velocitySeeds = seated.map((u, i) => ({
      u: [...u],
      angle: TWO_PI * rng.uniform(),
      speedScale: 0.72 + 0.56 * rng.uniform(),
      colour: i,
    }));
    const dynamicsRng = rng.clone();
    /* Aim for roughly 0.8 collision involvements per independent particle per
     * second.  Counting quotient collision orbits keeps high-order groups from
     * being over-energized merely because each event has many visible copies. */
    const targetRate = clamp(0.4 * count, 1.4, 6.5);

    for (let c = 0; c < SPEED_FACTORS.length; c++) {
      const targetSpeed = this._baseSpeed(radius, nominalBalls) * SPEED_FACTORS[c];
      const particles = velocitySeeds.map((source) => {
        const speed = targetSpeed * source.speedScale;
        return {
          u: [...source.u],
          v: [speed * Math.cos(source.angle), speed * Math.sin(source.angle)],
          colour: source.colour,
        };
      });
      if (particles.length > 1) {
        const mean = particles.reduce((s, p) => [s[0] + p.v[0], s[1] + p.v[1]], [0, 0]);
        mean[0] /= particles.length;
        mean[1] /= particles.length;
        for (const p of particles) {
          p.v[0] -= mean[0];
          p.v[1] -= mean[1];
        }
      }

      this.radius = radius;
      this.targetSpeed = targetSpeed;
      this.particles = particles;
      this.rng = dynamicsRng.clone();
      const dt = 1 / 120;
      const burnSeconds = 1;
      for (let k = 0; k < Math.round(burnSeconds / dt); k++) this._advance(dt, false);
      let impacts = 0;
      const probeSeconds = 2.5;
      for (let k = 0; k < Math.round(probeSeconds / dt); k++) {
        impacts += this._advance(dt, false);
      }
      const rate = impacts / probeSeconds;
      const score = Math.abs(Math.log((rate + 0.35) / (targetRate + 0.35))) +
        (rate === 0 ? 0.75 : 0);
      candidates.push({
        score,
        rate,
        radius,
        targetSpeed,
        particles: cloneParticles(this.particles),
        rng: this.rng.clone(),
      });
    }

    candidates.sort((a, b) => a.score - b.score);
    const best = candidates[0];
    this.radius = best.radius;
    this.targetSpeed = best.targetSpeed;
    this.particles = cloneParticles(best.particles);
    this.rng = best.rng;
    this.optimizedRate = best.rate;
    this.targetRate = targetRate;
    this.elapsed = 0;
    this.liveElapsed = 0;
    this.collisionTimes = [];
    this.flashes = [];
    this.history = [this.particles.map((p) => [...p.u])];
    this.historyTick = 0;
    const ended = typeof performance === "object" ? performance.now() : Date.now();
    this.optimizedMs = ended - started;
    return this.summary();
  }

  _baseSpeed(radius, balls) {
    /* A kinetic-theory starting point, capped so small discs do not become
     * bullets.  The probe above chooses a typical collision-rate realization. */
    return clamp(0.17 + 0.85 * radius + 0.0025 * balls, 0.19, 0.31);
  }

  step(dt) {
    const impacts = this._advance(dt, true);
    this.elapsed += dt;
    this.liveElapsed += dt;
    for (let i = 0; i < impacts; i++) this.collisionTimes.push(this.liveElapsed);
    const cutoff = this.liveElapsed - 4;
    while (this.collisionTimes.length && this.collisionTimes[0] < cutoff) {
      this.collisionTimes.shift();
    }
    for (const f of this.flashes) f.age += dt;
    this.flashes = this.flashes.filter((f) => f.age < 0.34);

    this.historyTick++;
    if (this.historyTick % 3 === 0) {
      this.history.push(this.particles.map((p) => [...p.u]));
      if (this.history.length > 30) this.history.shift();
    }
    return impacts;
  }

  collisionRate() {
    if (this.liveElapsed < 0.8) return this.optimizedRate;
    const window = Math.min(4, this.liveElapsed);
    return this.collisionTimes.length / Math.max(window, EPS);
  }

  summary() {
    return {
      group: this.group.hm,
      representatives: this.particles.length,
      ballsPerCell: this.particles.length * this.group.ops.length,
      radius: this.radius,
      optimizedRate: this.optimizedRate,
      targetRate: this.targetRate,
      optimizedMs: this.optimizedMs,
      residual: this.group.residual,
      seed: this.seed,
    };
  }

  _advance(dt, emit) {
    const decay = Math.exp(-this.damping * dt);
    const componentStd = this.targetSpeed * this.temperature / Math.sqrt(2);
    const noise = componentStd * Math.sqrt(Math.max(0, 1 - decay * decay));
    for (const p of this.particles) {
      p.v[0] = decay * p.v[0] + noise * this.rng.normal();
      p.v[1] = decay * p.v[1] + noise * this.rng.normal();
      const du = latticeOf(this.group.basis, [p.v[0] * dt, p.v[1] * dt]);
      p.u[0] += du[0];
      p.u[1] += du[1];
    }

    let impacts = 0;
    for (let pass = 0; pass < SOLVER_PASSES; pass++) {
      impacts += this._solvePass(pass === 0 && emit, pass === 0);
    }
    return impacts;
  }

  _solvePass(emit, count) {
    const B = this.group.basis;
    const diameter = 2 * this.radius;
    const diameter2 = diameter * diameter;
    let impacts = 0;

    for (let i = 0; i < this.particles.length; i++) {
      const a = this.particles[i];
      for (let j = i; j < this.particles.length; j++) {
        const b = this.particles[j];
        nearestImages(this.group, a.u, b.u, (op, base, m0, m1) => {
          if (i === j) {
            if (op.identity && !m0 && !m1) return;
            const w = [op.v[0] + m0, op.v[1] + m1];
            if (!canonicalSelf(op.M, w)) return;
            /* Translational copies of one representative have equal velocity
             * and fixed separation, so there is no dynamical constraint. */
            if (op.identity) return;
          }

          const pa = cart(B, a.u);
          const qb = cart(B, [base[0] + m0, base[1] + m1]);
          let dx = pa[0] - qb[0];
          let dy = pa[1] - qb[1];
          const d2 = dx * dx + dy * dy;
          if (d2 >= diameter2) return;
          let d = Math.sqrt(d2);
          if (d < 1e-10) {
            const theta = TWO_PI * this.rng.uniform();
            dx = Math.cos(theta);
            dy = Math.sin(theta);
            d = 1;
          }
          const n = [dx / d, dy / d];
          const rt = applyRT(op.R, n);
          const penetration = diameter - Math.sqrt(d2);

          if (i !== j) {
            const vb = applyR(op.R, b.v);
            const relative = (a.v[0] - vb[0]) * n[0] + (a.v[1] - vb[1]) * n[1];
            if (relative < -1e-5) {
              const impulse = -(1 + RESTITUTION) * relative / 2;
              a.v[0] += impulse * n[0];
              a.v[1] += impulse * n[1];
              b.v[0] -= impulse * rt[0];
              b.v[1] -= impulse * rt[1];
              if (count) impacts++;
              if (emit) this._flash(pa, qb);
            }
            const push = 0.52 * Math.max(0, penetration + 1e-6);
            const ca = [push * n[0], push * n[1]];
            const cb = [-push * rt[0], -push * rt[1]];
            const ua = latticeOf(B, ca);
            const ub = latticeOf(B, cb);
            a.u[0] += ua[0]; a.u[1] += ua[1];
            b.u[0] += ub[0]; b.u[1] += ub[1];
          } else {
            const J = [n[0] - rt[0], n[1] - rt[1]];
            const jj = J[0] * J[0] + J[1] * J[1];
            if (jj < 1e-10) return;
            const relative = J[0] * a.v[0] + J[1] * a.v[1];
            if (relative < -1e-5) {
              const impulse = -(1 + RESTITUTION) * relative / jj;
              a.v[0] += impulse * J[0];
              a.v[1] += impulse * J[1];
              if (count) impacts++;
              if (emit) this._flash(pa, qb);
            }
            const push = Math.max(0, penetration + 1e-6) / jj;
            const up = latticeOf(B, [push * J[0], push * J[1]]);
            a.u[0] += up[0]; a.u[1] += up[1];
          }
        });
      }
    }
    return impacts;
  }

  _flash(a, b) {
    const mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
    this.flashes.push({ u: latticeOf(this.group.basis, mid), age: 0 });
    if (this.flashes.length > 10) this.flashes.shift();
  }
}

/* Page controller and canvas renderer for symmetric Brownian motion. */
"use strict";

import { drawBall, elements, GROUND, PALETTE } from "./brownian-drawing.js?v=1";
import {
  BrownianWorld, DENSITIES, applyM, cart, latticeOf, prepareWallpaper,
} from "./brownian-physics.js?v=1";

const AXIS = "#6f7b76";
const GRID = "#d7deda";
const IMPACT = "#b64d43";
const MAX_FRAME = 0.1;
const FIXED_STEP = 1 / 120;
const MAX_STEPS = 12;
const TWO_PI = Math.PI * 2;

const el = (id) => document.getElementById(id);
const orb = (s) => s === "o" ? "◦" : s;

const WALLPAPERS = [
  { hm: "p1", orb: "◦", note: "Translations only." },
  { hm: "p2", orb: "2222", note: "Four order-2 cone points." },
  { hm: "pm", orb: "**", note: "Two mirror boundaries." },
  { hm: "pg", orb: "××", note: "Two crosscaps; glide reflections, no mirrors." },
  { hm: "cm", orb: "*×", note: "One mirror boundary and one crosscap." },
  { hm: "pmm", orb: "*2222", note: "Four order-2 mirror corners." },
  { hm: "pmg", orb: "22*", note: "Two order-2 cone points and one mirror boundary." },
  { hm: "pgg", orb: "22×", note: "Two order-2 cone points and one crosscap." },
  { hm: "cmm", orb: "2*22", note: "One order-2 cone point and two order-2 mirror corners." },
  { hm: "p4", orb: "442", note: "Order-4, order-4, and order-2 cone points." },
  { hm: "p4m", orb: "*442", note: "Order-4, order-4, and order-2 mirror corners." },
  { hm: "p4g", orb: "4*2", note: "One order-4 cone point and one order-2 mirror corner." },
  { hm: "p3", orb: "333", note: "Three order-3 cone points." },
  { hm: "p3m1", orb: "*333", note: "Three order-3 mirror corners." },
  { hm: "p31m", orb: "3*3", note: "One order-3 cone point and one order-3 mirror corner." },
  { hm: "p6", orb: "632", note: "Order-6, order-3, and order-2 cone points." },
  { hm: "p6m", orb: "*632", note: "Order-6, order-3, and order-2 mirror corners." },
];

function freshSeed() {
  if (globalThis.crypto && typeof globalThis.crypto.getRandomValues === "function") {
    return globalThis.crypto.getRandomValues(new Uint32Array(1))[0] || 1;
  }
  return (Date.now() ^ Math.floor(Math.random() * 0xffffffff)) >>> 0 || 1;
}

function queryState() {
  const q = new URLSearchParams(location.search);
  const densityKey = q.get("density");
  const density = Object.prototype.hasOwnProperty.call(DENSITIES, densityKey)
    ? densityKey : "balanced";
  const rawSeed = Number(q.get("seed"));
  const seed = Number.isFinite(rawSeed) ? rawSeed >>> 0 : 0;
  const temperature = Math.max(0.35, Math.min(1.9, Number(q.get("temp")) || 1));
  return {
    hm: WALLPAPERS.some((w) => w.hm === q.get("g")) ? q.get("g") : "p4m",
    seed: seed || freshSeed(),
    density,
    temperature,
  };
}

class BrownianView {
  constructor(canvas, stage) {
    this.canvas = canvas;
    this.stage = stage;
    this.ctx = canvas.getContext("2d");
    this.world = null;
    this.showAxes = false;
    this.showTrails = true;
    this.w = 0;
    this.h = 0;
    this.dpr = 1;
    this.span = 3;
    this.axisCache = null;
  }

  setWorld(world) {
    this.world = world;
    this.axisCache = null;
    this.draw();
  }

  _fit() {
    const rect = this.canvas.getBoundingClientRect();
    const w = Math.max(1, rect.width);
    const h = Math.max(1, rect.height);
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    if (w !== this.w || h !== this.h || dpr !== this.dpr) {
      this.w = w;
      this.h = h;
      this.dpr = dpr;
      this.canvas.width = Math.round(w * dpr);
      this.canvas.height = Math.round(h * dpr);
    }
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (!this.world) return;

    const B = this.world.group.basis;
    const corners = [[0, 0], [1, 0], [0, 1], [1, 1]].map((u) => cart(B, u));
    const xs = corners.map((p) => p[0]);
    const ys = corners.map((p) => p[1]);
    const cellW = Math.max(...xs) - Math.min(...xs);
    const cellH = Math.max(...ys) - Math.min(...ys);
    this.scale = Math.min(w / (2.55 * cellW), h / (2.55 * cellH));
    this.center = cart(B, [0.5, 0.5]);

    let span = 1;
    for (const sx of [-1, 1]) {
      for (const sy of [-1, 1]) {
        const u = latticeOf(B, [sx * w / (2 * this.scale), sy * h / (2 * this.scale)]);
        span = Math.max(span, Math.ceil(Math.abs(u[0])), Math.ceil(Math.abs(u[1])));
      }
    }
    this.span = span + 1;
  }

  screen(p) {
    return [
      this.w / 2 + (p[0] - this.center[0]) * this.scale,
      this.h / 2 - (p[1] - this.center[1]) * this.scale,
    ];
  }

  draw() {
    this._fit();
    const ctx = this.ctx;
    ctx.fillStyle = GROUND;
    ctx.fillRect(0, 0, this.w, this.h);
    if (!this.world) return;
    this._grid();
    if (this.showAxes) this._axes();
    if (this.showTrails) this._trails();
    this._balls();
    this._flashes();
  }

  _grid() {
    const ctx = this.ctx;
    const B = this.world.group.basis;
    ctx.save();
    ctx.strokeStyle = GRID;
    ctx.globalAlpha = 0.54;
    ctx.lineWidth = 0.7;
    for (let m = -this.span; m <= this.span; m++) {
      for (let n = -this.span; n <= this.span; n++) {
        const corners = [[m, n], [m + 1, n], [m + 1, n + 1], [m, n + 1]];
        ctx.beginPath();
        corners.forEach((u, i) => {
          const p = this.screen(cart(B, u));
          ctx[i ? "lineTo" : "moveTo"](p[0], p[1]);
        });
        ctx.closePath();
        ctx.stroke();
      }
    }
    ctx.restore();
  }

  _elementData() {
    const key = `${this.world.group.hm}:${this.span}`;
    if (!this.axisCache || this.axisCache.key !== key) {
      this.axisCache = { key, ...elements(this.world.group.ops, this.span) };
    }
    return this.axisCache;
  }

  _axes() {
    const ctx = this.ctx;
    const B = this.world.group.basis;
    const { pts, lns } = this._elementData();
    const reach = 3 * (this.span + 1);
    ctx.save();
    ctx.strokeStyle = AXIS;
    ctx.fillStyle = AXIS;
    ctx.globalAlpha = 0.76;
    for (const line of lns) {
      ctx.lineWidth = line.glide ? 1.1 : 1.55;
      ctx.setLineDash(line.glide ? [6, 5] : []);
      const a = this.screen(cart(B, [line.base[0] - reach * line.d[0],
                                     line.base[1] - reach * line.d[1]]));
      const b = this.screen(cart(B, [line.base[0] + reach * line.d[0],
                                     line.base[1] + reach * line.d[1]]));
      ctx.beginPath();
      ctx.moveTo(a[0], a[1]);
      ctx.lineTo(b[0], b[1]);
      ctx.stroke();
    }
    ctx.setLineDash([]);
    for (const point of pts) {
      const p = this.screen(cart(B, point.c));
      if (p[0] < -10 || p[0] > this.w + 10 || p[1] < -10 || p[1] > this.h + 10) continue;
      const r = point.order >= 6 ? 4.5 : point.order >= 4 ? 4 : 3.4;
      ctx.beginPath();
      ctx.arc(p[0], p[1], r + 1.8, 0, TWO_PI);
      ctx.fillStyle = GROUND;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(p[0], p[1], r, 0, TWO_PI);
      ctx.fillStyle = AXIS;
      ctx.fill();
    }
    ctx.restore();
  }

  _translationsNear(u, visit) {
    const m0 = Math.round(0.5 - u[0]);
    const n0 = Math.round(0.5 - u[1]);
    for (let m = -this.span; m <= this.span; m++) {
      for (let n = -this.span; n <= this.span; n++) visit(m0 + m, n0 + n);
    }
  }

  _trails() {
    const history = this.world.history;
    if (history.length < 2) return;
    const ctx = this.ctx;
    const B = this.world.group.basis;
    ctx.save();
    ctx.lineCap = "round";
    ctx.lineWidth = Math.max(0.8, this.world.radius * this.scale * 0.16);
    for (let i = 0; i < this.world.particles.length; i++) {
      ctx.strokeStyle = PALETTE[i % PALETTE.length];
      for (const op of this.world.group.ops) {
        const latest = applyM(op.M, history[history.length - 1][i]);
        latest[0] += op.v[0]; latest[1] += op.v[1];
        this._translationsNear(latest, (m, n) => {
          for (let k = 1; k < history.length; k++) {
            const a = applyM(op.M, history[k - 1][i]);
            const b = applyM(op.M, history[k][i]);
            a[0] += op.v[0] + m; a[1] += op.v[1] + n;
            b[0] += op.v[0] + m; b[1] += op.v[1] + n;
            const pa = this.screen(cart(B, a));
            const pb = this.screen(cart(B, b));
            if ((pa[0] < -20 && pb[0] < -20) || (pa[0] > this.w + 20 && pb[0] > this.w + 20) ||
                (pa[1] < -20 && pb[1] < -20) || (pa[1] > this.h + 20 && pb[1] > this.h + 20)) continue;
            ctx.globalAlpha = 0.04 + 0.24 * k / history.length;
            ctx.beginPath();
            ctx.moveTo(pa[0], pa[1]);
            ctx.lineTo(pb[0], pb[1]);
            ctx.stroke();
          }
        });
      }
    }
    ctx.restore();
  }

  _balls() {
    const ctx = this.ctx;
    const B = this.world.group.basis;
    const R = Math.max(2, this.world.radius * this.scale);
    for (let i = 0; i < this.world.particles.length; i++) {
      const particle = this.world.particles[i];
      for (const op of this.world.group.ops) {
        const q = applyM(op.M, particle.u);
        q[0] += op.v[0]; q[1] += op.v[1];
        this._translationsNear(q, (m, n) => {
          const p = this.screen(cart(B, [q[0] + m, q[1] + n]));
          if (p[0] < -R - 2 || p[0] > this.w + R + 2 ||
              p[1] < -R - 2 || p[1] > this.h + R + 2) return;
          drawBall(ctx, p[0], p[1], R, PALETTE[i % PALETTE.length]);
        });
      }
    }
  }

  _flashes() {
    if (!this.world.flashes.length) return;
    const ctx = this.ctx;
    const B = this.world.group.basis;
    ctx.save();
    ctx.strokeStyle = IMPACT;
    for (const flash of this.world.flashes) {
      const alpha = Math.max(0, 1 - flash.age / 0.34);
      const rr = this.world.radius * this.scale * (1.7 + 5 * flash.age);
      ctx.globalAlpha = 0.72 * alpha;
      ctx.lineWidth = 1.6;
      for (const op of this.world.group.ops) {
        const q = applyM(op.M, flash.u);
        q[0] += op.v[0]; q[1] += op.v[1];
        this._translationsNear(q, (m, n) => {
          const p = this.screen(cart(B, [q[0] + m, q[1] + n]));
          if (p[0] < -rr || p[0] > this.w + rr || p[1] < -rr || p[1] > this.h + rr) return;
          ctx.beginPath();
          ctx.arc(p[0], p[1], rr, 0, TWO_PI);
          ctx.stroke();
        });
      }
    }
    ctx.restore();
  }
}

const state = queryState();
const select = el("wallpaper-group");
for (const w of WALLPAPERS) {
  const option = document.createElement("option");
  option.value = w.hm;
  option.textContent = `${orb(w.orb)} · ${w.hm} — ${w.note.split(" — ")[0]}`;
  select.append(option);
}

const metaBy = new Map(WALLPAPERS.map((w) => [w.hm, w]));
const groups = new Map();
try {
  const response = await fetch("data/clockwork-coloring-correspondence.json",
    { cache: "no-cache" });
  if (!response.ok) {
    throw new Error(`brownian: group data request failed (${response.status})`);
  }
  const catalog = await response.json();
  for (const w of WALLPAPERS) {
    const raw = catalog.groups.find((g) => (
      g.parent?.hm === w.hm && g.clock_order === 1 && g.product
    ));
    if (!raw) throw new Error(`brownian: missing wallpaper product ${w.hm}`);
    groups.set(w.hm, prepareWallpaper(raw, w));
  }
} catch (error) {
  const message = "The wallpaper-group data could not be loaded. Reload the page to try again.";
  el("group-note").textContent = message;
  el("generation-status").textContent = message;
  document.querySelector(".brownian-lab").setAttribute("aria-busy", "false");
  el("brownian-stage").setAttribute("aria-disabled", "true");
  el("brownian-stage").setAttribute("aria-label", "Symmetric Brownian motion unavailable");
  console.error(error);
  throw error;
}

const stage = el("brownian-stage");
const canvas = el("brownian-canvas");
const view = new BrownianView(canvas, stage);
let world = null;
let running = false;
let frame = 0;
let last = null;
let accumulator = 0;
let statsAt = 0;
let current = { ...state };
let generationSerial = 0;
let generating = false;

function setGenerating(value) {
  generating = !!value;
  document.querySelector(".brownian-lab").setAttribute("aria-busy", String(generating));
  stage.setAttribute("aria-disabled", String(generating));
  document.querySelectorAll(
    ".brownian-toolbar button, .brownian-toolbar select, .brownian-toolbar input, " +
    "#brownian-play, [data-density], #temperature",
  ).forEach((node) => { node.disabled = generating; });
}

function writeUrl(mode = "replace") {
  const q = new URLSearchParams();
  q.set("g", current.hm);
  q.set("seed", String(current.seed >>> 0));
  if (current.density !== "balanced") q.set("density", current.density);
  if (Math.abs(current.temperature - 1) > 1e-6) q.set("temp", current.temperature.toFixed(2));
  history[mode === "push" ? "pushState" : "replaceState"]({}, "", `${location.pathname}?${q}`);
}

function setRunning(value) {
  running = !!value;
  const play = el("brownian-play");
  play.querySelector(".icon").textContent = running ? "■" : "▶";
  play.querySelector(".label").textContent = running ? "Pause" : "Play";
  stage.querySelector(".stage-hint").textContent = running
    ? "click the field or press space to pause"
    : "click the field or press space to play";
  last = null;
  accumulator = 0;
  updateStageLabel();
  if (running && !frame) frame = requestAnimationFrame(tick);
  if (!running) view.draw();
}

function updateStageLabel() {
  if (!world) return;
  const action = running ? "playing; press Space to pause" : "paused; press Space to play";
  stage.setAttribute("aria-label", `${orb(world.group.orb)} ${world.group.hm} symmetric Brownian motion, ${action}. ` +
    `${world.summary().ballsPerCell} balls per lattice cell.`);
}

function updateStats(force = false) {
  if (!world) return;
  const now = performance.now();
  if (!force && now - statsAt < 220) return;
  statsAt = now;
  const info = world.summary();
  el("stat-independent").textContent = String(info.representatives);
  el("stat-balls").textContent = String(info.ballsPerCell);
  el("stat-collisions").textContent = `${world.collisionRate().toFixed(1)} / s`;
  el("stat-symmetry").textContent = info.residual < 1e-10 ? "exact orbit" : `≤ ${info.residual.toExponential(1)}`;
}

function syncControls() {
  select.value = current.hm;
  el("temperature").value = String(current.temperature);
  el("temperature-out").textContent = `${current.temperature.toFixed(2)}×`;
  for (const button of document.querySelectorAll("[data-density]")) {
    button.setAttribute("aria-pressed", String(button.dataset.density === current.density));
  }
}

async function regenerate({ announce = true } = {}) {
  const serial = ++generationSerial;
  const requested = { ...current };
  const group = groups.get(requested.hm);
  if (!group) return;
  setGenerating(true);
  el("generation-status").textContent = "Optimizing a symmetric start…";
  /* A frame paints the busy state before the synchronous, sub-second search
   * begins.  The second callback resumes after that painted frame. */
  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  if (serial !== generationSerial) return;
  world = new BrownianWorld(group, {
    density: requested.density,
    temperature: requested.temperature,
  });
  const info = world.regenerate(requested.seed);
  view.setWorld(world);
  last = null;
  accumulator = 0;
  const meta = metaBy.get(requested.hm);
  el("group-symbol").textContent = orb(meta.orb);
  el("group-name").textContent = meta.hm;
  el("group-note").textContent = meta.note;
  el("optimizer-copy").textContent =
    `${info.representatives} independent particles generate ${info.ballsPerCell} balls per cell. ` +
    `Six thermostat speeds were tested in ${Math.round(info.optimizedMs)} ms; the selected trial produced ` +
    `${info.optimizedRate.toFixed(1)} collision orbits per second ` +
    `(target ${info.targetRate.toFixed(1)}).`;
  el("generation-status").textContent = announce
    ? `New ${meta.hm} motion ready, seed ${requested.seed}.`
    : "";
  setGenerating(false);
  updateStats(true);
  updateStageLabel();
}

function tick(now) {
  frame = 0;
  if (!running) return;
  if (last === null) last = now;
  accumulator += Math.min(MAX_FRAME, Math.max(0, (now - last) / 1000));
  last = now;
  let steps = 0;
  while (accumulator >= FIXED_STEP && steps < MAX_STEPS) {
    world.step(FIXED_STEP);
    accumulator -= FIXED_STEP;
    steps++;
  }
  if (steps === MAX_STEPS) accumulator = 0;
  view.draw();
  updateStats();
  frame = requestAnimationFrame(tick);
}

function chooseGroup(hm, mode = "push") {
  current.hm = hm;
  current.seed = freshSeed();
  writeUrl(mode);
  syncControls();
  regenerate();
}

select.addEventListener("change", () => chooseGroup(select.value));
el("brownian-new").addEventListener("click", () => {
  current.seed = freshSeed();
  writeUrl("push");
  regenerate();
});
el("brownian-play").addEventListener("click", () => setRunning(!running));
el("show-axes").addEventListener("change", (event) => {
  view.showAxes = event.target.checked;
  view.draw();
});
el("show-trails").addEventListener("change", (event) => {
  view.showTrails = event.target.checked;
  view.draw();
});
el("temperature").addEventListener("input", (event) => {
  current.temperature = Number(event.target.value);
  world.setTemperature(current.temperature);
  el("temperature-out").textContent = `${current.temperature.toFixed(2)}×`;
});
el("temperature").addEventListener("change", () => writeUrl("replace"));
for (const button of document.querySelectorAll("[data-density]")) {
  button.addEventListener("click", () => {
    if (button.dataset.density === current.density) return;
    current.density = button.dataset.density;
    current.seed = freshSeed();
    writeUrl("push");
    syncControls();
    regenerate();
  });
}

stage.addEventListener("click", (event) => {
  if (generating) return;
  if (event.target === canvas || event.target.closest(".stage-overlay")) setRunning(!running);
});
stage.addEventListener("keydown", (event) => {
  if (generating) return;
  if (event.key !== " " && event.key !== "Enter") return;
  event.preventDefault();
  setRunning(!running);
});

window.addEventListener("popstate", () => {
  current = queryState();
  syncControls();
  regenerate({ announce: false });
});
document.addEventListener("visibilitychange", () => { last = null; accumulator = 0; });
new ResizeObserver(() => view.draw()).observe(canvas);

syncControls();
writeUrl("replace");
await regenerate({ announce: false });
setRunning(false);

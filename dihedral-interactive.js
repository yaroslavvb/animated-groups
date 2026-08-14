/* Dihedral Interactive Explorer — Core Engine
 * Interactive visualization of dihedral group symmetries, subgroups, cosets,
 * and cyclic spacetime clockwork lifts.
 */
"use strict";

// Accessible Okabe-Ito palette (extended for up to 24 colors)
export const OKABE_PALETTE = [
  "#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00",
  "#56B4E9", "#F0E442", "#4d4d4d", "#8c564b", "#1f9e8f",
  "#7f3fbf", "#a6a413", "#2ca02c", "#d62728", "#9467bd",
  "#e377c2", "#7f7f7f", "#bcbd22", "#17becf", "#aec7e8",
  "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5"
];

const GROUND = "#faf9f6";
const RULE = "#c9c3b4";
const RULE_FAINT = "#e2ded6";
const EDGE = "#2c3848";

// ------------------------------------------------------------- Motifs
function bez(chain, n = 18) {
  const pts = [];
  for (const [p0, p1, p2, p3] of chain) {
    for (let i = 0; i < n; i++) {
      const t = i / n, m = 1 - t;
      pts.push([
        m * m * m * p0[0] + 3 * m * m * t * p1[0] + 3 * m * t * t * p2[0] + t ** 3 * p3[0],
        m * m * m * p0[1] + 3 * m * m * t * p1[1] + 3 * m * t * t * p2[1] + t ** 3 * p3[1],
      ]);
    }
  }
  return pts;
}

function normalizeShape(subs, R = 0.64) {
  const all = subs.flat();
  const xs = all.map(p => p[0]), ys = all.map(p => p[1]);
  const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
  const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
  const k = R / Math.max(...all.map(p => Math.hypot(p[0] - cx, p[1] - cy)));
  return subs.map(s => s.map(p => [(p[0] - cx) * k, (p[1] - cy) * k]));
}

const COMMA_PTS = normalizeShape([bez([
  [[0.40, -0.30], [0.52, 0.18], [0.32, 0.56], [-0.52, 0.74]],
  [[-0.52, 0.74], [-0.10, 0.52], [0.18, 0.26], [0.06, 0.02]],
  [[0.06, 0.02], [-0.14, 0.02], [-0.40, -0.10], [-0.40, -0.30]],
  [[-0.40, -0.30], [-0.40, -0.54], [-0.22, -0.68], [0.00, -0.68]],
  [[0.00, -0.68], [0.24, -0.68], [0.40, -0.54], [0.40, -0.30]],
])]);

const R_LETTER_PTS = normalizeShape([
  [[-0.46, -0.70], [0.14, -0.70], [0.34, -0.60], [0.42, -0.40], [0.42, -0.22],
   [0.34, -0.04], [0.18, 0.04], [0.48, 0.70], [0.14, 0.70], [-0.10, 0.10],
   [-0.16, 0.10], [-0.16, 0.70], [-0.46, 0.70]],
  [[-0.16, -0.22], [0.08, -0.22], [0.16, -0.28], [0.16, -0.38],
   [0.08, -0.44], [-0.16, -0.44]],
]);

const DART_PTS = normalizeShape([
  [[-0.45, -0.65], [0.55, -0.15], [-0.15, 0.05], [0.35, 0.65], [-0.45, 0.25]]
]);

export function drawMotifPath(ctx, r, style = "comma") {
  const shape = style === "letter" ? R_LETTER_PTS : (style === "dart" ? DART_PTS : COMMA_PTS);
  ctx.beginPath();
  for (const sub of shape) {
    ctx.moveTo(sub[0][0] * r, sub[0][1] * r);
    for (let i = 1; i < sub.length; i++) {
      ctx.lineTo(sub[i][0] * r, sub[i][1] * r);
    }
    ctx.closePath();
  }
}

// ------------------------------------------------------------- Dihedral Algebra
export class DihedralGroup {
  constructor(n) {
    this.n = n;
    this.order = 2 * n;
    this.elements = [];
    for (let f = 0; f < 2; f++) {
      for (let k = 0; k < n; k++) {
        this.elements.push([k, f]);
      }
    }
    this.identity = [0, 0];
    this.invMap = new Map();
    for (const g of this.elements) {
      this.invMap.set(this.key(g), this.inv(g));
    }
    this.subgroups = this.enumerateSubgroups();
    this.conjugacyClasses = this.classifySubgroups(this.subgroups);
  }

  key(g) {
    return `${g[0]},${g[1]}`;
  }

  name(g) {
    const k = g[0];
    const f = g[1];
    let rPart = "";
    if (k === 1) rPart = "r";
    else if (k > 1) rPart = `r${k}`;
    
    if (f === 1) {
      return rPart ? `${rPart}s` : "s";
    }
    return rPart || "1";
  }

  htmlName(g) {
    const k = g[0];
    const f = g[1];
    let rPart = "";
    if (k === 1) rPart = "<i>r</i>";
    else if (k > 1) rPart = `<i>r</i><sup>${k}</sup>`;
    
    if (f === 1) {
      return rPart ? `${rPart}<i>s</i>` : "<i>s</i>";
    }
    return rPart || "1";
  }

  mul(a, b) {
    const k = (a[0] + (a[1] === 0 ? b[0] : -b[0]) + 2 * this.n) % this.n;
    const f = (a[1] + b[1]) % 2;
    return [k, f];
  }

  inv(g) {
    if (g[1] === 1) return [g[0], 1]; // reflections are self-inverse
    return [(this.n - g[0]) % this.n, 0];
  }

  matrix(g) {
    const theta = (g[0] * 2 * Math.PI) / this.n;
    const c = Math.cos(theta);
    const s = Math.sin(theta);
    const R = [[c, -s], [s, c]];
    if (g[1] === 1) {
      // Reflect across x-axis, then rotate by theta
      return [[R[0][0], -R[0][1]], [R[1][0], -R[1][1]]];
    }
    return R;
  }

  close(generators) {
    const visited = new Map([[this.key(this.identity), this.identity]]);
    const queue = [this.identity];
    while (queue.length > 0) {
      const curr = queue.pop();
      for (const gen of generators) {
        const next = this.mul(curr, gen);
        const k = this.key(next);
        if (!visited.has(k)) {
          visited.set(k, next);
          queue.push(next);
        }
      }
    }
    return [...visited.values()].sort((a, b) => a[1] - b[1] || a[0] - b[0]);
  }

  sig(H) {
    return H.map(g => this.key(g)).sort().join("|");
  }

  conjugate(H, g) {
    const gInv = this.inv(g);
    return H.map(h => this.mul(this.mul(g, h), gInv))
      .sort((a, b) => a[1] - b[1] || a[0] - b[0]);
  }

  enumerateSubgroups() {
    const subs = new Map();
    // Subgroups generated by 1 or 2 elements generate all subgroups of D_n
    for (const a of this.elements) {
      const H1 = this.close([a]);
      subs.set(this.sig(H1), H1);
      for (const b of this.elements) {
        const H2 = this.close([a, b]);
        subs.set(this.sig(H2), H2);
      }
    }
    return [...subs.values()].sort((a, b) => a.length - b.length);
  }

  classifySubgroups(subgroups) {
    const classes = [];
    const seen = new Set();
    for (const H of subgroups) {
      const s = this.sig(H);
      if (seen.has(s)) continue;
      const conjugates = new Map();
      for (const g of this.elements) {
        const c = this.conjugate(H, g);
        conjugates.set(this.sig(c), c);
      }
      for (const cs of conjugates.keys()) seen.add(cs);

      // Kernel (core): intersection of all conjugate subgroups
      const inAll = h => this.elements.every(g =>
        this.conjugate(H, g).some(x => this.key(x) === this.key(h))
      );
      const core = H.filter(inAll);
      
      const numColors = this.order / H.length;
      const isNormal = conjugates.size === 1;
      const colorGroupOrder = this.order / core.length;

      // Determine isomorphism structure
      const structName = this.identifyStructure(H);
      const colorGroupName = this.identifyQuotientStructure(core);
      const isCyclicColorGroup = this.checkIfCyclicQuotient(core);

      classes.push({
        H,
        sig: s,
        name: structName,
        conjugates: [...conjugates.values()],
        nconj: conjugates.size,
        core,
        colours: numColors,
        normal: isNormal,
        colourGroupOrder: colorGroupOrder,
        colourGroupName: colorGroupName,
        isCyclicColorGroup,
        generators: this.findMinimalGenerators(H)
      });
    }
    return classes.sort((a, b) => a.colours - b.colours || b.H.length - a.H.length);
  }

  findMinimalGenerators(H) {
    if (H.length === 1) return [this.identity];
    // Try 1 generator
    for (const g of H) {
      if (this.key(g) === this.key(this.identity)) continue;
      if (this.close([g]).length === H.length) return [g];
    }
    // Try 2 generators
    for (const a of H) {
      for (const b of H) {
        if (this.close([a, b]).length === H.length) return [a, b];
      }
    }
    return H;
  }

  identifyStructure(H) {
    const sz = H.length;
    if (sz === 1) return "1";
    if (sz === 2) return H.some(g => g[1] === 1) ? "C₂ (mirror)" : "C₂ (turn)";
    if (sz === this.order) return `D${this.n}`;
    const allRotations = H.every(g => g[1] === 0);
    if (allRotations) return `C${sz}`;
    if (sz % 2 === 0) {
      const half = sz / 2;
      return half === 2 ? "V₄" : `D${half}`;
    }
    return `Order ${sz}`;
  }

  identifyQuotientStructure(core) {
    const qOrder = this.order / core.length;
    if (qOrder === 1) return "1";
    if (qOrder === 2) return "C₂";
    if (qOrder === 3) return "C₃";
    if (qOrder === 4) {
      // Check if cyclic or V4
      return this.checkIfCyclicQuotient(core) ? "C₄" : "V₄ (C₂×C₂)";
    }
    if (qOrder === 6) {
      return this.checkIfCyclicQuotient(core) ? "C₆" : "S₃ (D₃)";
    }
    if (qOrder === 8) {
      return this.checkIfCyclicQuotient(core) ? "C₈" : "D₄";
    }
    if (qOrder === 12) {
      return this.checkIfCyclicQuotient(core) ? "C₁₂" : `D₆`;
    }
    if (qOrder === this.order) return `D${this.n}`;
    return `Order ${qOrder}`;
  }

  checkIfCyclicQuotient(core) {
    const qOrder = this.order / core.length;
    if (qOrder === 1 || qOrder === 2 || qOrder === 3) return true;
    const coreMap = new Map(core.map(g => [this.key(g), true]));
    // Check if there is an element whose powers generate all cosets
    for (const g of this.elements) {
      const visitedCosets = new Set();
      let curr = this.identity;
      for (let p = 0; p < qOrder; p++) {
        // Find canonical coset
        const cosetRep = this.canonicalCoset(curr, core);
        visitedCosets.add(cosetRep);
        curr = this.mul(curr, g);
      }
      if (visitedCosets.size === qOrder) return true;
    }
    return false;
  }

  canonicalCoset(g, H) {
    const coset = H.map(h => this.key(this.mul(g, h))).sort();
    return coset[0];
  }

  getLeftCosets(H) {
    const cosets = [];
    const cosetMap = new Map();
    for (const g of this.elements) {
      const cSig = H.map(h => this.key(this.mul(g, h))).sort().join("|");
      if (!cosetMap.has(cSig)) {
        cosetMap.set(cSig, cosets.length);
        cosets.push({
          index: cosets.length,
          sig: cSig,
          rep: g,
          elements: H.map(h => this.mul(g, h)).sort((a, b) => a[1] - b[1] || a[0] - b[0])
        });
      }
    }
    return { cosets, cosetMap };
  }

  getPermutationAction(H) {
    const { cosets, cosetMap } = this.getLeftCosets(H);
    const k = cosets.length;
    const perms = new Map();
    for (const g of this.elements) {
      const perm = [];
      for (let i = 0; i < k; i++) {
        const c = cosets[i];
        const nextG = this.mul(g, c.rep);
        const nextSig = H.map(h => this.key(this.mul(nextG, h))).sort().join("|");
        perm.push(cosetMap.get(nextSig));
      }
      perms.set(this.key(g), perm);
    }
    return { cosets, perms };
  }
}

// ------------------------------------------------------------- Renderers
export function drawDihedralStage(canvas, group, H, options = {}) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth || 360;
  const h = canvas.clientHeight || 360;
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  ctx.fillStyle = options.background || GROUND;
  ctx.fillRect(0, 0, w, h);

  const cx = w / 2;
  const cy = h / 2;
  const S = Math.min(w, h) * 0.44;
  const scr = p => [cx + S * p[0], cy - S * p[1]];

  const N = group.n;

  // 1. Draw polygon boundary
  ctx.beginPath();
  for (let i = 0; i <= N; i++) {
    const a = (i * 2 * Math.PI) / N;
    const q = scr([Math.cos(a), Math.sin(a)]);
    if (i === 0) ctx.moveTo(q[0], q[1]);
    else ctx.lineTo(q[0], q[1]);
  }
  ctx.closePath();
  ctx.strokeStyle = RULE;
  ctx.lineWidth = 1.4;
  ctx.stroke();

  // 2. Draw fundamental domain slivers
  ctx.beginPath();
  for (let i = 0; i < 2 * N; i++) {
    const a = (i * Math.PI) / N;
    const rad = i % 2 === 0 ? 1 : Math.cos(Math.PI / N);
    const q = scr([rad * Math.cos(a), rad * Math.sin(a)]);
    ctx.moveTo(cx, cy);
    ctx.lineTo(q[0], q[1]);
  }
  ctx.strokeStyle = RULE_FAINT;
  ctx.lineWidth = 0.8;
  ctx.stroke();

  // 3. Highlight reflection lines if active
  if (options.highlightReflections) {
    ctx.beginPath();
    for (let i = 0; i < N; i++) {
      const a = (i * Math.PI) / N;
      const p1 = scr([Math.cos(a), Math.sin(a)]);
      const p2 = scr([-Math.cos(a), -Math.sin(a)]);
      ctx.moveTo(p1[0], p1[1]);
      ctx.lineTo(p2[0], p2[1]);
    }
    ctx.strokeStyle = "rgba(180, 83, 9, 0.45)";
    ctx.setLineDash([4, 4]);
    ctx.lineWidth = 1.2;
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // 4. Paint motifs according to cosets
  const { cosets, cosetMap } = group.getLeftCosets(H);
  const palette = options.palette || OKABE_PALETTE;
  const motifStyle = options.motifStyle || "comma";
  const activeOp = options.activeTransform || [0, 0];
  const phase = options.phase || 0;

  // Base point in fundamental domain (between angle 0 and angle PI/N)
  const baseAngle = Math.PI / (2 * N);
  const baseRadius = 0.62;
  const BASE_POINT = [baseRadius * Math.cos(baseAngle), baseRadius * Math.sin(baseAngle)];

  const motifR = S * (0.24 / Math.sqrt(N / 4));

  for (const g of group.elements) {
    // If active operator x is applied, position is x * g
    const displayG = group.mul(activeOp, g);
    const cSig = H.map(h => group.key(group.mul(displayG, h))).sort().join("|");
    const colorIndex = cosetMap.get(cSig) % palette.length;

    const M = group.matrix(displayG);
    const pOrig = [
      M[0][0] * BASE_POINT[0] + M[0][1] * BASE_POINT[1],
      M[1][0] * BASE_POINT[0] + M[1][1] * BASE_POINT[1]
    ];
    const p = scr(pOrig);

    ctx.save();
    ctx.translate(p[0], p[1]);
    ctx.transform(M[0][0], -M[1][0], -M[0][1], M[1][1], 0, 0);

    // Optional dynamic phase swelling
    let scaleFactor = 1.0;
    if (options.animatePhase) {
      const elemPhase = (displayG[0] / N + (displayG[1] ? 0.5 : 0) + phase) % 1.0;
      const swell = elemPhase < 0.5 ? elemPhase * 2 : 2 - elemPhase * 2;
      scaleFactor = 0.75 + 0.25 * swell;
    }

    drawMotifPath(ctx, motifR * scaleFactor, motifStyle);

    // Highlight hovered element
    const isHovered = options.hoveredElement && group.key(options.hoveredElement) === group.key(g);
    const isCosetHighlighted = options.highlightedCoset !== undefined && options.highlightedCoset === colorIndex;

    ctx.fillStyle = palette[colorIndex];
    ctx.fill("evenodd");

    ctx.lineWidth = isHovered || isCosetHighlighted ? Math.max(2.2, motifR * 0.12) : Math.max(0.8, motifR * 0.05);
    ctx.strokeStyle = isHovered ? "#d97706" : (isCosetHighlighted ? "#000000" : EDGE);
    ctx.stroke();

    ctx.restore();

    // Element label overlay if requested
    if (options.showLabels) {
      ctx.save();
      ctx.font = `600 ${Math.max(10, Math.round(S * 0.05))}px var(--font-mono)`;
      ctx.fillStyle = "#1e293b";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const lblPos = scr([pOrig[0] * 1.25, pOrig[1] * 1.25]);
      ctx.fillText(group.name(g), lblPos[0], lblPos[1]);
      ctx.restore();
    }
  }

  // Draw center rotation marker
  ctx.beginPath();
  ctx.arc(cx, cy, 3.5, 0, 2 * Math.PI);
  ctx.fillStyle = varColor("--accent", "#006f63");
  ctx.fill();

  return { cosets, numColors: cosets.length };
}

function varColor(name, fallback) {
  if (typeof window !== "undefined" && window.getComputedStyle) {
    const v = window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    if (v) return v;
  }
  return fallback;
}

// ------------------------------------------------------------- Interactive UI App
export class DihedralApp {
  constructor(rootEl) {
    this.root = rootEl;
    this.n = 6;
    this.group = new DihedralGroup(this.n);
    this.selectedSubgroupIndex = 0;
    this.activeTransform = [0, 0];
    this.hoveredElement = null;
    this.highlightedCoset = null;
    this.motifStyle = "comma";
    this.showLabels = true;
    this.showReflections = true;
    this.isPlaying = false;
    this.phase = 0;
    this.lastTime = 0;

    this.initDOM();
    this.attachEvents();
    this.updateGroup();
    this.startLoop();
  }

  initDOM() {
    this.stageCanvas = this.root.querySelector("#main-stage-canvas");
    this.keypadContainer = this.root.querySelector("#action-keypad");
    this.subgroupsGrid = this.root.querySelector("#subgroups-grid");
    this.subgroupDetailsEl = this.root.querySelector("#subgroup-details-card");
    this.cayleyContainer = this.root.querySelector("#cayley-table-wrap");
    this.filterCountEl = this.root.querySelector("#filter-count");
    this.playToggleBtn = this.root.querySelector("#play-toggle-btn");
    this.phaseSlider = this.root.querySelector("#phase-slider");
    this.phaseCounter = this.root.querySelector("#phase-counter");
  }

  attachEvents() {
    // Dihedral N selector buttons
    this.root.querySelectorAll("[data-n]").forEach(btn => {
      btn.addEventListener("click", () => {
        const n = parseInt(btn.dataset.n, 10);
        if (n !== this.n) {
          this.root.querySelectorAll("[data-n]").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          this.n = n;
          this.activeTransform = [0, 0];
          this.updateGroup();
        }
      });
    });

    // Motif Style selector
    const motifSelect = this.root.querySelector("#motif-style-select");
    if (motifSelect) {
      motifSelect.addEventListener("change", e => {
        this.motifStyle = e.target.value;
        this.renderAll();
      });
    }

    // Toggle Labels
    const labelCheck = this.root.querySelector("#toggle-labels-check");
    if (labelCheck) {
      labelCheck.addEventListener("change", e => {
        this.showLabels = e.target.checked;
        this.renderAll();
      });
    }

    // Playback scrubber
    if (this.phaseSlider) {
      this.phaseSlider.addEventListener("input", e => {
        this.phase = parseFloat(e.target.value);
        if (this.phaseCounter) this.phaseCounter.textContent = `${Math.round(this.phase * 360)}°`;
        this.renderMainStage();
      });
    }

    // Play/Pause toggle
    if (this.playToggleBtn) {
      this.playToggleBtn.addEventListener("click", () => {
        this.isPlaying = !this.isPlaying;
        this.playToggleBtn.innerHTML = this.isPlaying ? "❚❚" : "▶";
        this.playToggleBtn.setAttribute("aria-label", this.isPlaying ? "Pause" : "Play");
      });
    }

    // View Tabs
    this.root.querySelectorAll(".view-tab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        this.root.querySelectorAll(".view-tab-btn").forEach(b => b.classList.remove("active"));
        this.root.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
        btn.classList.add("active");
        const panelId = btn.dataset.tab;
        const targetPanel = this.root.querySelector(`#${panelId}`);
        if (targetPanel) targetPanel.classList.add("active");
        this.renderAll();
      });
    });

    // Subgroup filters
    const filterSelect = this.root.querySelector("#subgroup-filter-select");
    if (filterSelect) {
      filterSelect.addEventListener("change", () => {
        this.renderSubgroupsGrid();
      });
    }

    // Window resize
    window.addEventListener("resize", () => this.renderAll());
  }

  updateGroup() {
    this.group = new DihedralGroup(this.n);
    this.selectedSubgroupIndex = 0;
    this.renderKeypad();
    this.renderSubgroupsGrid();
    this.renderSubgroupDetails();
    this.renderCayleyTable();
    this.renderAll();
  }

  getSelectedClass() {
    return this.group.conjugacyClasses[this.selectedSubgroupIndex] || this.group.conjugacyClasses[0];
  }

  renderKeypad() {
    if (!this.keypadContainer) return;
    this.keypadContainer.innerHTML = "";

    // Rotations row
    const rotTitle = document.createElement("div");
    rotTitle.className = "keypad-row-title";
    rotTitle.textContent = "Rotations (rᵏ)";
    this.keypadContainer.appendChild(rotTitle);

    const rotRow = document.createElement("div");
    rotRow.className = "keypad-row";
    for (let k = 0; k < this.n; k++) {
      const btn = document.createElement("button");
      btn.className = "keypad-btn";
      const g = [k, 0];
      btn.innerHTML = this.group.htmlName(g);
      if (this.group.key(g) === this.group.key(this.activeTransform)) btn.classList.add("active");
      btn.addEventListener("click", () => {
        this.activeTransform = g;
        this.renderKeypad();
        this.renderMainStage();
        this.updatePermutationReadout();
      });
      btn.addEventListener("mouseenter", () => {
        this.hoveredElement = g;
        this.renderMainStage();
      });
      btn.addEventListener("mouseleave", () => {
        this.hoveredElement = null;
        this.renderMainStage();
      });
      rotRow.appendChild(btn);
    }
    this.keypadContainer.appendChild(rotRow);

    // Reflections row
    const refTitle = document.createElement("div");
    refTitle.className = "keypad-row-title";
    refTitle.textContent = "Reflections (rᵏs)";
    this.keypadContainer.appendChild(refTitle);

    const refRow = document.createElement("div");
    refRow.className = "keypad-row";
    for (let k = 0; k < this.n; k++) {
      const btn = document.createElement("button");
      btn.className = "keypad-btn reflection";
      const g = [k, 1];
      btn.innerHTML = this.group.htmlName(g);
      if (this.group.key(g) === this.group.key(this.activeTransform)) btn.classList.add("active");
      btn.addEventListener("click", () => {
        this.activeTransform = g;
        this.renderKeypad();
        this.renderMainStage();
        this.updatePermutationReadout();
      });
      btn.addEventListener("mouseenter", () => {
        this.hoveredElement = g;
        this.renderMainStage();
      });
      btn.addEventListener("mouseleave", () => {
        this.hoveredElement = null;
        this.renderMainStage();
      });
      refRow.appendChild(btn);
    }
    this.keypadContainer.appendChild(refRow);
  }

  renderSubgroupsGrid() {
    if (!this.subgroupsGrid) return;
    this.subgroupsGrid.innerHTML = "";

    const filterVal = this.root.querySelector("#subgroup-filter-select")?.value || "all";
    const classes = this.group.conjugacyClasses.filter(c => {
      if (filterVal === "normal") return c.normal;
      if (filterVal === "non-normal") return !c.normal;
      if (filterVal === "cyclic") return c.isCyclicColorGroup;
      if (filterVal === "2color") return c.colours === 2;
      return true;
    });

    if (this.filterCountEl) {
      this.filterCountEl.textContent = `${classes.length} of ${this.group.conjugacyClasses.length} classes`;
    }

    classes.forEach((c, idx) => {
      const actualIndex = this.group.conjugacyClasses.indexOf(c);
      const card = document.createElement("div");
      card.className = `subgroup-card ${actualIndex === this.selectedSubgroupIndex ? "selected" : ""}`;
      
      const header = document.createElement("div");
      header.className = "subgroup-card-header";
      header.innerHTML = `
        <h4 class="subgroup-title">
          <span>H ≅ ${c.name}</span>
          <span style="font-size:0.8rem;color:var(--muted);font-weight:normal;">|H| = ${c.H.length}</span>
        </h4>
        <div class="subgroup-badges">
          <span class="badge colours">${c.colours} colour${c.colours > 1 ? "s" : ""}</span>
          <span class="badge ${c.normal ? "normal" : "non-normal"}">${c.normal ? "Normal" : "Non-normal"}</span>
          <span class="badge ${c.isCyclicColorGroup ? "cyclic" : "non-cyclic"}">${c.isCyclicColorGroup ? "Clockwork" : "Non-cyclic"}</span>
        </div>
      `;
      card.appendChild(header);

      const previewDiv = document.createElement("div");
      previewDiv.className = "subgroup-preview";
      const previewCanvas = document.createElement("canvas");
      previewDiv.appendChild(previewCanvas);
      card.appendChild(previewDiv);

      const details = document.createElement("div");
      details.className = "subgroup-details";
      const genStr = c.generators.map(g => this.group.name(g)).join(", ");
      details.innerHTML = `
        <div class="detail-row"><span class="detail-label">Generators</span><span class="detail-value">⟨${genStr}⟩</span></div>
        <div class="detail-row"><span class="detail-label">Conjugates</span><span class="detail-value">${c.nconj} in class</span></div>
        <div class="detail-row"><span class="detail-label">Colour Group</span><span class="detail-value">${c.colourGroupName}</span></div>
      `;
      card.appendChild(details);

      card.addEventListener("click", () => {
        this.selectedSubgroupIndex = actualIndex;
        this.root.querySelectorAll(".subgroup-card").forEach(sc => sc.classList.remove("selected"));
        card.classList.add("selected");
        this.renderSubgroupDetails();
        this.renderMainStage();
        this.updatePermutationReadout();
      });

      this.subgroupsGrid.appendChild(card);

      // Render miniature canvas
      requestAnimationFrame(() => {
        drawDihedralStage(previewCanvas, this.group, c.H, {
          motifStyle: this.motifStyle,
          showLabels: false
        });
      });
    });
  }

  renderSubgroupDetails() {
    if (!this.subgroupDetailsEl) return;
    const c = this.getSelectedClass();
    const H = c.H;
    const { cosets } = this.group.getLeftCosets(H);

    const swatchesHtml = cosets.map((coset, i) => {
      const color = OKABE_PALETTE[i % OKABE_PALETTE.length];
      const elemsStr = coset.elements.map(g => this.group.name(g)).join(", ");
      return `
        <div class="swatch-chip" data-coset="${i}">
          <span class="swatch-dot" style="background:${color};"></span>
          <span>Coset ${i + 1}: {${elemsStr}}</span>
        </div>
      `;
    }).join("");

    const coreStr = c.core.map(g => this.group.name(g)).join(", ");
    const hStr = H.map(g => this.group.name(g)).join(", ");

    this.root.querySelector("#detail-subgroup-name").textContent = `H ≅ ${c.name} (${H.length} elements)`;
    this.root.querySelector("#detail-subgroup-elements").textContent = `{ ${hStr} }`;
    this.root.querySelector("#detail-kernel-elements").textContent = `{ ${coreStr} }`;
    this.root.querySelector("#detail-index").textContent = `${c.colours} (Index [D${this.n} : H])`;
    this.root.querySelector("#detail-normality").textContent = c.normal 
      ? "Normal (H ⊲ G, action is regular)" 
      : `Non-normal (${c.nconj} conjugate subgroups in class)`;
    this.root.querySelector("#detail-color-group").textContent = `${c.colourGroupName} (Order ${c.colourGroupOrder})`;
    this.root.querySelector("#detail-clockwork").textContent = c.isCyclicColorGroup
      ? "Yes · Cyclic colour group (lifts to spacetime clock)"
      : "No · Non-cyclic permutation structure";

    const swatchesContainer = this.root.querySelector("#detail-palette-swatches");
    if (swatchesContainer) {
      swatchesContainer.innerHTML = swatchesHtml;
      swatchesContainer.querySelectorAll(".swatch-chip").forEach(chip => {
        chip.addEventListener("mouseenter", () => {
          this.highlightedCoset = parseInt(chip.dataset.coset, 10);
          this.renderMainStage();
        });
        chip.addEventListener("mouseleave", () => {
          this.highlightedCoset = null;
          this.renderMainStage();
        });
      });
    }

    this.updatePermutationReadout();
  }

  updatePermutationReadout() {
    const permBox = this.root.querySelector("#active-permutation-box");
    if (!permBox) return;
    const c = this.getSelectedClass();
    const { perms } = this.group.getPermutationAction(c.H);
    const currentPerm = perms.get(this.group.key(this.activeTransform));
    if (currentPerm) {
      const cycles = this.toCycleNotation(currentPerm);
      permBox.innerHTML = `
        <div><strong>Active Operator:</strong> <span class="mono">${this.group.name(this.activeTransform)}</span></div>
        <div><strong>Palette Permutation:</strong> <span class="mono">${cycles || "(identity)"}</span></div>
      `;
    }
  }

  toCycleNotation(perm) {
    const visited = new Set();
    const cycles = [];
    for (let i = 0; i < perm.length; i++) {
      if (visited.has(i)) continue;
      const cycle = [];
      let curr = i;
      while (!visited.has(curr)) {
        visited.add(curr);
        cycle.push(curr + 1);
        curr = perm[curr];
      }
      if (cycle.length > 1) {
        cycles.push(`(${cycle.join(" ")})`);
      }
    }
    return cycles.join("");
  }

  renderCayleyTable() {
    if (!this.cayleyContainer) return;
    const els = this.group.elements;
    let html = `<table class="cayley-table"><thead><tr><th>·</th>`;
    for (const g of els) {
      html += `<th>${this.group.name(g)}</th>`;
    }
    html += `</tr></thead><tbody>`;

    for (const a of els) {
      html += `<tr><th>${this.group.name(a)}</th>`;
      for (const b of els) {
        const prod = this.group.mul(a, b);
        html += `<td data-a="${this.group.key(a)}" data-b="${this.group.key(b)}">${this.group.name(prod)}</td>`;
      }
      html += `</tr>`;
    }
    html += `</tbody></table>`;
    this.cayleyContainer.innerHTML = html;
  }

  renderMainStage() {
    if (!this.stageCanvas) return;
    const c = this.getSelectedClass();
    drawDihedralStage(this.stageCanvas, this.group, c.H, {
      motifStyle: this.motifStyle,
      showLabels: this.showLabels,
      highlightReflections: this.showReflections,
      activeTransform: this.activeTransform,
      hoveredElement: this.hoveredElement,
      highlightedCoset: this.highlightedCoset,
      animatePhase: this.isPlaying,
      phase: this.phase
    });
  }

  renderAll() {
    this.renderMainStage();
  }

  startLoop() {
    const step = timestamp => {
      if (this.isPlaying) {
        if (!this.lastTime) this.lastTime = timestamp;
        const dt = (timestamp - this.lastTime) / 1000;
        this.phase = (this.phase + dt * 0.25) % 1.0;
        if (this.phaseSlider) this.phaseSlider.value = this.phase;
        if (this.phaseCounter) this.phaseCounter.textContent = `${Math.round(this.phase * 360)}°`;
        this.renderMainStage();
      }
      this.lastTime = timestamp;
      requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
}

// Auto-initialize when DOM is ready
if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    const root = document.getElementById("dihedral-app");
    if (root) new DihedralApp(root);
  });
}

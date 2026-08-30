/* Paused, local film renderer for all 68 forward clockwork rows.
 *
 * Every canvas is driven by the checked-in correspondence JSON.  No code or
 * data is loaded from animated-groups-fable.  A film is the orbit of one
 * asymmetric animated motif: an operation (M,v,1,tau) places it at
 * M*base+v+lattice and shows its internal time t-tau.  Canvases are lazy,
 * start at a 1x1 backing store, and never request an animation frame until a
 * viewer explicitly presses Play.
 */

import {
  RING_MID,
  RING_W,
  buildClockworkGeometry,
  frac,
} from "./clockwork-coloring-geometry.js";

"use strict";

const DATA_URL = new URL("data/clockwork-coloring-correspondence.json", import.meta.url);
const BOOK_EXCERPT_TARGET = "clockwork-book-excerpt";
const PERIOD_MS = 4000;
const DPR_LIMIT = 1.5;
const TWO_PI = Math.PI * 2;
const STEP = 1 / 24;
const FINE_STEP = 1 / 240;

const COLORS = {
  background: "#faf8f1",
  body: "#dbe6f2",
  outline: "#657f99",
  fill: "#28709e",
  beatOn: "#b23a2c",
  beatOff: "#b8ad97",
};

const RAW_COMMA = [
  [[0.40, -0.30], [0.52, 0.18], [0.32, 0.56], [-0.52, 0.74]],
  [[-0.52, 0.74], [-0.10, 0.52], [0.18, 0.26], [0.06, 0.02]],
  [[0.06, 0.02], [-0.14, 0.02], [-0.40, -0.10], [-0.40, -0.30]],
  [[-0.40, -0.30], [-0.40, -0.54], [-0.22, -0.68], [0.00, -0.68]],
  [[0.00, -0.68], [0.24, -0.68], [0.40, -0.54], [0.40, -0.30]],
];

const COMMA = (() => {
  const samples = [];
  for (const [p0, p1, p2, p3] of RAW_COMMA) {
    for (let index = 0; index <= 24; index += 1) {
      const t = index / 24;
      const m = 1 - t;
      samples.push([
        m ** 3 * p0[0] + 3 * m * m * t * p1[0] + 3 * m * t * t * p2[0] + t ** 3 * p3[0],
        m ** 3 * p0[1] + 3 * m * m * t * p1[1] + 3 * m * t * t * p2[1] + t ** 3 * p3[1],
      ]);
    }
  }
  const xs = samples.map((point) => point[0]);
  const ys = samples.map((point) => point[1]);
  const centerX = (Math.min(...xs) + Math.max(...xs)) / 2;
  const centerY = (Math.min(...ys) + Math.max(...ys)) / 2;
  const scale = 0.64 / Math.max(
    ...samples.map((point) => Math.hypot(point[0] - centerX, point[1] - centerY)),
  );
  const segments = RAW_COMMA.map((segment) => segment.map((point) => [
    (point[0] - centerX) * scale,
    (point[1] - centerY) * scale,
  ]));
  const normalizedY = samples.map((point) => (point[1] - centerY) * scale);
  return {
    segments,
    top: Math.min(...normalizedY),
    bottom: Math.max(...normalizedY),
  };
})();

// Screen-space phase ruler, ported from animated-groups-fable 950b021.
// The ruler stays fixed while a short hand sweeps one turn per film period.
const RING_MIN_PX = 6.5;
const ARROW_MIN_PX = 9;
const HEAD_LEN = 1.7;
const HEAD_HALF = 1.15;
const HAND_TAIL = 1.4;

function bodyPath(context, radius) {
  const segments = COMMA.segments;
  context.beginPath();
  context.moveTo(segments[0][0][0] * radius, segments[0][0][1] * radius);
  for (const [, point1, point2, point3] of segments) {
    context.bezierCurveTo(
      point1[0] * radius,
      point1[1] * radius,
      point2[0] * radius,
      point2[1] * radius,
      point3[0] * radius,
      point3[1] * radius,
    );
  }
  context.closePath();
}

function drawMotif(context, theta, radius, layer) {
  const phase = frac(theta);
  const rising = phase < 0.5;
  const sweep = (phase * 2) % 1;
  const lineY = (COMMA.bottom - sweep * (COMMA.bottom - COMMA.top)) * radius;
  const top = (COMMA.top - 0.2) * radius;
  const bottom = (COMMA.bottom + 0.2) * radius;

  if (layer === "body") {
    bodyPath(context, radius);
    context.fillStyle = COLORS.body;
    context.fill();
    context.lineWidth = Math.max(0.7, 0.045 * radius);
    context.strokeStyle = COLORS.outline;
    context.stroke();
    return;
  }

  context.save();
  bodyPath(context, radius);
  context.clip();
  context.fillStyle = COLORS.fill;
  if (rising) {
    context.fillRect(-1.2 * radius, lineY, 2.4 * radius, bottom - lineY);
  } else {
    context.fillRect(-1.2 * radius, top, 2.4 * radius, lineY - top);
  }
  context.restore();
}

function drawPhaseRing(context, theta, radius, order, direction = 1) {
  if (radius < RING_MIN_PX) return;
  const ringRadius = RING_MID * radius;
  const lineWidth = Math.max(1.1, RING_W * radius);
  const gap = Math.min(0.125 / order, 0.022) * TWO_PI;
  const sweepDirection = direction < 0 ? -1 : 1;
  const pointAt = (angle, distance) => [
    distance * Math.cos(angle),
    distance * Math.sin(angle),
  ];

  context.save();
  context.lineWidth = lineWidth;
  context.lineCap = "butt";

  // The fixed N-interval ruler. No sector flashes when a boundary is crossed;
  // the continuously moving hand below carries both phase and direction.
  context.globalAlpha = 0.4;
  context.strokeStyle = COLORS.beatOff;
  for (let index = 0; index < order; index += 1) {
    const start = -Math.PI / 2 + (index / order) * TWO_PI + gap;
    const end = -Math.PI / 2 + ((index + 1) / order) * TWO_PI - gap;
    context.beginPath();
    context.arc(0, 0, ringRadius, start, end);
    context.stroke();
  }

  if (radius >= ARROW_MIN_PX) {
    context.globalAlpha = 1;
    const tip = -Math.PI / 2 + frac(theta) * TWO_PI;
    const headLength = (HEAD_LEN * lineWidth) / ringRadius;
    const base = tip - sweepDirection * headLength;
    const tail = base - sweepDirection * headLength * HAND_TAIL;

    context.strokeStyle = COLORS.beatOn;
    context.beginPath();
    context.arc(0, 0, ringRadius, Math.min(base, tail), Math.max(base, tail));
    context.stroke();

    const [baseX1, baseY1] = pointAt(base, ringRadius - HEAD_HALF * lineWidth);
    const [baseX2, baseY2] = pointAt(base, ringRadius + HEAD_HALF * lineWidth);
    const [tipX, tipY] = pointAt(tip, ringRadius);
    context.beginPath();
    context.moveTo(baseX1, baseY1);
    context.lineTo(baseX2, baseY2);
    context.lineTo(tipX, tipY);
    context.closePath();
    context.fillStyle = COLORS.beatOn;
    context.fill();
  }
  context.restore();
}

function validateRecord(record) {
  if (!record || !record.render || !Array.isArray(record.render.ops)) {
    throw new Error("missing render specification");
  }
  if (!Array.isArray(record.render.basis) || record.render.basis.length !== 2) {
    throw new Error("invalid wallpaper basis");
  }
  if (record.render.ops.length === 0 || record.render.ops.some((operation) => operation.s !== 1)) {
    throw new Error("the correspondence renderer accepts forward operations only");
  }
  const phases = new Set(record.render.ops.map((operation) => (
    Math.round(frac(operation.tau) * record.clock_order) % record.clock_order
  )));
  if (phases.size !== record.clock_order) {
    throw new Error("phase image is not the declared cyclic group");
  }
}

class ClockworkPlayer {
  constructor(root, record) {
    validateRecord(record);
    this.root = root;
    this.record = record;
    this.stage = root.querySelector("[data-film-stage]");
    this.canvas = root.querySelector("canvas");
    this.status = root.querySelector("[data-film-status]");
    this.controls = root.querySelector("[data-film-controls]");
    this.toggle = root.querySelector("[data-film-toggle]");
    this.toggleLabel = root.querySelector("[data-film-toggle-label]");
    this.slider = root.querySelector("[data-film-slider]");
    this.output = root.querySelector("[data-film-output]");
    this.phase = 0;
    this.playingIntent = false;
    this.nearViewport = false;
    this.active = false;
    this.frameRequest = 0;
    this.startedAt = 0;
    this.geometry = null;

    this.canvas.setAttribute(
      "aria-label",
      `Paused clockwork film for colour action ${record.id}, with ${record.clock_order} phase interval${record.clock_order === 1 ? "" : "s"}.`,
    );
    this.toggle.addEventListener("click", () => this.togglePlayback());
    this.slider.addEventListener("input", () => this.scrub(Number(this.slider.value)));
    this.controls.addEventListener("keydown", (event) => this.controlKeyDown(event));
    this.slider.title = "Scrub phase · arrow keys jump between clock marks · Shift+arrow steps finely";
    this.resizeObserver = new ResizeObserver(() => {
      if (this.active) this.resizeAndDraw();
    });
    this.resizeObserver.observe(this.stage);
  }

  activate() {
    this.nearViewport = true;
    if (!this.active) {
      this.active = true;
      this.resizeAndDraw();
      this.status.hidden = true;
      this.stage.dataset.state = "ready";
      this.controls.dataset.state = "ready";
      this.toggle.disabled = false;
      this.slider.disabled = false;
    }
    if (this.playingIntent && !document.hidden) this.startFrames();
  }

  deactivate() {
    this.nearViewport = false;
    this.suspendFrames();
    if (!this.active) return;
    this.active = false;
    this.geometry = null;
    this.canvas.width = 1;
    this.canvas.height = 1;
  }

  resizeAndDraw() {
    if (!this.active) return;
    const bounds = this.stage.getBoundingClientRect();
    const width = Math.max(1, Math.round(bounds.width));
    const height = Math.max(1, Math.round(bounds.height));
    const dpr = Math.min(window.devicePixelRatio || 1, DPR_LIMIT);
    const targetWidth = Math.max(1, Math.round(width * dpr));
    const targetHeight = Math.max(1, Math.round(height * dpr));
    if (this.canvas.width !== targetWidth || this.canvas.height !== targetHeight) {
      this.canvas.width = targetWidth;
      this.canvas.height = targetHeight;
    }
    this.geometry = buildClockworkGeometry(this.record.render, width, height, dpr);
    this.stage.dataset.motifCircleDiameter = this.geometry.circleDiameter.toFixed(2);
    this.draw(this.phase);
  }

  draw(phase) {
    if (!this.active || !this.geometry) return;
    const context = this.canvas.getContext("2d");
    if (!context) throw new Error("2D canvas is unavailable");
    const { width, height, dpr, motifRadius, placements } = this.geometry;
    context.save();
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    context.clearRect(0, 0, width, height);
    context.fillStyle = COLORS.background;
    context.fillRect(0, 0, width, height);
    context.translate(width / 2, height / 2);
    for (const layer of ["body", "fill"]) {
      for (const placement of placements) {
        context.save();
        context.translate(placement.pixelX, placement.pixelY);
        const matrix = placement.transform;
        context.transform(matrix[0][0], matrix[1][0], matrix[0][1], matrix[1][1], 0, 0);
        drawMotif(context, phase - placement.tau, motifRadius, layer);
        context.restore();
      }
    }
    for (const placement of placements) {
      context.save();
      context.translate(placement.pixelX, placement.pixelY);
      drawPhaseRing(context, phase - placement.tau, motifRadius, this.record.clock_order, 1);
      context.restore();
    }
    context.restore();
  }

  updateReadout() {
    const text = this.phase.toFixed(3);
    this.slider.value = text;
    this.slider.setAttribute("aria-valuetext", `phase ${text} of one period`);
    this.output.value = text;
    this.output.textContent = text;
  }

  setPhase(value) {
    this.phase = frac(Number.isFinite(value) ? value : 0);
    if (this.playingIntent) this.startedAt = performance.now() - this.phase * PERIOD_MS;
    this.updateReadout();
    this.draw(this.phase);
  }

  scrub(value) {
    this.pause();
    this.setPhase(value);
  }

  seek(value) {
    this.setPhase(value);
  }

  step(delta) {
    this.scrub(this.phase + delta);
  }

  stepMark(direction) {
    if (this.record.clock_order < 2) {
      this.step(direction * STEP);
      return;
    }
    const marks = Array.from(
      { length: this.record.clock_order },
      (_unused, index) => index / this.record.clock_order,
    );
    const epsilon = 1e-4;
    const next = direction > 0
      ? marks.find((mark) => mark > this.phase + epsilon)
      : [...marks].reverse().find((mark) => mark < this.phase - epsilon);
    this.scrub(next === undefined
      ? (direction > 0 ? marks[0] : marks[marks.length - 1])
      : next);
  }

  // Adapted from animated-groups-fable 94c55bc: the whole control bar owns
  // arrow/Home/End scrubbing, so the keys still work after clicking Play.
  controlKeyDown(event) {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    const step = (direction) => (
      event.shiftKey ? this.step(direction * FINE_STEP) : this.stepMark(direction)
    );
    if (event.key === "ArrowRight" || event.key === "ArrowUp") step(1);
    else if (event.key === "ArrowLeft" || event.key === "ArrowDown") step(-1);
    else if (event.key === "Home") this.seek(0);
    else if (event.key === "End") this.seek(1 - STEP);
    else return;
    event.preventDefault();
  }

  togglePlayback() {
    if (this.playingIntent) this.pause();
    else this.play();
  }

  play() {
    this.playingIntent = true;
    this.toggle.setAttribute("aria-pressed", "true");
    this.toggleLabel.textContent = "Pause";
    this.toggle.querySelector(".animation-icon").textContent = "❚❚";
    // An IntersectionObserver exit clears the backing store but deliberately
    // leaves the controls usable. A viewer's explicit Play request must win
    // over that lazy-rendering state: rebuild the selected film before its
    // first animation frame instead of advancing an invisible canvas.
    if (!this.active) this.activate();
    else this.resizeAndDraw();
    if (!document.hidden) this.startFrames();
  }

  pause() {
    this.playingIntent = false;
    this.suspendFrames();
    this.toggle.setAttribute("aria-pressed", "false");
    this.toggleLabel.textContent = "Play";
    this.toggle.querySelector(".animation-icon").textContent = "▶";
  }

  startFrames() {
    if (this.frameRequest || !this.active || !this.playingIntent) return;
    this.startedAt = performance.now() - this.phase * PERIOD_MS;
    const tick = (timestamp) => {
      this.frameRequest = 0;
      if (!this.playingIntent || !this.nearViewport || document.hidden || !this.active) return;
      this.phase = frac((timestamp - this.startedAt) / PERIOD_MS);
      this.updateReadout();
      this.draw(this.phase);
      this.frameRequest = requestAnimationFrame(tick);
    };
    this.frameRequest = requestAnimationFrame(tick);
  }

  suspendFrames() {
    if (this.frameRequest) cancelAnimationFrame(this.frameRequest);
    this.frameRequest = 0;
  }

  visibilityChanged() {
    if (document.hidden) this.suspendFrames();
    else if (this.playingIntent && this.nearViewport) this.startFrames();
  }

  fail(message) {
    this.pause();
    this.status.hidden = false;
    this.status.textContent = message;
    this.stage.dataset.state = "error";
    this.controls.dataset.state = "error";
    this.toggle.disabled = true;
    this.slider.disabled = true;
  }
}

function initializeClockworkTabs() {
  // Suppress the browser's pre-enhancement anchor jump: before inactive
  // panels collapse, every later wallpaper section has the wrong offset.
  const initialHash = location.hash;
  if (initialHash) history.replaceState(null, "", `${location.pathname}${location.search}`);
  const controllersByGroup = new Map();

  for (const host of document.querySelectorAll("[data-clockwork-tabs]")) {
    const tablist = host.querySelector("[data-clockwork-tablist]");
    const tabs = [...host.querySelectorAll("[data-clockwork-tab]")];
    if (!tablist || tabs.length === 0) continue;

    const items = tabs.map((tab) => {
      const panel = document.getElementById(tab.dataset.panelId || "");
      return panel ? { tab, panel } : null;
    }).filter(Boolean);
    if (items.length !== tabs.length) continue;

    tablist.setAttribute("role", "tablist");
    for (const { tab, panel } of items) {
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-controls", panel.id);
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", tab.id);
    }

    let activeId = "";
    const activate = (groupId, options = {}) => {
      const selected = items.find(({ panel }) => panel.id === groupId);
      if (!selected) return false;
      const previousId = activeId;
      activeId = groupId;

      for (const { tab, panel } of items) {
        const isActive = panel.id === groupId;
        tab.setAttribute("aria-selected", String(isActive));
        tab.tabIndex = isActive ? 0 : -1;
        panel.hidden = !isActive;
        if (panel.parentElement?.matches("li")) panel.parentElement.hidden = !isActive;
      }

      if (options.focus) selected.tab.focus();
      if (options.history === "push" || options.history === "replace") {
        const method = options.history === "push" ? "pushState" : "replaceState";
        history[method](null, "", `#${groupId}`);
      }
      if (options.scroll) {
        requestAnimationFrame(() => selected.panel.scrollIntoView({ block: "start" }));
      }
      // The initial deep link is reopened on `load` so its final scroll
      // position uses fully laid-out content.  That is a re-scroll, not a tab
      // transition: emitting a self-transition would make the player clear
      // its own canvas as both the inactive and active film.
      if (previousId !== groupId) {
        document.dispatchEvent(new CustomEvent("clockwork:tab-change", {
          detail: { activeId: groupId, inactiveId: previousId || null },
        }));
      }
      return true;
    };

    items.forEach(({ tab, panel }, index) => {
      tab.addEventListener("click", (event) => {
        if (
          event.button !== 0
          || event.metaKey
          || event.ctrlKey
          || event.shiftKey
          || event.altKey
        ) return;
        event.preventDefault();
        activate(panel.id, {
          history: location.hash === `#${panel.id}` ? null : "push",
        });
      });

      tab.addEventListener("keydown", (event) => {
        let nextIndex = null;
        if (event.key === "ArrowRight" || event.key === "ArrowDown") {
          nextIndex = (index + 1) % items.length;
        } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
          nextIndex = (index - 1 + items.length) % items.length;
        } else if (event.key === "Home") {
          nextIndex = 0;
        } else if (event.key === "End") {
          nextIndex = items.length - 1;
        }
        if (nextIndex === null) return;
        event.preventDefault();
        activate(items[nextIndex].panel.id, { focus: true, history: "replace" });
      });

      controllersByGroup.set(panel.id, { activate, panel });
    });

    activate(items[0].panel.id);
  }

  const openFromHash = (scroll = true) => {
    const id = decodeURIComponent(location.hash.replace(/^#/, ""));
    if (!id) return;
    const controller = controllersByGroup.get(id);
    if (controller) {
      controller.activate(id, { scroll });
      return;
    }
    const target = document.getElementById(id);
    if (target && scroll) requestAnimationFrame(() => target.scrollIntoView({ block: "start" }));
  };

  if (initialHash) history.replaceState(null, "", initialHash);
  openFromHash(true);
  window.addEventListener("load", () => openFromHash(true), { once: true });
  window.addEventListener("hashchange", () => openFromHash(true));
  window.addEventListener("popstate", () => openFromHash(true));
}

function initializeBookExcerptDialog() {
  const dialog = document.querySelector("#book-excerpt-dialog");
  if (!dialog) return;

  const title = dialog.querySelector("#book-excerpt-title");
  const context = dialog.querySelector("#book-excerpt-context");
  const media = dialog.querySelector("[data-book-excerpt-media]");
  const image = dialog.querySelector("[data-book-excerpt-image]");
  const status = dialog.querySelector("[data-book-excerpt-status]");
  const source = dialog.querySelector("[data-book-excerpt-source]");
  const zoomButton = dialog.querySelector("[data-book-zoom-toggle]");
  const closeButton = dialog.querySelector("[data-book-dialog-close]");
  const supportsNativeDialog = typeof dialog.showModal === "function";
  let opener = null;

  dialog.dataset.enhanced = "true";
  dialog.dataset.mode = supportsNativeDialog ? "native" : "fallback";

  function setZoom(actualSize) {
    media.dataset.zoom = actualSize ? "actual" : "fit";
    zoomButton.setAttribute("aria-pressed", String(actualSize));
    zoomButton.textContent = actualSize ? "Fit excerpt" : "Actual size";
    media.scrollTop = 0;
    media.scrollLeft = 0;
  }

  function resetExcerpt() {
    image.removeAttribute("src");
    image.alt = "";
    media.dataset.state = "idle";
    setZoom(false);
    status.hidden = false;
    document.documentElement.classList.remove("book-dialog-open");
    if (opener && opener.isConnected) opener.focus();
    opener = null;
  }

  function closeExcerpt() {
    if (!dialog.hasAttribute("open")) return;
    if (supportsNativeDialog) {
      dialog.close();
      return;
    }
    dialog.removeAttribute("open");
    dialog.classList.remove("is-fallback-open");
    resetExcerpt();
  }

  function openExcerpt(link) {
    opener = link;
    title.textContent = link.dataset.bookTitle || "Annotated book excerpt";
    context.textContent = link.dataset.bookContext || "Highlighted evidence from the cited page.";
    source.href = link.href;
    image.alt = link.dataset.bookAlt || "Annotated excerpt from The Symmetries of Things.";
    image.removeAttribute("src");
    setZoom(false);
    media.dataset.state = "loading";
    status.hidden = false;
    status.textContent = "Loading annotated excerpt…";

    if (supportsNativeDialog) {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
      dialog.classList.add("is-fallback-open");
    }
    document.documentElement.classList.add("book-dialog-open");
    image.src = new URL(link.dataset.bookImage, document.baseURI).href;
    closeButton.focus();
  }

  for (const link of document.querySelectorAll("a[data-book-excerpt]")) {
    link.addEventListener("click", (event) => {
      if (
        event.defaultPrevented
        || event.button !== 0
        || event.metaKey
        || event.ctrlKey
        || event.shiftKey
        || event.altKey
      ) return;
      event.preventDefault();
      openExcerpt(event.currentTarget);
    });
  }

  document.addEventListener("click", (event) => {
    if (
      !supportsNativeDialog
      && dialog.hasAttribute("open")
      && !dialog.contains(event.target)
    ) {
      event.preventDefault();
      closeExcerpt();
    }
  }, true);

  document.addEventListener("keydown", (event) => {
    if (supportsNativeDialog || !dialog.hasAttribute("open")) return;
    if (event.key === "Escape") {
      event.preventDefault();
      closeExcerpt();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = [closeButton, zoomButton, source].filter((element) => !element.hidden);
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });

  image.addEventListener("load", () => {
    if (!image.getAttribute("src")) return;
    media.dataset.state = "ready";
    status.hidden = true;
  });

  image.addEventListener("error", () => {
    if (!image.getAttribute("src")) return;
    media.dataset.state = "error";
    status.hidden = false;
    status.textContent = "The local excerpt could not be loaded. Use the Google Books link below.";
  });

  closeButton.addEventListener("click", closeExcerpt);
  zoomButton.addEventListener("click", () => {
    setZoom(media.dataset.zoom !== "actual");
  });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) closeExcerpt();
  });
  dialog.addEventListener("close", resetExcerpt);
}

function initializeDiagramSymbolDialog() {
  const dialog = document.querySelector("#diagram-symbol-dialog");
  const openButton = document.querySelector("[data-diagram-symbol-open]");
  if (!dialog || !openButton) return;

  const closeButton = dialog.querySelector("[data-diagram-symbol-close]");
  const supportsNativeDialog = typeof dialog.showModal === "function";
  let opener = null;

  dialog.dataset.mode = supportsNativeDialog ? "native" : "fallback";

  function restorePage() {
    document.documentElement.classList.remove("diagram-symbol-dialog-open");
    if (opener && opener.isConnected) opener.focus();
    opener = null;
  }

  function closeIndex() {
    if (!dialog.hasAttribute("open")) return;
    if (supportsNativeDialog) {
      dialog.close();
      return;
    }
    dialog.removeAttribute("open");
    dialog.classList.remove("is-fallback-open");
    restorePage();
  }

  function openIndex() {
    if (dialog.hasAttribute("open")) return;
    opener = openButton;
    if (supportsNativeDialog) {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
      dialog.classList.add("is-fallback-open");
    }
    document.documentElement.classList.add("diagram-symbol-dialog-open");
    closeButton?.focus();
  }

  openButton.addEventListener("click", openIndex);
  closeButton?.addEventListener("click", closeIndex);
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) closeIndex();
  });
  dialog.addEventListener("close", restorePage);

  document.addEventListener("click", (event) => {
    if (
      !supportsNativeDialog
      && dialog.hasAttribute("open")
      && event.target !== openButton
      && !dialog.contains(event.target)
    ) {
      event.preventDefault();
      closeIndex();
    }
  }, true);

  document.addEventListener("keydown", (event) => {
    if (supportsNativeDialog || !dialog.hasAttribute("open")) return;
    if (event.key === "Escape") {
      event.preventDefault();
      closeIndex();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = [
      ...dialog.querySelectorAll('button, a[href]'),
    ].filter((element) => !element.hidden);
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
}

function initializeBookExcerptLinks() {
  let viewerWindow = null;
  window.addEventListener("message", (event) => {
    if (
      event.origin === window.location.origin
      && event.data?.type === "clockwork:book-excerpt-ready"
      && event.source
    ) viewerWindow = event.source;
  });

  for (const link of document.querySelectorAll("a[data-book-excerpt]")) {
    link.target = BOOK_EXCERPT_TARGET;
    link.addEventListener("click", (event) => {
      if (
        event.defaultPrevented
        || event.button !== 0
        || event.metaKey
        || event.ctrlKey
        || event.shiftKey
        || event.altKey
      ) return;

      if (viewerWindow && !viewerWindow.closed) {
        event.preventDefault();
        viewerWindow.location.href = link.href;
        viewerWindow.focus();
        return;
      }

      // Let the named-target anchor perform the first open natively. The
      // viewer posts its WindowProxy back as soon as it loads, avoiding popup
      // blockers while still giving later clicks an exact reusable window.
    });
  }
}

async function initialize() {
  const roots = [...document.querySelectorAll("[data-clockwork-player]")];
  if (roots.length === 0) return;
  let payload;
  try {
    const response = await fetch(DATA_URL, { credentials: "same-origin" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    payload = await response.json();
    if (!payload || !Array.isArray(payload.groups) || payload.groups.length !== 68) {
      throw new Error("expected 68 correspondence records");
    }
  } catch (error) {
    for (const root of roots) {
      root.querySelector("[data-film-status]").textContent = "Film unavailable; use the static plate.";
      root.querySelector("[data-film-stage]").dataset.state = "error";
      root.querySelector("[data-film-controls]").dataset.state = "error";
    }
    console.error("Clockwork correspondence data failed to load", error);
    return;
  }

  const records = new Map(payload.groups.map((record) => [record.id, record]));
  const players = [];
  const playersById = new Map();
  for (const root of roots) {
    const record = records.get(root.dataset.groupId);
    try {
      if (!record) throw new Error(`missing record ${root.dataset.groupId}`);
      const player = new ClockworkPlayer(root, record);
      players.push(player);
      playersById.set(record.id, player);
    } catch (error) {
      const status = root.querySelector("[data-film-status]");
      status.textContent = "Film data failed validation; use the static plate.";
      root.querySelector("[data-film-stage]").dataset.state = "error";
      root.querySelector("[data-film-controls]").dataset.state = "error";
      console.error("Clockwork player failed to initialize", root.dataset.groupId, error);
    }
  }

  document.addEventListener("clockwork:tab-change", (event) => {
    const inactive = playersById.get(event.detail?.inactiveId);
    const active = playersById.get(event.detail?.activeId);
    // A repeated hash activation must never deactivate the selected player.
    // The tab controller suppresses these events, but keep this guard at the
    // rendering boundary as protection against future callers.
    if (inactive && inactive !== active) inactive.deactivate();
    if (active) {
      active.pause();
      active.seek(0);
    }
  });

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        const player = players.find((candidate) => candidate.root === entry.target);
        if (!player) continue;
        if (entry.isIntersecting) player.activate();
        else player.deactivate();
      }
    }, { rootMargin: "600px 0px" });
    for (const player of players) observer.observe(player.root);
  } else {
    for (const player of players) player.activate();
  }

  document.addEventListener("visibilitychange", () => {
    for (const player of players) player.visibilityChanged();
  });
}

initializeClockworkTabs();
initializeDiagramSymbolDialog();
initializeBookExcerptLinks();
void initialize();

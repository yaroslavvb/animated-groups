/* Interactive lift viewer for the cyclic-colouring / polar-space-group atlas.
 *
 * The checked-in record already contains the two-dimensional affine orbit
 * (M, v, tau).  This viewer changes only its interpretation: tau becomes a
 * vertical coordinate and each operation lifts to
 *
 *   (x, y, z) -> (M(x, y) + v, z + tau).
 *
 * Static WebP views remain in the page as the no-JavaScript fallback.  A
 * canvas is activated lazily for the selected tab and rotates only after an
 * explicit button press.
 */

"use strict";

const DATA_URL = new URL("data/space-group-correspondence.json", import.meta.url);
const TWO_PI = Math.PI * 2;
const ROTATION_MS = 12000;
const DPR_LIMIT = 1.5;

function frac(value) {
  return ((value % 1) + 1) % 1;
}

function phaseIndex(tau, order) {
  return ((Math.round(frac(tau) * order) % order) + order) % order;
}

function uniqueOrbit(record) {
  const points = new Map();
  const base = record.render.base || [0.31, 0.17];
  for (const operation of record.render.ops) {
    const x = frac(
      operation.M[0][0] * base[0]
      + operation.M[0][1] * base[1]
      + operation.v[0],
    );
    const y = frac(
      operation.M[1][0] * base[0]
      + operation.M[1][1] * base[1]
      + operation.v[1],
    );
    const z = frac(operation.tau);
    const key = `${Math.round(x * 1e6)},${Math.round(y * 1e6)},${Math.round(z * 1e6)}|${operation.M.flat().join(",")}`;
    if (!points.has(key)) points.set(key, { x, y, z, operation });
  }
  return [...points.values()];
}

function multiplyPoint(record, point) {
  const [a1, a2] = record.render.basis;
  return {
    x: point.x * a1[0] + point.y * a2[0],
    y: point.x * a1[1] + point.y * a2[1],
    z: point.z,
  };
}

function transformedMotif(record, orbitPoint, radius = 0.052) {
  const shape = [
    [-0.78, -0.45],
    [0.32, -0.62],
    [0.72, -0.05],
    [0.24, 0.16],
    [0.45, 0.69],
    [-0.58, 0.43],
  ];
  return shape.map(([x, y]) => {
    const operation = orbitPoint.operation;
    const dx = radius * (operation.M[0][0] * x + operation.M[0][1] * y);
    const dy = radius * (operation.M[1][0] * x + operation.M[1][1] * y);
    return multiplyPoint(record, {
      x: orbitPoint.x + dx,
      y: orbitPoint.y + dy,
      z: orbitPoint.z,
    });
  });
}

function worldBounds(record) {
  const corners = [];
  for (const x of [-0.08, 1.08]) {
    for (const y of [-0.08, 1.08]) {
      for (const z of [-0.06, 1.12]) corners.push(multiplyPoint(record, { x, y, z }));
    }
  }
  const xs = corners.map((point) => point.x);
  const ys = corners.map((point) => point.y);
  return {
    horizontalRadius: Math.max(
      Math.max(...xs) - Math.min(...xs),
      Math.max(...ys) - Math.min(...ys),
      0.8,
    ) / 2,
  };
}

function projection(record, width, height, yaw) {
  const pitch = 0.56;
  const center = multiplyPoint(record, { x: 0.5, y: 0.5, z: 0.5 });
  const bounds = worldBounds(record);
  const scale = Math.min(width, height) / (2.75 * bounds.horizontalRadius + 1.35);
  const cosYaw = Math.cos(yaw);
  const sinYaw = Math.sin(yaw);
  const cosPitch = Math.cos(pitch);
  const sinPitch = Math.sin(pitch);
  return (point) => {
    const x = point.x - center.x;
    const y = point.y - center.y;
    const z = point.z - center.z;
    const rotatedX = cosYaw * x - sinYaw * y;
    const rotatedY = sinYaw * x + cosYaw * y;
    return {
      x: width / 2 + rotatedX * scale,
      y: height / 2 + (rotatedY * sinPitch - z * cosPitch) * scale,
      depth: rotatedY * cosPitch + z * sinPitch,
      scale,
    };
  };
}

function line(context, start, end, color, width = 1, dash = []) {
  context.save();
  context.beginPath();
  context.moveTo(start.x, start.y);
  context.lineTo(end.x, end.y);
  context.setLineDash(dash);
  context.lineWidth = width;
  context.strokeStyle = color;
  context.stroke();
  context.restore();
}

function polygon(context, points, fill, stroke, width = 1) {
  if (points.length === 0) return;
  context.beginPath();
  context.moveTo(points[0].x, points[0].y);
  for (const point of points.slice(1)) context.lineTo(point.x, point.y);
  context.closePath();
  context.fillStyle = fill;
  context.fill();
  context.lineWidth = width;
  context.strokeStyle = stroke;
  context.stroke();
}

function hexToRgba(hex, alpha) {
  const value = hex.replace("#", "");
  const channels = value.length === 3
    ? value.split("").map((part) => parseInt(part + part, 16))
    : [0, 2, 4].map((index) => parseInt(value.slice(index, index + 2), 16));
  return `rgba(${channels[0]}, ${channels[1]}, ${channels[2]}, ${alpha})`;
}

function drawArrow(context, start, end, color) {
  line(context, start, end, color, 2.2);
  const angle = Math.atan2(end.y - start.y, end.x - start.x);
  const length = 9;
  context.beginPath();
  context.moveTo(end.x, end.y);
  context.lineTo(
    end.x - length * Math.cos(angle - Math.PI / 6),
    end.y - length * Math.sin(angle - Math.PI / 6),
  );
  context.lineTo(
    end.x - length * Math.cos(angle + Math.PI / 6),
    end.y - length * Math.sin(angle + Math.PI / 6),
  );
  context.closePath();
  context.fillStyle = color;
  context.fill();
}

class SpaceGroupViewer {
  constructor(root, record) {
    if (!record?.render?.ops?.length || !record?.space_group) {
      throw new Error("missing lifted space-group data");
    }
    this.root = root;
    this.record = record;
    this.stage = root.querySelector(".space-stage");
    this.canvas = root.querySelector("canvas");
    this.toggle = root.querySelector("[data-space-toggle]");
    this.slider = root.querySelector("[data-space-slider]");
    this.output = root.querySelector("[data-space-output]");
    this.yaw = Number(this.slider?.value || 0) * TWO_PI;
    this.playing = false;
    this.active = false;
    this.nearViewport = false;
    this.frameRequest = 0;
    this.startedAt = 0;
    this.orbit = uniqueOrbit(record);

    this.canvas.setAttribute(
      "aria-label",
      `Rotatable unit-cell view of space group ${record.space_group.hm_short}, International number ${record.space_group.it_number}.`,
    );
    this.toggle?.addEventListener("click", () => this.togglePlayback());
    this.slider?.addEventListener("input", () => {
      this.pause();
      this.yaw = Number(this.slider.value) * TWO_PI;
      this.updateReadout();
      this.draw();
    });
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
      this.stage.dataset.state = "ready";
      if (this.toggle) this.toggle.disabled = false;
      if (this.slider) this.slider.disabled = false;
    }
    if (this.playing && !document.hidden) this.startFrames();
  }

  deactivate() {
    this.nearViewport = false;
    this.suspendFrames();
    if (!this.active) return;
    this.active = false;
    this.stage.dataset.state = "static";
    this.canvas.width = 1;
    this.canvas.height = 1;
  }

  resizeAndDraw() {
    const bounds = this.stage.getBoundingClientRect();
    const width = Math.max(1, Math.round(bounds.width));
    const height = Math.max(1, Math.round(bounds.height));
    const dpr = Math.min(window.devicePixelRatio || 1, DPR_LIMIT);
    this.canvas.width = Math.max(1, Math.round(width * dpr));
    this.canvas.height = Math.max(1, Math.round(height * dpr));
    // Keep CSS sizing relative to the responsive stage. Pixel dimensions are
    // still pinned above for a sharp backing buffer, but must not survive a
    // viewport change as an overflowing inline width.
    this.canvas.style.width = "100%";
    this.canvas.style.height = "100%";
    this.draw();
  }

  draw() {
    if (!this.active) return;
    const context = this.canvas.getContext("2d");
    if (!context) return;
    const dpr = Math.min(window.devicePixelRatio || 1, DPR_LIMIT);
    const width = this.canvas.width / dpr;
    const height = this.canvas.height / dpr;
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    context.clearRect(0, 0, width, height);

    const background = context.createLinearGradient(0, 0, 0, height);
    background.addColorStop(0, "#f5f8f6");
    background.addColorStop(1, "#faf8f1");
    context.fillStyle = background;
    context.fillRect(0, 0, width, height);

    const project = projection(this.record, width, height, this.yaw);
    const cellCorners = [];
    for (const x of [0, 1]) {
      for (const y of [0, 1]) {
        for (const z of [0, 1]) cellCorners.push({ x, y, z, p: project(multiplyPoint(this.record, { x, y, z })) });
      }
    }
    const corner = (x, y, z) => cellCorners.find((item) => item.x === x && item.y === y && item.z === z).p;

    for (const z of [0, 1]) {
      polygon(
        context,
        [[0, 0], [1, 0], [1, 1], [0, 1]].map(([x, y]) => corner(x, y, z)),
        z === 0 ? "rgba(0, 111, 99, 0.035)" : "rgba(0, 111, 99, 0.018)",
        "rgba(77, 96, 89, 0.30)",
        1,
      );
    }
    for (const [x, y] of [[0, 0], [1, 0], [1, 1], [0, 1]]) {
      line(context, corner(x, y, 0), corner(x, y, 1), "rgba(77, 96, 89, 0.34)", 1, [4, 4]);
    }

    const items = [];
    for (const orbitPoint of this.orbit) {
      const center = project(multiplyPoint(this.record, orbitPoint));
      const motif = transformedMotif(this.record, orbitPoint).map(project);
      items.push({ orbitPoint, center, motif, depth: center.depth });
      if (orbitPoint.z === 0) {
        const ghostPoint = { ...orbitPoint, z: 1 };
        const ghostCenter = project(multiplyPoint(this.record, ghostPoint));
        const ghostMotif = transformedMotif(this.record, ghostPoint).map(project);
        items.push({ orbitPoint: ghostPoint, center: ghostCenter, motif: ghostMotif, depth: ghostCenter.depth, ghost: true });
      }
    }
    items.sort((left, right) => left.depth - right.depth);

    const phaseGroups = new Map();
    for (const item of items.filter((candidate) => !candidate.ghost)) {
      const index = phaseIndex(item.orbitPoint.z, this.record.clock_order);
      if (!phaseGroups.has(index)) phaseGroups.set(index, []);
      phaseGroups.get(index).push(item);
    }
    const representatives = [...phaseGroups.entries()]
      .sort(([left], [right]) => left - right)
      .map(([, group]) => group[0]);
    if (representatives.length > 1) {
      for (let index = 0; index < representatives.length - 1; index += 1) {
        line(
          context,
          representatives[index].center,
          representatives[index + 1].center,
          "rgba(178, 58, 44, 0.55)",
          1.5,
          [3, 4],
        );
      }
    }

    for (const item of items) {
      const index = phaseIndex(item.orbitPoint.z, this.record.clock_order);
      const color = this.record.phase_residues[index]?.color || "#0072B2";
      const alpha = item.ghost ? 0.34 : 0.88;
      polygon(context, item.motif, hexToRgba(color, alpha), `rgba(30, 40, 36, ${item.ghost ? 0.35 : 0.75})`, 0.9);
      const radius = item.ghost ? 1.4 : 2.2;
      context.beginPath();
      context.arc(item.center.x, item.center.y, radius, 0, TWO_PI);
      context.fillStyle = item.ghost ? "rgba(255,255,255,0.7)" : "#ffffff";
      context.fill();
      context.strokeStyle = `rgba(31, 42, 38, ${item.ghost ? 0.35 : 0.8})`;
      context.lineWidth = 0.8;
      context.stroke();
    }

    const axisStart = project(multiplyPoint(this.record, { x: 0, y: 0, z: -0.05 }));
    const axisEnd = project(multiplyPoint(this.record, { x: 0, y: 0, z: 1.26 }));
    drawArrow(context, axisStart, axisEnd, "#b23a2c");
    context.fillStyle = "#8f3025";
    context.font = "650 11px ui-sans-serif, -apple-system, sans-serif";
    context.fillText("lift direction z", axisEnd.x + 8, axisEnd.y + 3);

    const label = `${this.record.space_group.hm_short}  ·  No. ${this.record.space_group.it_number}`;
    context.fillStyle = "rgba(23, 26, 24, 0.80)";
    context.font = "650 12px ui-sans-serif, -apple-system, sans-serif";
    context.fillText(label, 12, height - 14);
  }

  updateReadout() {
    const turns = frac(this.yaw / TWO_PI);
    if (this.slider) this.slider.value = turns.toFixed(3);
    if (this.output) {
      const degrees = Math.round(turns * 360);
      this.output.value = `${degrees}°`;
      this.output.textContent = `${degrees}°`;
    }
  }

  togglePlayback() {
    if (this.playing) this.pause();
    else this.play();
  }

  play() {
    this.playing = true;
    this.startedAt = performance.now() - frac(this.yaw / TWO_PI) * ROTATION_MS;
    if (this.toggle) {
      this.toggle.setAttribute("aria-pressed", "true");
      const label = this.toggle.querySelector("[data-space-toggle-label]");
      if (label) label.textContent = "Pause";
    }
    this.startFrames();
  }

  pause() {
    this.playing = false;
    this.suspendFrames();
    if (this.toggle) {
      this.toggle.setAttribute("aria-pressed", "false");
      const label = this.toggle.querySelector("[data-space-toggle-label]");
      if (label) label.textContent = "Rotate";
    }
  }

  startFrames() {
    if (this.frameRequest || !this.active || !this.nearViewport || document.hidden) return;
    const tick = (timestamp) => {
      this.frameRequest = 0;
      if (!this.playing || !this.active || !this.nearViewport || document.hidden) return;
      this.yaw = frac((timestamp - this.startedAt) / ROTATION_MS) * TWO_PI;
      this.updateReadout();
      this.draw();
      this.frameRequest = requestAnimationFrame(tick);
    };
    this.frameRequest = requestAnimationFrame(tick);
  }

  suspendFrames() {
    if (this.frameRequest) cancelAnimationFrame(this.frameRequest);
    this.frameRequest = 0;
  }
}

function initializeTabs() {
  const initialHash = location.hash;
  if (initialHash) history.replaceState(null, "", `${location.pathname}${location.search}`);
  const controllers = new Map();
  const defaults = [];

  for (const host of document.querySelectorAll("[data-space-tabs]")) {
    const tablist = host.querySelector("[data-space-tablist]");
    const tabs = [...host.querySelectorAll("[data-space-tab]")];
    const items = tabs.map((tab) => {
      const panel = document.getElementById(tab.dataset.panelId || "");
      return panel ? { tab, panel } : null;
    }).filter(Boolean);
    if (!tablist || items.length !== tabs.length || items.length === 0) continue;

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
        const active = panel.id === groupId;
        tab.setAttribute("aria-selected", String(active));
        tab.tabIndex = active ? 0 : -1;
        panel.hidden = !active;
      }
      if (options.focus) selected.tab.focus();
      if (options.history) history[options.history === "push" ? "pushState" : "replaceState"](null, "", `#${groupId}`);
      if (options.scroll) requestAnimationFrame(() => selected.panel.scrollIntoView({ block: "start" }));
      if (previousId !== groupId) {
        document.dispatchEvent(new CustomEvent("space:tab-change", {
          detail: { activeId: groupId, inactiveId: previousId || null },
        }));
      }
      return true;
    };

    items.forEach(({ tab, panel }, index) => {
      tab.addEventListener("click", (event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        activate(panel.id, { history: location.hash === `#${panel.id}` ? null : "push" });
      });
      tab.addEventListener("keydown", (event) => {
        let next = null;
        if (event.key === "ArrowRight" || event.key === "ArrowDown") next = (index + 1) % items.length;
        else if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = (index - 1 + items.length) % items.length;
        else if (event.key === "Home") next = 0;
        else if (event.key === "End") next = items.length - 1;
        if (next === null) return;
        event.preventDefault();
        activate(items[next].panel.id, { focus: true, history: "replace" });
      });
      controllers.set(panel.id, { activate });
    });
    const defaultId = items[0].panel.id;
    defaults.push({ activate, groupId: defaultId });
    activate(defaultId);
  }

  const openFromHash = (scroll = true) => {
    const rawId = location.hash.replace(/^#/, "");
    if (!rawId) {
      for (const entry of defaults) entry.activate(entry.groupId);
      return;
    }
    let id;
    try {
      id = decodeURIComponent(rawId);
    } catch {
      return;
    }
    const controller = controllers.get(id);
    if (controller) controller.activate(id, { scroll });
    else if (scroll) document.getElementById(id)?.scrollIntoView({ block: "start" });
  };

  if (initialHash) history.replaceState(null, "", initialHash);
  openFromHash(true);
  window.addEventListener("load", () => openFromHash(true), { once: true });
  window.addEventListener("hashchange", () => openFromHash(true));
  window.addEventListener("popstate", () => openFromHash(true));
}

async function initializeViewers() {
  const roots = [...document.querySelectorAll("[data-space-viewer]")];
  if (roots.length === 0) return;
  let payload;
  try {
    const response = await fetch(DATA_URL, { credentials: "same-origin" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    payload = await response.json();
    if (!Array.isArray(payload.groups) || payload.groups.length !== 68) throw new Error("expected 68 records");
  } catch (error) {
    console.error("Space-group correspondence data failed to load", error);
    return;
  }

  const records = new Map(payload.groups.map((record) => [record.id, record]));
  const viewers = [];
  const byId = new Map();
  for (const root of roots) {
    try {
      const record = records.get(root.dataset.groupId);
      if (!record) throw new Error(`missing record ${root.dataset.groupId}`);
      const viewer = new SpaceGroupViewer(root, record);
      viewers.push(viewer);
      byId.set(record.id, viewer);
    } catch (error) {
      console.error("Space-group viewer failed to initialize", root.dataset.groupId, error);
    }
  }

  document.addEventListener("space:tab-change", (event) => {
    const inactive = byId.get(event.detail?.inactiveId);
    const active = byId.get(event.detail?.activeId);
    if (inactive && inactive !== active) inactive.deactivate();
    if (active) {
      active.pause();
      active.yaw = 0.095 * TWO_PI;
      active.updateReadout();
    }
  });

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        const viewer = viewers.find((candidate) => candidate.root === entry.target);
        if (!viewer) continue;
        if (entry.isIntersecting && !viewer.root.closest("[hidden]")) viewer.activate();
        else viewer.deactivate();
      }
    }, { rootMargin: "500px 0px" });
    for (const viewer of viewers) observer.observe(viewer.root);
  } else {
    for (const viewer of viewers.filter((candidate) => !candidate.root.closest("[hidden]"))) viewer.activate();
  }

  document.addEventListener("space:tab-change", (event) => {
    const active = byId.get(event.detail?.activeId);
    if (active && active.root.getBoundingClientRect().top < innerHeight + 500) active.activate();
  });
  document.addEventListener("visibilitychange", () => {
    for (const viewer of viewers) {
      if (document.hidden) viewer.suspendFrames();
      else if (viewer.playing) viewer.startFrames();
    }
  });
}

initializeTabs();
void initializeViewers();

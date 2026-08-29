(function initializeTorusColorings(root) {
  "use strict";

  const N = 3;
  const CELL_COUNT = N * N;
  const ACTING_GROUP_ORDER = N * N * 2;

  function patternFromInteger(value) {
    return value.toString(2).padStart(CELL_COUNT, "0");
  }

  function complement(pattern) {
    return [...pattern].map((value) => (value === "0" ? "1" : "0")).join("");
  }

  function translate(pattern, dx, dy) {
    let translated = "";
    for (let y = 0; y < N; y += 1) {
      for (let x = 0; x < N; x += 1) {
        const sourceX = (x - dx + N) % N;
        const sourceY = (y - dy + N) % N;
        translated += pattern[sourceY * N + sourceX];
      }
    }
    return translated;
  }

  function orbit(pattern) {
    const values = new Set();
    for (let dy = 0; dy < N; dy += 1) {
      for (let dx = 0; dx < N; dx += 1) {
        const translated = translate(pattern, dx, dy);
        values.add(translated);
        values.add(complement(translated));
      }
    }
    return values;
  }

  function weight(pattern) {
    return [...pattern].reduce((sum, value) => sum + Number(value), 0);
  }

  function compareCanonicalCandidates(left, right) {
    return weight(left) - weight(right) || left.localeCompare(right);
  }

  function canonical(pattern) {
    return [...orbit(pattern)].sort(compareCanonicalCandidates)[0];
  }

  function records() {
    const representatives = new Set();
    for (let value = 0; value < 2 ** CELL_COUNT; value += 1) {
      representatives.add(canonical(patternFromInteger(value)));
    }

    const result = [...representatives]
      .sort(compareCanonicalCandidates)
      .map((pattern, index) => {
        const orbitSize = orbit(pattern).size;
        return {
          id: `torus-${String(index + 1).padStart(2, "0")}`,
          index: index + 1,
          pattern,
          rows: [0, 1, 2].map((row) => pattern.slice(row * N, row * N + N)),
          weight: weight(pattern),
          orbitSize,
          stabilizerSize: ACTING_GROUP_ORDER / orbitSize,
        };
      });

    if (result.length !== 32) {
      throw new Error(`Expected 32 equivalence classes; found ${result.length}.`);
    }
    if (result.reduce((sum, record) => sum + record.orbitSize, 0) !== 2 ** CELL_COUNT) {
      throw new Error("The computed orbits do not partition all 512 binary patterns.");
    }
    return result;
  }

  function svgElement(name, attributes = {}) {
    const element = document.createElementNS("http://www.w3.org/2000/svg", name);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
    return element;
  }

  function patternSvg(record) {
    const cellSize = 24;
    const repeatedCells = 9;
    const size = cellSize * repeatedCells;
    const titleId = `${record.id}-image-title`;
    const svg = svgElement("svg", {
      class: "torus-pattern",
      viewBox: `0 0 ${size} ${size}`,
      role: "img",
      "aria-labelledby": titleId,
      "shape-rendering": "crispEdges",
    });

    const title = svgElement("title", { id: titleId });
    title.textContent = `Class ${record.index}: periodic extension of ${record.rows.join(" slash ")}`;
    svg.append(title);

    for (let y = 0; y < repeatedCells; y += 1) {
      for (let x = 0; x < repeatedCells; x += 1) {
        const value = record.pattern[(y % N) * N + (x % N)];
        svg.append(svgElement("rect", {
          x: x * cellSize,
          y: y * cellSize,
          width: cellSize,
          height: cellSize,
          class: value === "0" ? "cell cell-a" : "cell cell-b",
        }));
      }
    }

    for (let offset = 0; offset <= repeatedCells; offset += 1) {
      const position = offset * cellSize;
      svg.append(svgElement("line", {
        x1: position,
        y1: 0,
        x2: position,
        y2: size,
        class: "cell-line",
      }));
      svg.append(svgElement("line", {
        x1: 0,
        y1: position,
        x2: size,
        y2: position,
        class: "cell-line",
      }));
    }

    for (let offset = N; offset < repeatedCells; offset += N) {
      const position = offset * cellSize;
      svg.append(svgElement("line", {
        x1: position,
        y1: 0,
        x2: position,
        y2: size,
        class: "domain-line",
      }));
      svg.append(svgElement("line", {
        x1: 0,
        y1: position,
        x2: size,
        y2: position,
        class: "domain-line",
      }));
    }

    svg.append(svgElement("rect", {
      x: cellSize * N,
      y: cellSize * N,
      width: cellSize * N,
      height: cellSize * N,
      class: "central-domain",
    }));
    return svg;
  }

  function patternCard(record) {
    const article = document.createElement("article");
    article.className = "pattern-card";
    article.id = record.id;

    const header = document.createElement("header");
    const heading = document.createElement("h3");
    heading.textContent = `Class ${String(record.index).padStart(2, "0")}`;
    const code = document.createElement("code");
    code.textContent = record.rows.join("/");
    code.setAttribute("aria-label", `Canonical word ${record.rows.join(", ")}`);
    header.append(heading, code);

    const figure = document.createElement("figure");
    figure.append(patternSvg(record));
    const caption = document.createElement("figcaption");
    caption.innerHTML = `<span>${record.weight} B</span><span>orbit ${record.orbitSize}</span><span>stabilizer ${record.stabilizerSize}</span>`;
    figure.append(caption);

    article.append(header, figure);
    return article;
  }

  function render() {
    const catalog = document.querySelector("[data-torus-catalog]");
    if (!catalog) return;

    const allRecords = records();
    const byWeight = new Map();
    allRecords.forEach((record) => {
      if (!byWeight.has(record.weight)) byWeight.set(record.weight, []);
      byWeight.get(record.weight).push(record);
    });

    byWeight.forEach((group, groupWeight) => {
      const section = document.createElement("section");
      section.className = "weight-group";
      section.setAttribute("aria-labelledby", `weight-${groupWeight}-title`);

      const heading = document.createElement("h2");
      heading.id = `weight-${groupWeight}-title`;
      heading.innerHTML = `${groupWeight} <span>minority-color ${groupWeight === 1 ? "cell" : "cells"}</span><small>${group.length} ${group.length === 1 ? "class" : "classes"}</small>`;

      const grid = document.createElement("div");
      grid.className = "pattern-grid";
      group.forEach((record) => grid.append(patternCard(record)));
      section.append(heading, grid);
      catalog.append(section);
    });

    const count = document.querySelector("[data-class-count]");
    if (count) count.textContent = String(allRecords.length);
  }

  const api = {
    canonical,
    complement,
    orbit,
    records,
    translate,
  };

  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", render, { once: true });
    } else {
      render();
    }
  }
  if (root) root.TorusColorings = api;
}(typeof window !== "undefined" ? window : globalThis));

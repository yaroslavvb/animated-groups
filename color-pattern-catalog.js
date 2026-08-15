(() => {
  "use strict";

  const DATA_URL = "data/color-pattern-catalog.json?v=presentations";
  const SVG_NS = "http://www.w3.org/2000/svg";
  const PALETTES = {
    1: ["#9aa19e"],
    2: ["#0072B2", "#E69F00"],
    3: ["#0072B2", "#E69F00", "#009E73"],
  };
  const MOTIF_SCALE = 1.55;

  const state = {
    payload: null,
    wallpaperById: new Map(),
    groupById: new Map(),
    patternById: new Map(),
    groupsByWallpaper: new Map(),
    patternsByGroup: new Map(),
    activeGroupByWallpaper: new Map(),
    activePatternByGroup: new Map(),
    filter: "all",
    excerptWindow: null,
  };

  const byId = (id) => document.getElementById(id);
  const SUBSCRIPT_DIGITS = {"0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉"};
  const SUPERSCRIPT_DIGITS = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9"};

  function typesetSymbol(value) {
    return String(value)
      .replace(/_(\d+)/g, (_match, digits) => [...digits].map((digit) => SUBSCRIPT_DIGITS[digit]).join(""))
      .replaceAll("*", "∗");
  }

  function indexPayload(payload) {
    state.payload = payload;
    payload.wallpaper_groups.forEach((item) => state.wallpaperById.set(item.id, item));
    payload.colour_groups.forEach((item) => {
      state.groupById.set(item.id, item);
      if (!state.groupsByWallpaper.has(item.wallpaper_id)) {
        state.groupsByWallpaper.set(item.wallpaper_id, []);
      }
      state.groupsByWallpaper.get(item.wallpaper_id).push(item);
    });
    payload.pattern_types.forEach((item) => {
      state.patternById.set(item.id, item);
      if (!state.patternsByGroup.has(item.colour_group_id)) {
        state.patternsByGroup.set(item.colour_group_id, []);
      }
      state.patternsByGroup.get(item.colour_group_id).push(item);
    });
    state.groupsByWallpaper.forEach((groups) => groups.sort((a, b) => {
      const aTrivial = a.number_of_colours === 1 ? 1 : 0;
      const bTrivial = b.number_of_colours === 1 ? 1 : 0;
      return aTrivial - bTrivial || a.number_of_colours - b.number_of_colours || a.index_within_parent - b.index_within_parent;
    }));
  }

  function textElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = text;
    return element;
  }

  function appendTableRow(table, label, value) {
    const row = document.createElement("tr");
    const heading = document.createElement("th");
    heading.scope = "row";
    heading.textContent = label;
    const cell = document.createElement("td");
    if (value instanceof Node) cell.append(value);
    else cell.textContent = value;
    row.append(heading, cell);
    table.append(row);
  }

  function excerptLink(excerpt, label, returnId) {
    const parameters = new URLSearchParams({
      image: excerpt.image,
      title: excerpt.title,
      context: excerpt.context,
      alt: excerpt.alt,
      return: `color-pattern-catalog.html#${returnId}`,
      returnLabel: "Return to pattern catalog",
    });
    if (excerpt.source_url) parameters.set("source", excerpt.source_url);
    const link = document.createElement("a");
    link.className = "book-evidence-link";
    link.href = `book-excerpt.html?v=pattern-sources&${parameters.toString()}`;
    link.target = "color-pattern-book-excerpt";
    if (label instanceof Node) link.append(label);
    else link.textContent = label;
    return link;
  }

  function shortSignatureElement(signature) {
    const wrapper = document.createElement("span");
    wrapper.className = "inline-short-signature";
    let index = 0;
    while (index < signature.length) {
      const character = signature[index];
      if (SUPERSCRIPT_DIGITS[character]) {
        const superscript = document.createElement("sup");
        let digits = "";
        while (index < signature.length && SUPERSCRIPT_DIGITS[signature[index]]) {
          digits += SUPERSCRIPT_DIGITS[signature[index]];
          index += 1;
        }
        superscript.textContent = digits;
        wrapper.append(superscript);
        continue;
      }
      if (character === "^" && signature[index + 1] === "(") {
        const end = signature.indexOf(")", index + 2);
        if (end >= 0) {
          const superscript = document.createElement("sup");
          superscript.textContent = signature.slice(index + 1, end + 1);
          wrapper.append(superscript);
          index = end + 1;
          continue;
        }
      }
      if (character === "*") {
        wrapper.append(textElement("span", "orbifold-star", "∗"));
      } else {
        wrapper.append(document.createTextNode(character));
      }
      index += 1;
    }
    return wrapper;
  }

  function sourceSymbolLink(excerpt, returnId, content, accessibleLabel) {
    const wrapper = document.createDocumentFragment();
    wrapper.append(content, textElement("span", "source-link-mark", "↗"));
    const link = excerptLink(excerpt, wrapper, returnId);
    link.classList.add("source-value-link");
    link.setAttribute("aria-label", accessibleLabel);
    return link;
  }

  function mathSymbolElement(value) {
    return textElement("span", "source-math-symbol", typesetSymbol(value));
  }

  function ghkElement(group) {
    const wrapper = document.createElement("span");
    wrapper.className = "ghk-expression source-math-symbol";
    ["G", "H", "K"].forEach((key, index) => {
      if (index > 0) wrapper.append(textElement("span", "ghk-separator", "/"));
      wrapper.append(textElement("span", "ghk-term", typesetSymbol(group.ghk[key])));
    });
    wrapper.setAttribute(
      "aria-label",
      `G ${typesetSymbol(group.ghk.G)}; H ${typesetSymbol(group.ghk.H)}; K ${typesetSymbol(group.ghk.K)}`,
    );
    return wrapper;
  }

  function permutationNotation(permutation) {
    const labels = ["A", "B", "C"].slice(0, permutation.length);
    if (permutation.every((image, index) => image === index)) return "id";
    const moved = permutation.map((image, index) => image !== index ? index : -1).filter((index) => index >= 0);
    if (moved.length === 2) return `(${labels[moved[0]]} ${labels[moved[1]]})`;
    const cycle = [0];
    while (cycle.length < permutation.length) cycle.push(permutation[cycle[cycle.length - 1]]);
    return `(${cycle.map((index) => labels[index]).join(" ")})`;
  }

  function permutationDescription(permutation) {
    const labels = ["A", "B", "C"].slice(0, permutation.length);
    if (permutation.every((image, index) => image === index)) {
      return labels.map((label) => `${label}→${label}`).join(", ");
    }
    const fixed = permutation.map((image, index) => image === index ? index : -1).filter((index) => index >= 0);
    if (fixed.length === permutation.length - 2) {
      const moved = permutation.map((image, index) => image !== index ? index : -1).filter((index) => index >= 0);
      const fixedText = fixed.length ? `; ${labels[fixed[0]]} fixed` : "";
      return `${labels[moved[0]]}↔${labels[moved[1]]}${fixedText}`;
    }
    const cycle = [0];
    while (cycle.length < permutation.length) cycle.push(permutation[cycle[cycle.length - 1]]);
    return `${cycle.map((index) => labels[index]).join("→")}→${labels[cycle[0]]}`;
  }

  function actionPaletteElement(group) {
    const palette = document.createElement("div");
    palette.className = "action-palette";
    palette.title = "Canonical colour labels; simultaneous relabelling gives the same colour group.";
    palette.setAttribute("aria-label", "Canonical colour labels used in the permutations");
    ["A", "B", "C"].slice(0, group.number_of_colours).forEach((label, index) => {
      const swatch = textElement("span", "action-colour", label);
      swatch.style.setProperty("--swatch", PALETTES[group.number_of_colours][index]);
      palette.append(swatch);
    });
    return palette;
  }

  function presentationElement(group) {
    const section = document.createElement("section");
    section.className = "group-presentation";
    const titleId = `${group.id}-presentation-title`;
    section.setAttribute("aria-labelledby", titleId);

    const heading = document.createElement("header");
    heading.className = "presentation-heading";
    const title = textElement("h4", "", "Presentation");
    title.id = titleId;
    heading.append(title, actionPaletteElement(group));

    const table = document.createElement("table");
    table.dataset.presentation = group.id;
    const caption = textElement(
      "caption",
      "visually-hidden",
      `Geometric generators and induced colour permutations for ${group.id}`,
    );
    const body = document.createElement("tbody");
    group.generator_colour_actions.forEach((action) => {
      const row = document.createElement("tr");
      row.className = "presentation-generator-row";
      const generatorCell = document.createElement("th");
      generatorCell.scope = "row";
      generatorCell.append(
        textElement("span", "generator-key", action.generator),
        textElement("span", "generator-geometry", action.geometry),
      );
      const permutationCell = document.createElement("td");
      const notation = permutationNotation(action.colour_permutation);
      const description = permutationDescription(action.colour_permutation);
      permutationCell.setAttribute(
        "aria-label",
        notation === "id" ? `Identity permutation; ${description}` : description,
      );
      if (notation !== "id") {
        const value = textElement("span", "presentation-permutation", notation);
        value.title = description;
        permutationCell.append(value);
      }
      row.append(generatorCell, permutationCell);
      body.append(row);
    });
    table.append(caption, body);

    const relations = document.createElement("p");
    relations.className = "presentation-relations";
    relations.append(
      textElement("strong", "", "Relations"),
      textElement(
        "span",
        "",
        `G = ⟨${group.presentation.generators.join(", ")} | ${group.presentation.relations}⟩`,
      ),
    );
    section.append(heading, table, relations);
    return section;
  }

  function hashString(value) {
    let result = 2166136261;
    for (let index = 0; index < value.length; index += 1) {
      result ^= value.charCodeAt(index);
      result = Math.imul(result, 16777619);
    }
    return result >>> 0;
  }

  function svgElement(tag, attributes = {}) {
    const element = document.createElementNS(SVG_NS, tag);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
    return element;
  }

  function orbitOrder(parent) {
    if (parent === "p6" || parent === "p6m") return 6;
    if (parent === "p3" || parent === "p3m1" || parent === "p31m") return 3;
    if (parent === "p4" || parent === "p4m" || parent === "p4g") return 4;
    if (["p2", "pmm", "pmg", "pgg", "cmm"].includes(parent)) return 2;
    return 1;
  }

  function addMotif(svg, x, y, angle, colour, mirrored) {
    const group = svgElement("g", {
      transform: `translate(${x.toFixed(2)} ${y.toFixed(2)}) rotate(${angle.toFixed(2)}) scale(${mirrored ? -MOTIF_SCALE : MOTIF_SCALE} ${MOTIF_SCALE})`,
    });
    const diamond = svgElement("polygon", {
      points: "0,-13 13,0 0,13 -13,0",
      fill: colour,
      stroke: "#26322e",
      "stroke-width": 1.25,
      "vector-effect": "non-scaling-stroke",
    });
    const letter = svgElement("text", {
      x: 0,
      y: 0.75,
      fill: "#fffaf1",
      stroke: "#26322e",
      "stroke-width": 0.6,
      "paint-order": "stroke fill",
      "font-family": "Arial, Helvetica, sans-serif",
      "font-size": 13,
      "font-weight": 800,
      "text-anchor": "middle",
      "dominant-baseline": "middle",
    });
    letter.textContent = "R";
    group.append(diamond, letter);
    svg.append(group);
  }

  function buildP4TwoColourPattern(svg, pattern, group) {
    // Write p4 as <A, tx, ty>, where A is a quarter-turn about a lattice
    // point.  If a=chi(A) and u=chi(tx)=chi(ty), then the other 4-centre has
    // character a+u and the intervening 2-centre has character u.
    //
    //   ¹4²4²2 (K=442):  a=0, u=1 — monochrome 4-orbits checkerboard.
    //   ²4²4¹2 (K=2222): a=1, u=0 — alternating colours in every 4-orbit.
    const quarterTurnShift = group.all_colours_kernel_K === "2222" ? 1 : 0;
    const translationShift = group.all_colours_kernel_K === "442" ? 1 : 0;
    const siblings = state.patternsByGroup.get(group.id) || [];
    const siblingIndex = Math.max(0, siblings.findIndex((item) => item.id === pattern.id));
    const lattice = siblingIndex % 2 === 0 ? 138 : 152;
    const seedVector = siblingIndex % 2 === 0 ? [39, 17] : [48, 14];
    const guideRadius = Math.hypot(...seedVector) + 13 * MOTIF_SCALE + 3;
    const guide = svgElement("g", {opacity: 0.19, stroke: "#75837d", "stroke-width": 0.8});
    const motifs = svgElement("g");
    const columns = Math.ceil(960 / lattice);
    const rows = Math.ceil(560 / lattice);

    for (let row = 0; row < rows; row += 1) {
      for (let col = 0; col < columns; col += 1) {
        const cx = (col + 0.5) * lattice;
        const cy = (row + 0.5) * lattice;
        guide.append(svgElement("circle", {cx, cy, r: guideRadius, fill: "none"}));
        for (let orbit = 0; orbit < 4; orbit += 1) {
          const [sx, sy] = seedVector;
          const rotated = (
            orbit === 0 ? [sx, sy]
              : orbit === 1 ? [-sy, sx]
                : orbit === 2 ? [-sx, -sy]
                  : [sy, -sx]
          );
          const rawPhase = translationShift * (col + row) + quarterTurnShift * orbit;
          const colourIndex = ((rawPhase % 2) + 2) % 2;
          addMotif(
            motifs,
            cx + rotated[0],
            cy + rotated[1],
            orbit * 90,
            PALETTES[2][colourIndex],
            false,
          );
        }
      }
    }
    svg.append(guide, motifs);
  }

  function buildPatternSvg(pattern, group, wallpaper) {
    const svg = svgElement("svg", {
      viewBox: "0 0 960 560",
      role: "img",
      "aria-label": `Schematic periodic representative for ${pattern.gs_pattern_type}`,
      preserveAspectRatio: "xMidYMid meet",
    });
    const background = svgElement("rect", {x: 0, y: 0, width: 960, height: 560, fill: "#f8f6ee"});
    svg.append(background);

    if (wallpaper.id === "p4" && pattern.number_of_colours === 2) {
      buildP4TwoColourPattern(svg, pattern, group);
      return svg;
    }

    const seed = hashString(`${pattern.id}:${group.id}`);
    const colours = PALETTES[pattern.number_of_colours];
    const order = orbitOrder(pattern.wallpaper_id);
    const hexagonal = ["p3", "p3m1", "p31m", "p6", "p6m"].includes(pattern.wallpaper_id);
    const rigidLattice = hexagonal || ["p4", "p4m", "p4g"].includes(pattern.wallpaper_id);
    const siblings = state.patternsByGroup.get(group.id) || [];
    const siblingIndex = Math.max(0, siblings.findIndex((item) => item.id === pattern.id));
    const layoutVariant = siblingIndex % 6;
    const cols = [6, 5, 6, 5, 6, 5][layoutVariant];
    const rows = [4, 4, 5, 5, 4, 5][layoutVariant];
    const dx = 960 / (cols - 0.25);
    const dy = 560 / (rows - 0.15);
    const a = 1 + (seed % Math.max(1, pattern.number_of_colours - 1));
    const b = 1 + ((seed >>> 3) % Math.max(1, pattern.number_of_colours - 1));
    const orbitRadius = order === 1 ? 0 : [34, 43, 38, 46, 42, 36][layoutVariant];
    const guideRadius = order === 1 ? 31 : orbitRadius + 13 * MOTIF_SCALE + 3;
    const guide = svgElement("g", {opacity: 0.19, stroke: "#75837d", "stroke-width": 0.8});
    const motifs = svgElement("g");

    for (let row = -1; row <= rows; row += 1) {
      for (let col = -1; col <= cols; col += 1) {
        let x = (col + 0.55 + (hexagonal && row % 2 !== 0 ? 0.5 : 0)) * dx;
        let y = (row + 0.58) * dy;
        if (!rigidLattice) {
          if (layoutVariant === 1) x += (Math.abs(row) % 2) * dx * 0.34;
          if (layoutVariant === 2) y += (Math.abs(col) % 2) * dy * 0.2;
          if (layoutVariant === 3) x += ((row % 3) + 3) % 3 * dx * 0.14;
          if (layoutVariant === 4) x += (Math.abs(col + row) % 2) * dx * 0.18;
          if (layoutVariant === 5) y += (((col % 3) + 3) % 3) * dy * 0.13;
        }
        if (x < -50 || x > 1010 || y < -50 || y > 610) continue;
        guide.append(svgElement("circle", {cx: x, cy: y, r: guideRadius, fill: "none"}));
        const baseColour = pattern.number_of_colours === 1 ? 0 : ((a * col + b * row + colours.length * 10) % colours.length);
        for (let orbit = 0; orbit < order; orbit += 1) {
          const theta = (Math.PI * 2 * orbit) / order;
          const px = x + Math.cos(theta) * orbitRadius;
          const py = y + Math.sin(theta) * orbitRadius;
          let colourIndex = (baseColour + orbit) % colours.length;
          if (group.colour_image === "S3" && row % 2 !== 0) {
            colourIndex = (colours.length - colourIndex) % colours.length;
          }
          const mirrored = wallpaper.orbifold.includes("*") && ((col + row + orbit) & 1) !== 0;
          const motifAngle = (theta * 180) / Math.PI;
          addMotif(motifs, px, py, motifAngle, colours[colourIndex], mirrored);
        }
      }
    }
    svg.append(guide, motifs);
    return svg;
  }

  function buildPatternPane(pattern, group, wallpaper) {
    const pane = document.createElement("article");
    pane.className = "pattern-pane";
    pane.id = `panel-${pattern.id}`;
    pane.setAttribute("role", "tabpanel");
    pane.setAttribute("aria-labelledby", `tab-${pattern.id}`);

    const figure = document.createElement("figure");
    figure.className = "pattern-plate";
    figure.append(buildPatternSvg(pattern, group, wallpaper));

    const details = document.createElement("div");
    details.className = "pattern-details";

    const table = document.createElement("table");
    table.className = "pattern-data";
    appendTableRow(table, "Chaim short form", sourceSymbolLink(
      group.book_excerpt,
      pattern.id,
      shortSignatureElement(group.chaim_short_signature),
      `Open Chaim short colour signature ${group.chaim_short_signature.replaceAll("^", "")} in The Symmetries of Things`,
    ));
    appendTableRow(table, "G / H / K", ghkElement(group));
    appendTableRow(table, "G&S group symbol", sourceSymbolLink(
      pattern.book_excerpt,
      pattern.id,
      mathSymbolElement(group.gs_symbol),
      `Open Grünbaum–Shephard source crop for group symbol ${group.gs_symbol}`,
    ));
    appendTableRow(table, "G&S pattern type", sourceSymbolLink(
      pattern.book_excerpt,
      pattern.id,
      mathSymbolElement(pattern.gs_pattern_type),
      `Open Grünbaum–Shephard source crop for pattern type ${pattern.gs_pattern_type}`,
    ));
    details.append(presentationElement(group), table);
    pane.append(figure, details);
    return pane;
  }

  function buildGroupPanel(group) {
    const wallpaper = state.wallpaperById.get(group.wallpaper_id);
    const patterns = state.patternsByGroup.get(group.id) || [];
    const panel = document.createDocumentFragment();

    const selector = document.createElement("div");
    selector.className = "pattern-selector";
    const tabs = document.createElement("nav");
    tabs.className = "pattern-tabs";
    tabs.setAttribute("role", "tablist");
    tabs.setAttribute("aria-label", `Pattern types in ${typesetSymbol(group.chaim_notation)}`);
    patterns.forEach((pattern, index) => {
      const tab = document.createElement("a");
      tab.className = "pattern-tab";
      tab.id = `tab-${pattern.id}`;
      tab.href = `#${pattern.id}`;
      tab.dataset.patternId = pattern.id;
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-controls", `panel-${pattern.id}`);
      tab.setAttribute("aria-selected", index === 0 ? "true" : "false");
      tab.tabIndex = index === 0 ? 0 : -1;
      tab.textContent = typesetSymbol(pattern.gs_pattern_type);
      tabs.append(tab);
    });
    selector.append(tabs);

    const body = document.createElement("div");
    body.dataset.patternPanelHost = "";
    const selectedPatternId = state.activePatternByGroup.get(group.id);
    const selectedPattern = state.patternById.get(selectedPatternId) || patterns[0];
    if (selectedPattern) body.append(buildPatternPane(selectedPattern, group, wallpaper));
    panel.append(selector, body);
    return panel;
  }

  function groupIsVisible(group) {
    return state.filter === "all" || String(group.number_of_colours) === state.filter;
  }

  function activatePattern(patternId, {updateHash = true, focus = false} = {}) {
    const pattern = state.patternById.get(patternId);
    if (!pattern) return false;
    const group = state.groupById.get(pattern.colour_group_id);
    const wallpaper = state.wallpaperById.get(pattern.wallpaper_id);
    const section = document.querySelector(`[data-wallpaper-id="${pattern.wallpaper_id}"]`);
    if (!group || !wallpaper || !section) return false;
    if (state.activeGroupByWallpaper.get(pattern.wallpaper_id) !== group.id) {
      activateGroup(group.id, {updateHash: false});
    }
    state.activePatternByGroup.set(group.id, pattern.id);
    section.querySelectorAll("[data-pattern-id]").forEach((tab) => {
      const active = tab.dataset.patternId === pattern.id;
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
      if (active && focus) tab.focus();
    });
    const host = section.querySelector("[data-pattern-panel-host]");
    if (host) host.replaceChildren(buildPatternPane(pattern, group, wallpaper));
    if (updateHash) history.pushState(null, "", `#${pattern.id}`);
    return true;
  }

  function activateGroup(groupId, {updateHash = true, focus = false} = {}) {
    const group = state.groupById.get(groupId);
    if (!group) return false;
    const section = document.querySelector(`[data-wallpaper-id="${group.wallpaper_id}"]`);
    if (!section) return false;
    state.activeGroupByWallpaper.set(group.wallpaper_id, group.id);
    section.querySelectorAll("[data-group-id]").forEach((tab) => {
      const active = tab.dataset.groupId === group.id;
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
      if (active && focus) tab.focus();
    });
    const patterns = state.patternsByGroup.get(group.id) || [];
    if (!state.activePatternByGroup.has(group.id) && patterns.length) {
      state.activePatternByGroup.set(group.id, patterns[0].id);
    }
    const host = section.querySelector("[data-group-panel]");
    if (host) {
      host.id = `panel-${group.id}`;
      host.setAttribute("role", "tabpanel");
      host.setAttribute("aria-labelledby", `tab-${group.id}`);
      host.replaceChildren(buildGroupPanel(group));
    }
    if (updateHash) history.pushState(null, "", `#${group.id}`);
    return true;
  }

  function openFromHash({scroll = false} = {}) {
    const id = decodeURIComponent(location.hash.slice(1));
    if (!id) return false;
    const pattern = state.patternById.get(id);
    if (pattern) {
      activatePattern(id, {updateHash: false});
      if (scroll) byId(`wallpaper-${pattern.wallpaper_id}`)?.scrollIntoView({block: "start"});
      return true;
    }
    const group = state.groupById.get(id);
    if (group) {
      activateGroup(id, {updateHash: false});
      if (scroll) byId(`wallpaper-${group.wallpaper_id}`)?.scrollIntoView({block: "start"});
      return true;
    }
    return false;
  }

  function initializeFamilies() {
    state.payload.wallpaper_groups.forEach((wallpaper) => {
      const groups = state.groupsByWallpaper.get(wallpaper.id) || [];
      const first = groups.find(groupIsVisible) || groups[0];
      if (first) activateGroup(first.id, {updateHash: false});
    });
  }

  function applyFilter(value) {
    state.filter = value;
    document.querySelectorAll("[data-colour-filter]").forEach((button) => {
      const active = button.dataset.colourFilter === value;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    state.payload.wallpaper_groups.forEach((wallpaper) => {
      const section = document.querySelector(`[data-wallpaper-id="${wallpaper.id}"]`);
      const groups = state.groupsByWallpaper.get(wallpaper.id) || [];
      const hasMatch = groups.some(groupIsVisible);
      if (section) section.hidden = !hasMatch;
      const directoryLink = document.querySelector(`[data-directory-wallpaper-id="${wallpaper.id}"]`);
      if (directoryLink) directoryLink.hidden = !hasMatch;
      groups.forEach((group) => {
        const tab = section?.querySelector(`[data-group-id="${group.id}"]`);
        if (tab) tab.hidden = !groupIsVisible(group);
      });
      const active = state.groupById.get(state.activeGroupByWallpaper.get(wallpaper.id));
      if (hasMatch && (!active || !groupIsVisible(active))) {
        const replacement = groups.find(groupIsVisible);
        if (replacement) activateGroup(replacement.id, {updateHash: false});
      }
    });
  }

  function moveTab(current, direction, selector, dataKey, activate) {
    const container = current.closest('[role="tablist"]');
    if (!container) return;
    const tabs = [...container.querySelectorAll(selector)].filter((tab) => !tab.hidden);
    const index = tabs.indexOf(current);
    if (index < 0 || !tabs.length) return;
    let nextIndex = index;
    if (direction === "home") nextIndex = 0;
    else if (direction === "end") nextIndex = tabs.length - 1;
    else nextIndex = (index + direction + tabs.length) % tabs.length;
    const next = tabs[nextIndex];
    activate(next.dataset[dataKey], {focus: true});
  }

  function bindEvents() {
    window.addEventListener("message", (event) => {
      if (
        event.origin === window.location.origin
        && event.data?.type === "clockwork:book-excerpt-ready"
        && event.source
      ) state.excerptWindow = event.source;
    });
    document.addEventListener("click", (event) => {
      const excerpt = event.target.closest(".book-evidence-link");
      if (excerpt) {
        if (
          !event.defaultPrevented
          && event.button === 0
          && !event.metaKey
          && !event.ctrlKey
          && !event.shiftKey
          && !event.altKey
          && state.excerptWindow
          && !state.excerptWindow.closed
        ) {
          event.preventDefault();
          state.excerptWindow.location.href = excerpt.href;
          state.excerptWindow.focus();
        }
        return;
      }
      const groupTab = event.target.closest("[data-group-id]");
      if (groupTab) {
        event.preventDefault();
        activateGroup(groupTab.dataset.groupId);
        return;
      }
      const patternTab = event.target.closest("[data-pattern-id]");
      if (patternTab) {
        event.preventDefault();
        activatePattern(patternTab.dataset.patternId);
        return;
      }
      const filter = event.target.closest("[data-colour-filter]");
      if (filter) applyFilter(filter.dataset.colourFilter);
    });
    document.addEventListener("keydown", (event) => {
      const tab = event.target.closest('[role="tab"]');
      if (!tab || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const direction = event.key === "Home" ? "home" : event.key === "End" ? "end" : event.key === "ArrowLeft" ? -1 : 1;
      if (tab.dataset.groupId) moveTab(tab, direction, "[data-group-id]", "groupId", activateGroup);
      else if (tab.dataset.patternId) moveTab(tab, direction, "[data-pattern-id]", "patternId", activatePattern);
    });
    window.addEventListener("hashchange", () => openFromHash({scroll: true}));
  }

  async function main() {
    try {
      const response = await fetch(DATA_URL);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      indexPayload(await response.json());
      initializeFamilies();
      bindEvents();
      openFromHash({scroll: true});
    } catch (error) {
      document.querySelectorAll("[data-group-panel]").forEach((panel) => {
        panel.replaceChildren(textElement("p", "noscript-note", `Catalog data could not be loaded: ${error.message}`));
      });
    }
  }

  main();
})();

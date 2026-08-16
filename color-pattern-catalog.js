(() => {
  "use strict";

  const DATA_URL = "data/color-pattern-catalog.json?v=p6m-spacing-v1";
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
    renderActionsByGroup: new Map(),
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
    link.href = `book-excerpt.html?v=one-colour-source-v1&${parameters.toString()}`;
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
        while (index < signature.length) {
          if (SUPERSCRIPT_DIGITS[signature[index]]) {
            digits += SUPERSCRIPT_DIGITS[signature[index]];
            index += 1;
            continue;
          }
          if (
            signature[index] === ","
            && SUPERSCRIPT_DIGITS[signature[index + 1]]
          ) {
            digits += ",";
            index += 1;
            continue;
          }
          break;
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

  function gsGroupSymbolElement(pattern, group) {
    if (group.number_of_colours === 1) {
      return mathSymbolElement(group.gs_symbol);
    }
    return sourceSymbolLink(
      pattern.book_excerpt,
      pattern.id,
      mathSymbolElement(group.gs_symbol),
      `Open Grünbaum–Shephard source crop for group symbol ${group.gs_symbol}`,
    );
  }

  function gsPatternTypeElement(pattern) {
    if (pattern.book_excerpt.direct_source) {
      return sourceSymbolLink(
        pattern.book_excerpt,
        pattern.id,
        mathSymbolElement(pattern.gs_pattern_type),
        `Open Grünbaum–Shephard source crop for pattern type ${pattern.gs_pattern_type}`,
      );
    }
    const wrapper = document.createElement("span");
    wrapper.className = "indirect-source-value";
    wrapper.append(
      mathSymbolElement(pattern.gs_pattern_type),
      document.createTextNode(
        ` · ${pattern.underlying_pattern_is_primitive ? "primitive" : "nonprimitive"}`,
      ),
    );
    wrapper.title = (
      `${pattern.underlying_pattern_is_primitive
        ? "Primitive: the wallpaper group is the only motif-transitive subgroup."
        : "Nonprimitive: symmetry-related motif copies have merged into a motif with its own stabilizer."} `
      + `The supplied excerpt has no Chapter 5 plate for ${pattern.gs_pattern_type}; `
      + `its Chapter 8 cross-reference is ${pattern.book_excerpt.source_symbol}.`
    );
    return wrapper;
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

  function layoutDiscrepancyElement(pattern) {
    const layout = pattern.render_layout;
    const reference = state.patternById.get(layout.reference_pattern_id);
    const wrapper = document.createElement("span");
    wrapper.className = "layout-discrepancy";
    wrapper.append(document.createTextNode(layout.colour_blind_discrepancy.toFixed(3)));
    if (reference && reference.id !== pattern.id) {
      wrapper.append(
        document.createTextNode(" from "),
        mathSymbolElement(reference.gs_pattern_type),
      );
    }
    if (layout.schematic_constraint) {
      wrapper.append(document.createTextNode(" · approx."));
      wrapper.title = `${state.payload.meta.definitions.layout_discrepancy} ${layout.schematic_constraint}`;
    } else {
      wrapper.title = state.payload.meta.definitions.layout_discrepancy;
    }
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

  function svgElement(tag, attributes = {}) {
    const element = document.createElementNS(SVG_NS, tag);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
    return element;
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

  function multiplyMatrices(left, right) {
    return [
      [
        left[0][0] * right[0][0] + left[0][1] * right[1][0],
        left[0][0] * right[0][1] + left[0][1] * right[1][1],
      ],
      [
        left[1][0] * right[0][0] + left[1][1] * right[1][0],
        left[1][0] * right[0][1] + left[1][1] * right[1][1],
      ],
    ];
  }

  function applyMatrix(matrix, vector) {
    return [
      matrix[0][0] * vector[0] + matrix[0][1] * vector[1],
      matrix[1][0] * vector[0] + matrix[1][1] * vector[1],
    ];
  }

  function composeAffine(left, right) {
    const shifted = applyMatrix(left.matrix, right.translation);
    return {
      matrix: multiplyMatrices(left.matrix, right.matrix),
      translation: [shifted[0] + left.translation[0], shifted[1] + left.translation[1]],
    };
  }

  function inverseAffine(operation) {
    const matrix = operation.matrix;
    const determinant = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0];
    const inverseMatrix = [
      [matrix[1][1] / determinant, -matrix[0][1] / determinant],
      [-matrix[1][0] / determinant, matrix[0][0] / determinant],
    ];
    const shifted = applyMatrix(inverseMatrix, operation.translation);
    return {matrix: inverseMatrix, translation: [-shifted[0], -shifted[1]]};
  }

  function composePermutations(left, right) {
    return right.map((image) => left[image]);
  }

  function inversePermutation(permutation) {
    const inverse = new Array(permutation.length);
    permutation.forEach((image, index) => { inverse[image] = index; });
    return inverse;
  }

  function affineKey(operation) {
    return [...operation.matrix[0], ...operation.matrix[1], ...operation.translation]
      .map((value) => Math.round(value * 1000000))
      .join(":");
  }

  function samePermutation(left, right) {
    return left.length === right.length && left.every((value, index) => value === right[index]);
  }

  function enumerateGroupActions(group, wallpaper) {
    if (state.renderActionsByGroup.has(group.id)) return state.renderActionsByGroup.get(group.id);
    const actionByName = new Map(
      group.generator_colour_actions.map((action) => [action.generator, action]),
    );
    const steps = [];
    wallpaper.render_geometry.generators.forEach((geometry) => {
      const colourAction = actionByName.get(geometry.generator);
      if (!colourAction) throw new Error(`Missing colour action for ${group.id}:${geometry.generator}`);
      const forward = {
        matrix: geometry.matrix,
        translation: geometry.translation,
        permutation: colourAction.colour_permutation,
      };
      const backwardAffine = inverseAffine(forward);
      steps.push(forward, {
        ...backwardAffine,
        permutation: inversePermutation(forward.permutation),
      });
    });

    const identity = {
      matrix: [[1, 0], [0, 1]],
      translation: [0, 0],
      permutation: Array.from({length: group.number_of_colours}, (_value, index) => index),
    };
    const byAffine = new Map([[affineKey(identity), identity]]);
    const queue = [identity];
    const translationBound = 6.5;
    for (let cursor = 0; cursor < queue.length; cursor += 1) {
      const current = queue[cursor];
      steps.forEach((step) => {
        const affine = composeAffine(step, current);
        if (Math.max(...affine.translation.map(Math.abs)) > translationBound) return;
        const next = {
          ...affine,
          permutation: composePermutations(step.permutation, current.permutation),
        };
        const key = affineKey(next);
        const existing = byAffine.get(key);
        if (existing) {
          if (!samePermutation(existing.permutation, next.permutation)) {
            throw new Error(`Inconsistent colour homomorphism for ${group.id}`);
          }
          return;
        }
        byAffine.set(key, next);
        queue.push(next);
        if (queue.length > 16000) throw new Error(`Affine closure exceeded limit for ${group.id}`);
      });
    }
    state.renderActionsByGroup.set(group.id, queue);
    return queue;
  }

  function patternTemplateSeeds(pattern, group) {
    return pattern.render_layout.seeds.map((seed) => ({
      point: seed.point,
      angle: seed.angle,
      colour: seed.colour % group.number_of_colours,
    }));
  }

  function addFixedVerticalBands(svg, pattern, colours) {
    const layout = pattern.render_layout;
    const [originX, originY] = layout.origin;
    const [spacingX, spacingY] = layout.spacing;
    const [offsetX, offsetY] = layout.pair_offset;
    const motifs = svgElement("g");
    for (let row = 0; row < layout.rows; row += 1) {
      for (let column = 0; column < layout.columns; column += 1) {
        const colour = colours[column % colours.length];
        const offsets = layout.motifs_per_band === 2
          ? [[-offsetX, -offsetY, 0], [offsetX, offsetY, 180]]
          : [[0, 0, 0]];
        offsets.forEach(([dx, dy, angle]) => addMotif(
          motifs,
          originX + column * spacingX + dx,
          originY + row * spacingY + dy,
          angle,
          colour,
          false,
        ));
      }
    }
    svg.append(motifs);
  }

  function motifPose(operation, seed, scale) {
    const worldPoint = applyMatrix(operation.matrix, seed.point);
    worldPoint[0] += operation.translation[0];
    worldPoint[1] += operation.translation[1];
    const radians = seed.angle * Math.PI / 180;
    const worldDirection = applyMatrix(operation.matrix, [Math.cos(radians), Math.sin(radians)]);
    const screenDirection = [worldDirection[0], -worldDirection[1]];
    const determinant = operation.matrix[0][0] * operation.matrix[1][1]
      - operation.matrix[0][1] * operation.matrix[1][0];
    const mirrored = determinant < 0;
    let angle = Math.atan2(screenDirection[1], screenDirection[0]) * 180 / Math.PI;
    if (mirrored) angle += 180;
    return {
      x: 480 + scale * worldPoint[0],
      y: 280 - scale * worldPoint[1],
      angle,
      mirrored,
    };
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

    const colours = PALETTES[pattern.number_of_colours];
    if (pattern.render_layout.kind === "fixed_vertical_bands") {
      addFixedVerticalBands(svg, pattern, colours);
      return svg;
    }
    const operations = enumerateGroupActions(group, wallpaper);
    const seeds = patternTemplateSeeds(pattern, group);
    const scale = wallpaper.render_geometry.scale;
    const motifs = svgElement("g");
    const rendered = new Map();
    seeds.forEach((seed, seedIndex) => {
      operations.forEach((operation) => {
        const pose = motifPose(operation, seed, scale);
        if (pose.x < -30 || pose.x > 990 || pose.y < -30 || pose.y > 590) return;
        const colourIndex = operation.permutation[seed.colour];
        const key = [pose.x, pose.y, pose.angle, pose.mirrored ? 1 : 0, colourIndex, seedIndex]
          .map((value) => typeof value === "number" ? Math.round(value * 1000) : value)
          .join(":");
        rendered.set(key, {...pose, colourIndex});
      });
    });
    const ordered = [...rendered.values()].sort((left, right) => (
      left.y - right.y || left.x - right.x || left.angle - right.angle || left.colourIndex - right.colourIndex
    ));
    ordered.forEach((pose) => {
      addMotif(motifs, pose.x, pose.y, pose.angle, colours[pose.colourIndex], pose.mirrored);
    });
    svg.append(motifs);
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
    appendTableRow(table, "Chaim G/H/K", ghkElement(group));
    appendTableRow(table, "G&S group symbol", gsGroupSymbolElement(pattern, group));
    appendTableRow(table, "G&S pattern type", gsPatternTypeElement(pattern));
    appendTableRow(table, "Colour-blind Δ", layoutDiscrepancyElement(pattern));
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
      const first = groups[0];
      if (first) activateGroup(first.id, {updateHash: false});
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

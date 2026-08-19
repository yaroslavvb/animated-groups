(() => {
  "use strict";

  const DATA_URL = "data/color-pattern-catalog.json?v=pm-subgroups-v1";
  window.COLOR_PATTERN_CATALOG_SETTINGS = Object.freeze({
    enableGsPatternSelection: false,
    ...(window.COLOR_PATTERN_CATALOG_SETTINGS || {}),
  });
  const SETTINGS = window.COLOR_PATTERN_CATALOG_SETTINGS;
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
    const labels = ["A", "B", "C"].slice(0, group.number_of_colours);
    palette.setAttribute(
      "aria-label",
      `Permutation cycles over canonical colour labels ${labels.join(", ")}`,
    );
    palette.append(document.createTextNode("cycles over"));
    labels.forEach((label, index) => {
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

  function groupExplanationElement(group) {
    const explanation = group.group_explanation;
    if (!explanation) return null;

    const section = document.createElement("section");
    section.className = "group-explanation";
    const titleId = `${group.id}-subgroups-title`;
    section.setAttribute("aria-labelledby", titleId);

    const title = textElement("h4", "", "Subgroups of ∗∗");
    title.id = titleId;
    const decoder = textElement(
      "p",
      "subgroup-decoder",
      "α translates along the mirrors; P and Q are adjacent parallel mirrors; QP translates across them. H fixes A; K fixes every colour.",
    );
    const subgroups = textElement(
      "p",
      "subgroup-formula",
      typesetSymbol(explanation.subgroups),
    );
    const prose = textElement("p", "subgroup-prose", typesetSymbol(explanation.explanation));
    section.append(title, decoder, subgroups, prose);
    return section;
  }

  function svgElement(tag, attributes = {}) {
    const element = document.createElementNS(SVG_NS, tag);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
    return element;
  }

  function addMotif(svg, x, y, angle, colour, mirrored) {
    const group = svgElement("g", {
      class: "pattern-motif",
      "data-motif-x": x.toFixed(2),
      "data-motif-y": y.toFixed(2),
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
        const offsets = layout.motifs_per_band === 2
          ? [[-offsetX, -offsetY, 0], [offsetX, offsetY, 180]]
          : [[0, 0, 0]];
        offsets.forEach(([dx, dy, angle], motifIndex) => addMotif(
          motifs,
          originX + column * spacingX + dx,
          originY + row * spacingY + dy,
          angle,
          colours[
            layout.colour_rule === "within_pair"
              ? motifIndex % colours.length
              : column % colours.length
          ],
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

  function worldToScreen(point, scale) {
    return [480 + scale * point[0], 280 - scale * point[1]];
  }

  function clippedAxis(axisPoint, axisDirection, scale) {
    const point = worldToScreen(axisPoint, scale);
    const direction = [axisDirection[0], -axisDirection[1]];
    const length = Math.hypot(...direction);
    const unit = [direction[0] / length, direction[1] / length];
    const bounds = [[10, 950], [10, 550]];
    let lower = -Infinity;
    let upper = Infinity;
    for (let dimension = 0; dimension < 2; dimension += 1) {
      if (Math.abs(unit[dimension]) < 1e-9) {
        if (point[dimension] < bounds[dimension][0] || point[dimension] > bounds[dimension][1]) {
          return null;
        }
        continue;
      }
      const first = (bounds[dimension][0] - point[dimension]) / unit[dimension];
      const second = (bounds[dimension][1] - point[dimension]) / unit[dimension];
      lower = Math.max(lower, Math.min(first, second));
      upper = Math.min(upper, Math.max(first, second));
    }
    if (lower > upper) return null;
    return {
      start: [point[0] + lower * unit[0], point[1] + lower * unit[1]],
      end: [point[0] + upper * unit[0], point[1] + upper * unit[1]],
      direction: unit,
      normal: [-unit[1], unit[0]],
    };
  }

  function overlayLine(container, axis, offset, className) {
    const shift = [axis.normal[0] * offset, axis.normal[1] * offset];
    container.append(svgElement("line", {
      x1: axis.start[0] + shift[0],
      y1: axis.start[1] + shift[1],
      x2: axis.end[0] + shift[0],
      y2: axis.end[1] + shift[1],
      class: className,
    }));
  }

  function labelPlacementContext(svg) {
    return {
      motifs: [...svg.querySelectorAll(".pattern-motif")].map((motif) => ({
        x: Number(motif.getAttribute("data-motif-x")),
        y: Number(motif.getAttribute("data-motif-y")),
      })),
      labels: [],
    };
  }

  function labelBox(candidate) {
    return {
      left: candidate[0] - 12,
      right: candidate[0] + 12,
      top: candidate[1] - 12,
      bottom: candidate[1] + 12,
    };
  }

  function boxesIntersect(first, second) {
    return first.left < second.right && first.right > second.left
      && first.top < second.bottom && first.bottom > second.top;
  }

  function motifIntersectsLabel(motif, box) {
    const closestX = Math.max(box.left, Math.min(box.right, motif.x));
    const closestY = Math.max(box.top, Math.min(box.bottom, motif.y));
    return Math.hypot(motif.x - closestX, motif.y - closestY) < 22;
  }

  function chooseLabelPosition(candidates, context) {
    const unique = new Map();
    candidates.forEach(([x, y], index) => {
      const candidate = [Math.max(14, Math.min(946, x)), Math.max(14, Math.min(546, y))];
      const key = candidate.map((value) => value.toFixed(2)).join(":");
      if (!unique.has(key)) unique.set(key, {candidate, index});
    });
    let best = null;
    unique.forEach(({candidate, index}) => {
      const box = labelBox(candidate);
      const motifHits = context.motifs.filter((motif) => motifIntersectsLabel(motif, box)).length;
      const labelHits = context.labels.filter((placed) => boxesIntersect(box, placed)).length;
      const score = motifHits * 1_000_000 + labelHits * 2_000_000 + index;
      if (!best || score < best.score) best = {candidate, box, score};
    });
    context.labels.push(best.box);
    return best;
  }

  function addOverlayLabel(container, label, candidates, context, anchor) {
    const expandedCandidates = [...candidates];
    for (let x = 20; x <= 940; x += 20) expandedCandidates.push([x, 20], [x, 540]);
    for (let y = 40; y <= 520; y += 20) expandedCandidates.push([20, y], [940, y]);
    for (let y = 19; y <= 539; y += 10) {
      for (let x = 24; x <= 934; x += 10) expandedCandidates.push([x, y]);
    }
    const placement = chooseLabelPosition(expandedCandidates, context);
    const [clampedX, clampedY] = placement.candidate;
    if (anchor && Math.hypot(clampedX - anchor[0], clampedY - anchor[1]) > 74) {
      container.append(svgElement("line", {
        x1: anchor[0],
        y1: anchor[1],
        x2: clampedX,
        y2: clampedY,
        class: "generator-label-leader",
      }));
    }
    container.append(svgElement("rect", {
      x: clampedX - 12,
      y: clampedY - 12,
      width: 24,
      height: 24,
      rx: 5,
      class: "generator-label-backing",
    }));
    const text = svgElement("text", {
      x: clampedX,
      y: clampedY,
      class: "generator-label",
      "text-anchor": "middle",
      "dominant-baseline": "middle",
    });
    text.textContent = label;
    container.append(text);
  }

  function addAxisGenerator(overlay, geometry, action, scale, index, labelContext) {
    const visualization = geometry.visualization;
    const axis = clippedAxis(
      visualization.axis_point,
      visualization.axis_direction,
      scale,
    );
    if (!axis) return;
    const marker = svgElement("g", {
      class: `generator-marker generator-${visualization.kind}`,
      "data-generator": geometry.generator,
      "data-generator-kind": visualization.kind,
    });
    const title = svgElement("title");
    title.textContent = `${geometry.generator} — ${action.geometry}`;
    marker.append(title);

    if (visualization.kind === "mirror") {
      overlayLine(marker, axis, 0, "generator-axis-halo generator-mirror-halo");
      overlayLine(marker, axis, 0, "generator-mirror-line");
    } else {
      for (const offset of [-3.4, 3.4]) {
        overlayLine(marker, axis, offset, "generator-axis-halo");
        overlayLine(marker, axis, offset, "generator-glide-line");
      }
    }

    const preferredFraction = index % 2 === 0
      ? 0.14 + (index % 3) * 0.055
      : 0.86 - (index % 3) * 0.055;
    const fractions = [preferredFraction];
    for (let fraction = 0.025; fraction < 1; fraction += 0.025) fractions.push(fraction);
    const candidates = [];
    const offsets = [13, -13, 0];
    for (let offset = 21; offset <= 133; offset += 8) offsets.push(offset, -offset);
    offsets.forEach((normalOffset) => {
      fractions.forEach((fraction) => candidates.push([
        axis.start[0] + (axis.end[0] - axis.start[0]) * fraction + axis.normal[0] * normalOffset,
        axis.start[1] + (axis.end[1] - axis.start[1]) * fraction + axis.normal[1] * normalOffset,
      ]));
    });
    const anchor = [
      axis.start[0] + (axis.end[0] - axis.start[0]) * preferredFraction,
      axis.start[1] + (axis.end[1] - axis.start[1]) * preferredFraction,
    ];
    addOverlayLabel(marker, geometry.generator, candidates, labelContext, anchor);
    overlay.append(marker);
  }

  function rotationArcGeometry(cx, cy, radius, angleDegrees) {
    const startAngle = -72;
    const delta = -angleDegrees;
    const endAngle = startAngle + delta;
    const radians = (value) => value * Math.PI / 180;
    const start = [
      cx + radius * Math.cos(radians(startAngle)),
      cy + radius * Math.sin(radians(startAngle)),
    ];
    const tip = [
      cx + radius * Math.cos(radians(endAngle)),
      cy + radius * Math.sin(radians(endAngle)),
    ];
    const sweep = delta > 0 ? 1 : 0;
    const path = `M ${start[0].toFixed(2)} ${start[1].toFixed(2)} A ${radius} ${radius} 0 ${Math.abs(delta) > 180 ? 1 : 0} ${sweep} ${tip[0].toFixed(2)} ${tip[1].toFixed(2)}`;
    const directionSign = Math.sign(delta) || 1;
    const tangent = [
      directionSign * -Math.sin(radians(endAngle)),
      directionSign * Math.cos(radians(endAngle)),
    ];
    const base = [tip[0] - tangent[0] * 7.5, tip[1] - tangent[1] * 7.5];
    const normal = [-tangent[1], tangent[0]];
    const arrow = [
      tip,
      [base[0] + normal[0] * 3.7, base[1] + normal[1] * 3.7],
      [base[0] - normal[0] * 3.7, base[1] - normal[1] * 3.7],
    ];
    return {path, arrow};
  }

  function addRotationGenerator(overlay, geometry, action, scale, labelContext) {
    const visualization = geometry.visualization;
    const [cx, cy] = worldToScreen(visualization.centre, scale);
    const radius = 18;
    const arc = rotationArcGeometry(cx, cy, radius, visualization.angle_degrees);
    const marker = svgElement("g", {
      class: "generator-marker generator-rotation",
      "data-generator": geometry.generator,
      "data-generator-kind": "rotation",
    });
    const title = svgElement("title");
    title.textContent = `${geometry.generator} — ${action.geometry}`;
    marker.append(
      title,
      svgElement("path", {d: arc.path, class: "generator-rotation-halo"}),
      svgElement("path", {d: arc.path, class: "generator-rotation-arc"}),
      svgElement("polygon", {
        points: arc.arrow.map((point) => point.map((value) => value.toFixed(2)).join(",")).join(" "),
        class: "generator-rotation-arrow",
      }),
      svgElement("circle", {cx, cy, r: 4.7, class: "generator-rotation-centre"}),
    );
    const candidates = [[cx + radius + 10, cy - radius - 5]];
    for (let labelRadius = 30; labelRadius <= 150; labelRadius += 8) {
      for (let step = 0; step < 32; step += 1) {
        const angle = (step * Math.PI) / 16;
        candidates.push([
          cx + Math.cos(angle) * labelRadius,
          cy + Math.sin(angle) * labelRadius,
        ]);
      }
    }
    addOverlayLabel(marker, geometry.generator, candidates, labelContext, [cx, cy]);
    overlay.append(marker);
  }

  function addGeneratorOverlay(svg, group, wallpaper) {
    const actionByName = new Map(
      group.generator_colour_actions.map((action) => [action.generator, action]),
    );
    const overlay = svgElement("g", {
      class: "generator-overlay",
      "aria-hidden": "true",
    });
    const labelContext = labelPlacementContext(svg);
    wallpaper.render_geometry.generators.forEach((geometry, index) => {
      const action = actionByName.get(geometry.generator);
      if (!action) throw new Error(`Missing Presentation row for ${group.id}:${geometry.generator}`);
      const kind = geometry.visualization.kind;
      if (kind === "translation") return;
      if (kind === "rotation") {
        addRotationGenerator(overlay, geometry, action, wallpaper.render_geometry.scale, labelContext);
      } else {
        addAxisGenerator(overlay, geometry, action, wallpaper.render_geometry.scale, index, labelContext);
      }
    });
    svg.append(overlay);
  }

  function buildPatternSvg(pattern, group, wallpaper) {
    const visibleGenerators = wallpaper.render_geometry.generators.filter(
      (geometry) => geometry.visualization.kind !== "translation",
    );
    const actionByName = new Map(
      group.generator_colour_actions.map((action) => [action.generator, action]),
    );
    const titleId = `${pattern.id}-graphic-title`;
    const descriptionId = `${pattern.id}-graphic-description`;
    const svg = svgElement("svg", {
      viewBox: "0 0 960 560",
      role: "img",
      "aria-labelledby": `${titleId} ${descriptionId}`,
      preserveAspectRatio: "xMidYMid meet",
    });
    const title = svgElement("title", {id: titleId});
    title.textContent = `${pattern.gs_pattern_type} with geometric generators`;
    const description = svgElement("desc", {id: descriptionId});
    description.textContent = visibleGenerators.length
      ? `Generator overlay: ${visibleGenerators.map((geometry) => (
        `${geometry.generator}: ${actionByName.get(geometry.generator).geometry}`
      )).join("; ")}. Translation generators are omitted.`
      : "Translation generators are omitted; no generator markers are shown.";
    const background = svgElement("rect", {x: 0, y: 0, width: 960, height: 560, fill: "#fffefa"});
    svg.append(title, description, background);

    const colours = PALETTES[pattern.number_of_colours];
    if (pattern.render_layout.kind === "fixed_vertical_bands") {
      addFixedVerticalBands(svg, pattern, colours);
      addGeneratorOverlay(svg, group, wallpaper);
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
    addGeneratorOverlay(svg, group, wallpaper);
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
    details.append(presentationElement(group));
    const explanation = groupExplanationElement(group);
    if (explanation) details.append(explanation);
    details.append(table);
    pane.append(figure, details);
    return pane;
  }

  function buildGroupPanel(group) {
    const wallpaper = state.wallpaperById.get(group.wallpaper_id);
    const patterns = state.patternsByGroup.get(group.id) || [];
    const panel = document.createDocumentFragment();

    // Mark the pattern this group is actually showing, not always the first:
    // a group revisited after its pattern was changed still renders that
    // pattern, so keying the tab state off the index desynchronizes the
    // highlight, the tab order, and aria-selected from the visible pane.
    const selectedPatternId = state.activePatternByGroup.get(group.id);
    const selectedPattern = SETTINGS.enableGsPatternSelection
      ? state.patternById.get(selectedPatternId) || patterns[0]
      : patterns[0];

    const selector = document.createElement("div");
    selector.className = "pattern-selector";
    const tabs = document.createElement("nav");
    tabs.className = "pattern-tabs";
    tabs.setAttribute("role", "tablist");
    tabs.setAttribute("aria-label", `Pattern types in ${typesetSymbol(group.chaim_notation)}`);
    patterns.forEach((pattern, index) => {
      const enabled = SETTINGS.enableGsPatternSelection || index === 0;
      const active = selectedPattern ? pattern.id === selectedPattern.id : false;
      const tab = document.createElement("a");
      tab.className = "pattern-tab";
      tab.id = `tab-${pattern.id}`;
      tab.dataset.patternId = pattern.id;
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-selected", String(active && enabled));
      tab.tabIndex = active && enabled ? 0 : -1;
      if (enabled) {
        tab.href = `#${pattern.id}`;
        tab.setAttribute("aria-controls", `panel-${pattern.id}`);
      } else {
        tab.classList.add("is-disabled");
        tab.setAttribute("aria-disabled", "true");
        tab.setAttribute("aria-label", `${pattern.gs_pattern_type}; temporarily unavailable while G&S pattern notation is under review`);
        tab.title = "Temporarily unavailable while G&S pattern notation is under review";
      }
      tab.textContent = typesetSymbol(pattern.gs_pattern_type);
      tabs.append(tab);
    });
    selector.append(tabs);

    const body = document.createElement("div");
    body.dataset.patternPanelHost = "";
    if (selectedPattern) body.append(buildPatternPane(selectedPattern, group, wallpaper));
    panel.append(selector, body);
    return panel;
  }

  function activatePattern(patternId, {updateHash = true, focus = false} = {}) {
    const pattern = state.patternById.get(patternId);
    if (!pattern) return false;
    const group = state.groupById.get(pattern.colour_group_id);
    const patterns = state.patternsByGroup.get(pattern.colour_group_id) || [];
    if (!SETTINGS.enableGsPatternSelection && patterns[0]?.id !== pattern.id) return false;
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
    if (!SETTINGS.enableGsPatternSelection && patterns.length) {
      state.activePatternByGroup.set(group.id, patterns[0].id);
    } else if (!state.activePatternByGroup.has(group.id) && patterns.length) {
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
      const patterns = state.patternsByGroup.get(pattern.colour_group_id) || [];
      const availablePattern = SETTINGS.enableGsPatternSelection ? pattern : patterns[0];
      if (!availablePattern) return false;
      activatePattern(availablePattern.id, {updateHash: false});
      if (availablePattern.id !== id) {
        history.replaceState(null, "", `#${availablePattern.id}`);
      }
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
    const tabs = [...container.querySelectorAll(selector)].filter((tab) => (
      !tab.hidden && tab.getAttribute("aria-disabled") !== "true"
    ));
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
    // Tabs are real anchors, so a modified click must keep its native
    // meaning (open in a new tab or window) instead of being swallowed.
    const isPlainClick = (event) => (
      !event.defaultPrevented
      && event.button === 0
      && !event.metaKey
      && !event.ctrlKey
      && !event.shiftKey
      && !event.altKey
    );
    document.addEventListener("click", (event) => {
      const excerpt = event.target.closest(".book-evidence-link");
      if (excerpt) {
        if (isPlainClick(event) && state.excerptWindow && !state.excerptWindow.closed) {
          event.preventDefault();
          state.excerptWindow.location.href = excerpt.href;
          state.excerptWindow.focus();
        }
        return;
      }
      if (!isPlainClick(event)) return;
      const groupTab = event.target.closest("[data-group-id]");
      if (groupTab) {
        event.preventDefault();
        activateGroup(groupTab.dataset.groupId);
        return;
      }
      const patternTab = event.target.closest("[data-pattern-id]");
      if (patternTab) {
        event.preventDefault();
        if (patternTab.getAttribute("aria-disabled") === "true") return;
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

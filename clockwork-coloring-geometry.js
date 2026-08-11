/* Pure geometry for the correspondence films.
 *
 * Kept separate from the DOM controller so the exact production sizing logic
 * can be checked over every catalog record in Node as well as in the browser.
 */

"use strict";

const CELLS = 4;
const MAX_COLUMNS = 18;

export const RING_MID = 0.76;
export const RING_W = 0.12;
// The supplied reference measured 74 bitmap pixels at Retina 2×, or 37 CSS
// pixels across the outside of the pale ring. Keep a one-pixel safety margin.
export const MIN_PHASE_CIRCLE_DIAMETER_PX = 38;

const RING_OUTER_DIAMETER_FACTOR = 2 * (RING_MID + RING_W / 2);
const MIN_MOTIF_RADIUS_PX = MIN_PHASE_CIRCLE_DIAMETER_PX / RING_OUTER_DIAMETER_FACTOR;

export function frac(value) {
  return ((value % 1) + 1) % 1;
}

export function phaseCircleOuterDiameter(radius) {
  return RING_OUTER_DIAMETER_FACTOR * radius;
}

function multiply2(left, right) {
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

function invert2(matrix) {
  const determinant = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0];
  if (Math.abs(determinant) < 1e-10) {
    throw new Error("singular wallpaper basis");
  }
  return [
    [matrix[1][1] / determinant, -matrix[0][1] / determinant],
    [-matrix[1][0] / determinant, matrix[0][0] / determinant],
  ];
}

function latticeToPixel(matrix, b1, b2) {
  const basis = [[b1[0], b2[0]], [b1[1], b2[1]]];
  return multiply2(multiply2(basis, matrix), invert2(basis));
}

export function buildClockworkGeometry(spec, width, height, dpr = 1) {
  if (!spec || !Array.isArray(spec.ops) || !Array.isArray(spec.basis)) {
    throw new Error("invalid clockwork render specification");
  }
  const safeWidth = Math.max(1, Number(width));
  const safeHeight = Math.max(1, Number(height));
  const basis = spec.basis;
  const shortSide = Math.min(safeWidth, safeHeight);
  const horizontalExtent = Math.max(Math.abs(basis[0][0]), Math.abs(basis[1][0])) || 1;
  const verticalExtent = Math.max(Math.abs(basis[0][1]), Math.abs(basis[1][1])) || 1;
  const limitingExtent = shortSide === safeHeight ? verticalExtent : horizontalExtent;
  const cellFor = (count) => Math.max(shortSide / (count * limitingExtent), 24);
  const uniqueSites = new Set(spec.ops.map((operation) => (
    `${operation.M.flat().join(",")}|${operation.v.map((value) => Math.round(frac(value) * 1e6)).join(",")}`
  ))).size;
  const basisDeterminant = Math.abs(
    basis[0][0] * basis[1][1] - basis[0][1] * basis[1][0],
  ) || 1;

  const measure = (cell) => {
    const b1 = [basis[0][0] * cell, -basis[0][1] * cell];
    const b2 = [basis[1][0] * cell, -basis[1][1] * cell];
    const sites = [];
    const base = spec.base || [0.31, 0.17];
    for (const operation of spec.ops) {
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
      for (const shiftX of [0, 1]) {
        for (const shiftY of [0, 1]) sites.push([x + shiftX, y + shiftY]);
      }
    }
    let minimumDistance = Math.min(Math.hypot(...b1), Math.hypot(...b2));
    for (let left = 0; left < sites.length; left += 1) {
      for (let right = left + 1; right < sites.length; right += 1) {
        const deltaX = (sites[left][0] - sites[right][0]) * b1[0]
          + (sites[left][1] - sites[right][1]) * b2[0];
        const deltaY = (sites[left][0] - sites[right][0]) * b1[1]
          + (sites[left][1] - sites[right][1]) * b2[1];
        const distance = Math.hypot(deltaX, deltaY);
        if (distance > 1e-6 && distance < minimumDistance) minimumDistance = distance;
      }
    }
    return {
      b1,
      b2,
      motifRadius: Math.min(
        0.40 * Math.min(Math.hypot(...b1), Math.hypot(...b2)),
        0.52 * minimumDistance,
      ),
    };
  };

  let cell = cellFor(CELLS);
  let measured = measure(cell);
  if (measured.motifRadius > 0 && measured.motifRadius < MIN_MOTIF_RADIUS_PX) {
    // Distances are homogeneous in cell. Enlarge the cell without a repeat-count
    // cap: showing fewer repeats is preferable to shrinking below the reference.
    cell *= (MIN_MOTIF_RADIUS_PX + 1e-6) / measured.motifRadius;
    measured = measure(cell);
  }
  const columns = safeWidth / Math.sqrt(basisDeterminant * cell * cell / uniqueSites);
  if (columns > MAX_COLUMNS) {
    cell *= columns / MAX_COLUMNS;
    measured = measure(cell);
  }

  const { b1, b2, motifRadius } = measured;
  const circleDiameter = phaseCircleOuterDiameter(motifRadius);
  if (circleDiameter + 1e-6 < MIN_PHASE_CIRCLE_DIAMETER_PX) {
    throw new Error(`phase circle ${circleDiameter.toFixed(3)}px is below the minimum`);
  }

  const inverse = invert2([[b1[0], b2[0]], [b1[1], b2[1]]]);
  const centerX = safeWidth / 2;
  const centerY = safeHeight / 2;
  let min1 = Infinity;
  let max1 = -Infinity;
  let min2 = Infinity;
  let max2 = -Infinity;
  for (const [pixelX, pixelY] of [[0, 0], [safeWidth, 0], [0, safeHeight], [safeWidth, safeHeight]]) {
    const x = pixelX - centerX;
    const y = pixelY - centerY;
    const lattice1 = inverse[0][0] * x + inverse[0][1] * y;
    const lattice2 = inverse[1][0] * x + inverse[1][1] * y;
    min1 = Math.min(min1, lattice1);
    max1 = Math.max(max1, lattice1);
    min2 = Math.min(min2, lattice2);
    max2 = Math.max(max2, lattice2);
  }

  const placements = [];
  const base = spec.base || [0.31, 0.17];
  const pad = 1.6;
  for (const operation of spec.ops) {
    const baseX = operation.M[0][0] * base[0]
      + operation.M[0][1] * base[1]
      + operation.v[0];
    const baseY = operation.M[1][0] * base[0]
      + operation.M[1][1] * base[1]
      + operation.v[1];
    const transform = latticeToPixel(operation.M, b1, b2);
    for (let lattice1 = Math.floor(min1 - pad); lattice1 <= Math.ceil(max1 + pad); lattice1 += 1) {
      for (let lattice2 = Math.floor(min2 - pad); lattice2 <= Math.ceil(max2 + pad); lattice2 += 1) {
        const position1 = baseX + lattice1;
        const position2 = baseY + lattice2;
        const pixelX = position1 * b1[0] + position2 * b2[0];
        const pixelY = position1 * b1[1] + position2 * b2[1];
        if (
          pixelX < -safeWidth / 2 - motifRadius * 3
          || pixelX > safeWidth / 2 + motifRadius * 3
          || pixelY < -safeHeight / 2 - motifRadius * 3
          || pixelY > safeHeight / 2 + motifRadius * 3
        ) continue;
        placements.push({
          pixelX,
          pixelY,
          transform,
          tau: operation.tau,
        });
      }
    }
  }
  return {
    width: safeWidth,
    height: safeHeight,
    dpr,
    motifRadius,
    circleDiameter,
    placements,
  };
}

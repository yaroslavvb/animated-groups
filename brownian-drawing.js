/* Shared glyphs and fixed-point geometry for the Brownian canvas. */
"use strict";

export const GROUND = "#ffffff";
export const PALETTE = [
  "#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9",
];

const EDGE = "#2f3935";
const TWO_PI = Math.PI * 2;

export function drawBall(ctx, x, y, radius, colour) {
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, TWO_PI);
  ctx.fillStyle = colour;
  ctx.fill();
  ctx.lineWidth = Math.max(1, radius * 0.16);
  ctx.strokeStyle = EDGE;
  ctx.stroke();
}

const frac = (x) => ((x % 1) + 1) % 1;

const apply = (matrix, point) => [
  matrix[0][0] * point[0] + matrix[0][1] * point[1],
  matrix[1][0] * point[0] + matrix[1][1] * point[1],
];

function inverse2(matrix) {
  const determinant = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0];
  return [
    [matrix[1][1] / determinant, -matrix[0][1] / determinant],
    [-matrix[1][0] / determinant, matrix[0][0] / determinant],
  ];
}

const pick = (columns) => (
  Math.hypot(columns[0][0], columns[0][1]) > 1e-9 ? columns[0] : columns[1]
);

function solve2(direction, normal, vector) {
  const determinant = direction[0] * normal[1] - direction[1] * normal[0];
  return [
    (vector[0] * normal[1] - vector[1] * normal[0]) / determinant,
    (direction[0] * vector[1] - direction[1] * vector[0]) / determinant,
  ];
}

function rotationOrder(matrix) {
  const trace = matrix[0][0] + matrix[1][1];
  return trace === 1 ? 6 : trace === 0 ? 4 : trace === -1 ? 3 : 2;
}

/* Enumerate rotation centres and mirror/glide axes in lattice coordinates.
 * Lattice translates of every finite operation are required: for example, an
 * order-three rotation has three times as many centres as one translated seed
 * would reveal. */
export function elements(operations, span) {
  const reach = span + 1;
  const seenPoints = new Map();
  const seenLines = new Map();
  const points = [];
  const lines = [];

  for (const operation of operations) {
    const matrix = operation.M;
    const determinant = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0];
    const identity = matrix[0][0] === 1 && matrix[1][1] === 1
      && matrix[0][1] === 0 && matrix[1][0] === 0;
    if (identity) continue;

    const direction = determinant < 0
      ? pick([[matrix[0][0] + 1, matrix[1][0]], [matrix[0][1], matrix[1][1] + 1]])
      : null;
    const normal = determinant < 0
      ? pick([[matrix[0][0] - 1, matrix[1][0]], [matrix[0][1], matrix[1][1] - 1]])
      : null;
    const fixedPoint = determinant > 0
      ? inverse2([[1 - matrix[0][0], -matrix[0][1]], [-matrix[1][0], 1 - matrix[1][1]]])
      : null;
    const order = determinant > 0 ? rotationOrder(matrix) : 0;

    for (let m = -3 * reach; m <= 3 * reach; m++) {
      for (let n = -3 * reach; n <= 3 * reach; n++) {
        const shift = [operation.v[0] + m, operation.v[1] + n];
        if (determinant > 0) {
          const centre = apply(fixedPoint, shift);
          if (Math.abs(centre[0]) > reach + 1 || Math.abs(centre[1]) > reach + 1) continue;
          const key = [Math.round(centre[0] * 60), Math.round(centre[1] * 60)].join();
          const previous = seenPoints.get(key);
          const tau = frac(operation.tau || 0);
          if (previous === undefined) {
            seenPoints.set(key, points.length);
            points.push({ c: centre, free: tau < 1e-9, order, tau });
          } else if (order > points[previous].order) {
            points[previous] = { c: centre, free: tau < 1e-9, order, tau };
          }
        } else {
          const coefficients = solve2(direction, normal, shift);
          const offset = coefficients[1] / 2;
          const base = [normal[0] * offset, normal[1] * offset];
          if (Math.abs(base[0]) > 2 * reach || Math.abs(base[1]) > 2 * reach) continue;
          const key = [
            Math.round(direction[0] * 60), Math.round(direction[1] * 60),
            Math.round(offset * 60),
          ].join();
          const glide = Math.abs(frac(coefficients[0] + 0.5) - 0.5) > 1e-6;
          const previous = seenLines.get(key);
          if (previous === undefined) {
            seenLines.set(key, lines.length);
            lines.push({ base, d: direction, glide });
          } else if (!glide) {
            lines[previous].glide = false;
          }
        }
      }
    }
  }
  return { pts: points, lns: lines };
}

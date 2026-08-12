"use strict";

const DATA_URL = "data/color-forward-census.json";

function renderOrbifoldNotation(element, source) {
  const notation = String(source);
  element.setAttribute("aria-label", notation);
  notation.split("*").forEach((fragment, index) => {
    if (index > 0) {
      const star = document.createElement("span");
      star.className = "orbifold-star";
      star.textContent = "∗";
      element.append(star);
    }
    element.append(fragment);
  });
}

function makeTable(headers, rows, options = {}) {
  const table = document.createElement("table");
  table.className = "census-table";

  if (options.caption) {
    const caption = document.createElement("caption");
    caption.textContent = options.caption;
    table.append(caption);
  }

  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  for (const label of headers) {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = label;
    headerRow.append(th);
  }
  thead.append(headerRow);
  table.append(thead);

  const tbody = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    row.forEach((value, index) => {
      const cell = document.createElement(index === 0 ? "th" : "td");
      if (index === 0) {
        cell.scope = "row";
        if (options.firstColumnClass) cell.className = options.firstColumnClass;
      }
      if (index === 0 && options.firstColumnRenderer) {
        options.firstColumnRenderer(cell, value);
      } else {
        cell.textContent = value;
      }
      tr.append(cell);
    });
    tbody.append(tr);
  }
  table.append(tbody);
  return table;
}

function replaceWithTable(id, table) {
  const host = document.getElementById(id);
  if (host) host.replaceChildren(table);
}

function summaryRow(data, field, label) {
  const values = data.summary.map(row => row[field]);
  return [label, ...values, values.reduce((sum, value) => sum + value, 0)];
}

function renderSummary(data) {
  const result = document.getElementById("result-clock-orders");
  if (result) {
    result.textContent = data.summary
      .map(row => row.forward_catalog_canonical_clock_order)
      .join(", ");
  }

  const headers = [
    "census",
    ...data.summary.map(row => `N=${row.colours}`),
    "Σ through 6",
  ];
  const rows = [
    summaryRow(data, "wieting_all_transitive",
      "all transitive perfect plane colourings"),
    summaryRow(data, "regular_cyclic_kernels",
      "regular cyclic plane colour groups"),
    summaryRow(data, "forward_catalog_canonical_clock_order",
      "forward representatives of exact clock order"),
  ];
  replaceWithTable("census-table", makeTable(headers, rows, {
    caption: "Counts for exact colour or canonical clock order N",
  }));
}

function orbifoldRows(data, field) {
  const rows = data.by_wallpaper.map(row => {
    const counts = data.summary.map(summary =>
      row[field][String(summary.colours)]);
    return [
      row.orbifold,
      ...counts,
      field === "forward_catalog"
        ? row.forward_total
        : counts.reduce((sum, value) => sum + value, 0),
    ];
  });
  const totals = data.summary.map(summary => {
    const n = String(summary.colours);
    return data.by_wallpaper.reduce((sum, row) => sum + row[field][n], 0);
  });
  rows.push(["TOTAL", ...totals, totals.reduce((sum, value) => sum + value, 0)]);
  return rows;
}

function renderOrbifoldTables(data) {
  const headers = [
    "orbifold",
    ...data.summary.map(row => `N=${row.colours}`),
    "Σ",
  ];
  replaceWithTable("cyclic-orbifold-table", makeTable(
    headers,
    orbifoldRows(data, "regular_cyclic"),
    {
      caption: "Regular cyclic plane colour groups by Conway orbifold",
      firstColumnClass: "orbifold-symbol",
      firstColumnRenderer: renderOrbifoldNotation,
    },
  ));
  replaceWithTable("film-orbifold-table", makeTable(
    headers,
    orbifoldRows(data, "forward_catalog"),
    {
      caption: "Forward representatives by spatial orbifold projection and canonical clock order",
      firstColumnClass: "orbifold-symbol",
      firstColumnRenderer: renderOrbifoldNotation,
    },
  ));
}

function renderFingerprint(data) {
  const host = document.getElementById("data-fingerprint");
  if (!host) return;
  const meta = data.meta;
  host.textContent =
    `Generated from ${meta.source_catalog.forward_groups} forward records; ` +
    `source 275-catalog SHA-256 ${meta.source_catalog.sha256}; ` +
    `manifest SHA-256 ${meta.manifest_sha256}.`;
}

function showError(error) {
  console.error(error);
  for (const id of ["census-table", "cyclic-orbifold-table", "film-orbifold-table"]) {
    const host = document.getElementById(id);
    if (!host) continue;
    const p = document.createElement("p");
    p.className = "data-warning";
    p.textContent = "The generated census could not be loaded. Use the CSV links below.";
    host.replaceChildren(p);
  }
}

try {
  const response = await fetch(DATA_URL, { cache: "no-cache" });
  if (!response.ok) throw new Error(`${DATA_URL}: HTTP ${response.status}`);
  const data = await response.json();
  renderSummary(data);
  renderOrbifoldTables(data);
  renderFingerprint(data);
} catch (error) {
  showError(error);
}

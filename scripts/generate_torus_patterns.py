#!/usr/bin/env python3
"""Generate the page of symmetric 0/1 patterns on the 3x3 torus.

The ambient group is A = (Z/3)^2 acting on itself by translation.  Of the
2^9 = 512 binary patterns, 26 have a nontrivial stabilizer.  This page shows
every one of them, grouped first by stabilizer and then by translation orbit,
with the stabilizer and the orbit structure described for each row.

Run with --check to verify the committed page is current.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from html import escape
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "torus-patterns.html"

N = 3
CELLS = [(a, b) for a in range(N) for b in range(N)]
INDEX = {cell: i for i, cell in enumerate(CELLS)}
AMBIENT = CELLS

FILL, EMPTY, EDGE = "#0072B2", "#e9e4d7", "#c8c1b0"


def shifted(t: tuple[int, int], pattern: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(
        pattern[INDEX[((c[0] - t[0]) % N, (c[1] - t[1]) % N)]] for c in CELLS
    )


def stabilizer(pattern: tuple[int, ...]) -> frozenset[tuple[int, int]]:
    return frozenset(t for t in AMBIENT if shifted(t, pattern) == pattern)


def orbit(pattern: tuple[int, ...]) -> frozenset[tuple[int, ...]]:
    return frozenset(shifted(t, pattern) for t in AMBIENT)


def span(generators: tuple[tuple[int, int], ...]) -> frozenset[tuple[int, int]]:
    seen, frontier = {(0, 0)}, [(0, 0)]
    while frontier:
        x = frontier.pop()
        for g in generators:
            y = ((x[0] + g[0]) % N, (x[1] + g[1]) % N)
            if y not in seen:
                seen.add(y)
                frontier.append(y)
    return frozenset(seen)


ROWS = (
    {
        "subgroup": span(((1, 0), (0, 1))),
        "title": "K = A",
        "generators": "X, Y",
        "blurb": "Every translation fixes the pattern, so the pattern is constant.",
        "invariant": "nothing is distinguished",
        "cosets": "one coset — the whole torus",
    },
    {
        "subgroup": span(((0, 1),)),
        "title": "K = ⟨Y⟩ — rows",
        "generators": "Y = (0,1), the column shift",
        "blurb": "Sliding along a row changes nothing, so each row is uniform.",
        "invariant": "a mod 3 — the row index",
        "cosets": "three cosets — the three rows",
    },
    {
        "subgroup": span(((1, 0),)),
        "title": "K = ⟨X⟩ — columns",
        "generators": "X = (1,0), the row shift",
        "blurb": "Sliding down a column changes nothing, so each column is uniform.",
        "invariant": "b mod 3 — the column index",
        "cosets": "three cosets — the three columns",
    },
    {
        "subgroup": span(((1, 1),)),
        "title": "K = ⟨XY⟩ — diagonal",
        "generators": "XY = (1,1)",
        "blurb": "Stepping down-and-right changes nothing; the stripes run diagonally.",
        "invariant": "(b − a) mod 3",
        "cosets": "three cosets — three diagonal stripes",
    },
    {
        "subgroup": span(((1, 2),)),
        "title": "K = ⟨XY²⟩ — anti-diagonal",
        "generators": "XY² = (1,2)",
        "blurb": "Stepping down-and-left changes nothing; the stripes lean the other way.",
        "invariant": "(a + b) mod 3",
        "cosets": "three cosets — three anti-diagonal stripes",
    },
)


def collect() -> list[dict[str, object]]:
    by_stabilizer: dict[frozenset[tuple[int, int]], list[tuple[int, ...]]] = defaultdict(list)
    for pattern in product((0, 1), repeat=len(CELLS)):
        by_stabilizer[stabilizer(pattern)].append(pattern)

    records = []
    for row in ROWS:
        subgroup = row["subgroup"]
        assert isinstance(subgroup, frozenset)
        patterns = sorted(by_stabilizer.get(subgroup, []))
        seen: set[frozenset[tuple[int, ...]]] = set()
        orbits: list[list[tuple[int, ...]]] = []
        for pattern in patterns:
            block = orbit(pattern)
            if block in seen:
                continue
            seen.add(block)
            orbits.append(sorted(block))
        records.append({
            **row,
            "patterns": patterns,
            "orbits": orbits,
            "size": len(subgroup),
            "index": len(CELLS) // len(subgroup),
            "orbit_size": len(CELLS) // len(subgroup),
        })
    return records


def validate(records: list[dict[str, object]]) -> None:
    total = 0
    for record in records:
        patterns = record["patterns"]
        orbits = record["orbits"]
        assert isinstance(patterns, list) and isinstance(orbits, list)
        if not patterns:
            raise ValueError(f"{record['title']}: no patterns")
        if sum(len(o) for o in orbits) != len(patterns):
            raise ValueError(f"{record['title']}: orbits do not cover the patterns")
        for block in orbits:
            if len(block) != record["orbit_size"]:
                raise ValueError(
                    f"{record['title']}: orbit size {len(block)} != {record['orbit_size']}"
                )
        expected = 2 if record["size"] == 9 else 2 ** 3 - 2
        if len(patterns) != expected:
            raise ValueError(f"{record['title']}: expected {expected} patterns")
        total += len(patterns)
    if total != 26:
        raise ValueError(f"expected 26 symmetric patterns, found {total}")


def pattern_svg(pattern: tuple[int, ...], cell: int = 17, gap: int = 2) -> str:
    size = N * cell + (N - 1) * gap
    parts = [
        f'<svg class="pat" viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
        f'role="img" aria-label="pattern {"".join(str(v) for v in pattern)}">'
    ]
    for (a, b), value in zip(CELLS, pattern):
        parts.append(
            f'<rect x="{b * (cell + gap)}" y="{a * (cell + gap)}" width="{cell}" '
            f'height="{cell}" rx="3" fill="{FILL if value else EMPTY}"'
            + ("" if value else f' stroke="{EDGE}" stroke-width="1"')
            + "/>"
        )
    parts.append("</svg>")
    return "".join(parts)


def row_html(record: dict[str, object]) -> str:
    orbits = record["orbits"]
    assert isinstance(orbits, list)
    blocks = "".join(
        '<div class="orbit"><p class="orbit-label">orbit '
        f'{i + 1} &middot; size {len(block)}</p><div class="orbit-pats">'
        + "".join(pattern_svg(p) for p in block)
        + "</div></div>"
        for i, block in enumerate(orbits)
    )
    return f"""
    <section class="stab-row" id="row-{record['index']}-{escape(str(record['invariant'])).replace(' ', '')[:6]}">
      <header class="row-head">
        <h3>{escape(str(record['title']))}</h3>
        <p class="row-meta"><span>|K| = {record['size']}</span>
          <span>index {record['index']}</span>
          <span>{len(record['patterns'])} patterns</span>
          <span>{len(orbits)} orbit{'s' if len(orbits) != 1 else ''} of size {record['orbit_size']}</span></p>
      </header>
      <div class="row-body">
        <dl class="row-data">
          <dt>Stabilizer</dt>
          <dd>Generated by <code>{escape(str(record['generators']))}</code>.
              {escape(str(record['blurb']))}</dd>
          <dt>As an equivalence relation</dt>
          <dd>Two cells are equivalent when <code>{escape(str(record['invariant']))}</code>
              agrees — {escape(str(record['cosets']))}.</dd>
          <dt>Orbits</dt>
          <dd>The ambient group has order 9 and the stabilizer has order
              {record['size']}, so every orbit has size
              9 / {record['size']} = {record['orbit_size']}. The
              {len(record['patterns'])} patterns fall into {len(orbits)}
              orbit{'s' if len(orbits) != 1 else ''}; patterns in one orbit are
              translates of each other and share this stabilizer exactly.</dd>
        </dl>
        <div class="orbits">{blocks}</div>
      </div>
    </section>"""


STYLE = """
  :root { --ink:#1b2430; --muted:#5a6470; --paper:#faf8f2; --rule:#ded8c9;
          --card:#ffffff; --accent:#0072B2; }
  body { background:var(--paper); color:var(--ink); }
  .patterns { max-width:1120px; margin:0 auto; padding:0 20px 72px; }
  .patterns h1 { font-size:2rem; line-height:1.2; margin:.2em 0 .3em; }
  .patterns h2 { font-size:1.32rem; margin:2.4rem 0 .7rem;
                 border-bottom:1px solid var(--rule); padding-bottom:.35rem; }
  .patterns h3 { font-size:1.05rem; margin:0 0 .2rem;
                 font-family:ui-monospace,Menlo,Consolas,monospace; }
  .overline { text-transform:uppercase; letter-spacing:.12em; font-size:.74rem;
              color:var(--muted); margin:2rem 0 0; }
  .lead { font-size:1.05rem; color:var(--muted); max-width:64ch; }
  .patterns p, .patterns li { max-width:74ch; }
  code { background:#eef1f4; padding:.08em .34em; border-radius:4px; font-size:.92em; }
  .funnel { display:flex; flex-wrap:wrap; gap:10px; list-style:none; padding:0;
            margin:1rem 0 0; }
  .funnel li { background:var(--card); border:1px solid var(--rule); border-radius:9px;
               padding:9px 14px; font-size:.9rem; }
  .funnel strong { font-size:1.15rem; display:block; }
  .stab-row { background:var(--card); border:1px solid var(--rule); border-radius:12px;
              padding:16px 18px; margin-bottom:16px; }
  .row-meta { margin:.1rem 0 .9rem; font-size:.78rem; color:var(--muted); }
  .row-meta span { display:inline-block; background:#eef1f4; border-radius:20px;
                   padding:.14em .7em; margin:0 .3em .3em 0; }
  .row-body { display:grid; gap:18px;
              grid-template-columns:repeat(auto-fit,minmax(min(300px,100%),1fr)); }
  .row-data { margin:0; }
  .row-data dt { font-size:.74rem; text-transform:uppercase; letter-spacing:.08em;
                 color:var(--accent); margin-top:.65rem; }
  .row-data dd { margin:.2rem 0 0; font-size:.9rem; }
  .orbits { display:flex; flex-wrap:wrap; gap:12px; align-content:flex-start; }
  .orbit { border:1px dashed var(--rule); border-radius:9px; padding:8px 10px 6px; }
  .orbit-label { margin:0 0 6px; font-size:.7rem; color:var(--muted);
                 text-transform:uppercase; letter-spacing:.06em; }
  .orbit-pats { display:flex; gap:8px; flex-wrap:wrap; }
  .pat { display:block; }
  .table-scroll { overflow-x:auto; }
  table { border-collapse:collapse; font-size:.9rem; min-width:520px; }
  th, td { text-align:left; padding:.42em .8em; border-bottom:1px solid var(--rule); }
  th { font-size:.76rem; text-transform:uppercase; letter-spacing:.07em; color:var(--muted); }
  td.num, th.num { text-align:right; font-variant-numeric:tabular-nums; }
  .footnote { color:var(--muted); font-size:.86rem; }
  @media (prefers-color-scheme: dark) {
    :root { --ink:#e8e6e1; --muted:#a8b0ba; --paper:#161a1f; --rule:#333a42;
            --card:#1e242b; --accent:#56B4E9; }
    code, .row-meta span { background:#2a323a; }
  }
"""

NAV = """
  <header class="site-header">
    <div class="header-inner">
      <a class="site-name" href="./">Spacetime-group visualizations</a>
      <nav aria-label="Project links">
        <a href="./">Gallery</a>
        <a href="brownian.html">brownian</a>
        <a href="torus-tutorial.html">Torus guide</a>
        <a href="torus-colorings.html">Binary catalog</a>
        <a href="torus-patterns.html" aria-current="page">Translation symmetries</a>
        <a href="torus-patterns-c4.html">With rotations</a>
        <a href="torus-cayley.html">Cayley graphs</a>
        <a href="torus-nonregular.html">Non-regular</a>
        <a href="color-pattern-catalog.html">Patterns</a>
        <a href="https://github.com/yaroslavvb/animated-groups">Source</a>
      </nav>
    </div>
  </header>
"""


def build_page() -> str:
    records = collect()
    validate(records)
    rows = "".join(row_html(record) for record in records)
    summary = "".join(
        f"<tr><td><code>{escape(str(r['title']))}</code></td>"
        f"<td class='num'>{r['size']}</td><td class='num'>{r['index']}</td>"
        f"<td class='num'>{len(r['patterns'])}</td>"
        f"<td class='num'>{len(r['orbits'])}</td>"
        f"<td class='num'>{r['orbit_size']}</td></tr>"
        for r in records
    )
    counts = "".join(
        f"<tr><td class='num'>{q}</td><td class='num'>{q}</td>"
        f"<td class='num'>{q ** 3 - q}</td><td class='num'>{4 * (q ** 3 - q)}</td>"
        f"<td class='num'>{q ** 9 - 4 * q ** 3 + 3 * q}</td>"
        f"<td class='num'>{q ** 9}</td></tr>"
        for q in (2, 3, 4)
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Every binary pattern on the 3x3 torus with a nontrivial stabilizer, grouped by stabilizer and by translation orbit.">
  <meta name="theme-color" content="#ffffff">
  <title>Symmetric patterns on the 3×3 torus</title>
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="site-controls-v2.css">
  <style>{STYLE}</style>
</head>
<body>
  <a class="skip-link" href="#patterns">Skip to patterns</a>
{NAV}
  <main id="patterns" class="patterns">
    <p class="overline">Companion to the torus tutorial</p>
    <h1>Symmetric patterns on the 3&times;3 torus</h1>
    <p class="lead">
      Colour each of the nine cells 0 or 1. There are 512 patterns, and only 26 of them have
      any translational symmetry at all. Here is every one, sorted by its stabilizer and then
      by orbit.
    </p>

    <h2>The funnel</h2>
    <ul class="funnel">
      <li><strong>512</strong>binary patterns</li>
      <li><strong>26</strong>with nontrivial stabilizer</li>
      <li><strong>10</strong>orbits among those</li>
      <li><strong>5</strong>nontrivial stabilizers</li>
      <li><strong>2</strong>types up to GL(2,&#120125;&#8323;)</li>
    </ul>
    <p>
      The other 486 patterns have trivial stabilizer &mdash; 95% of them &mdash; falling into
      54 orbits of size 9. Generic patterns have no symmetry, which is why searching over
      patterns is a poor way to find groups.
    </p>

    <h2>The five rows</h2>
    <p>
      Filled cells are 1, outlined cells are 0. Because the ambient group is abelian, every
      pattern in an orbit has <em>exactly the same</em> stabilizer, not merely a conjugate one,
      so each row below is a union of whole orbits.
    </p>
{rows}

    <h2>Summary</h2>
    <div class="table-scroll">
      <table>
        <thead><tr><th>stabilizer</th><th class="num">|K|</th><th class="num">index</th>
          <th class="num">patterns</th><th class="num">orbits</th>
          <th class="num">orbit size</th></tr></thead>
        <tbody>{summary}
          <tr><td><code>K = {{0}}</code> (not shown)</td><td class="num">1</td>
            <td class="num">9</td><td class="num">486</td><td class="num">54</td>
            <td class="num">9</td></tr>
        </tbody>
      </table>
    </div>
    <p class="footnote">
      Orbit sizes obey orbit&ndash;stabilizer exactly: <code>|orbit| = 9 / |K|</code>. Summing
      <code>2&times;1 + 8&times;3 + 54&times;9 = 512</code> recovers every pattern, and
      <code>2 + 8 + 54 = 64</code> recovers the Burnside count of patterns up to translation.
    </p>

    <h2>Counts for larger alphabets</h2>
    <p>
      Nothing above is special to two values. Writing <code>q</code> for the alphabet size,
      M&ouml;bius inversion over the subgroup lattice
      <code>{{0}} &lt; four lines &lt; A</code> gives closed forms, since a pattern with
      stabilizer containing <code>K</code> is a function on the <code>[A:K]</code> cosets.
    </p>
    <div class="table-scroll">
      <table>
        <thead><tr><th class="num">q</th><th class="num">K = A<br>(q)</th>
          <th class="num">each line<br>(q&sup3; &minus; q)</th><th class="num">all four lines</th>
          <th class="num">trivial<br>(q&#8313; &minus; 4q&sup3; + 3q)</th>
          <th class="num">total (q&#8313;)</th></tr></thead>
        <tbody>{counts}</tbody>
      </table>
    </div>
    <p class="footnote">
      The <code>q&sup3; &minus; q</code> reads directly: a line-stabilized pattern is a function
      on three cosets, so <code>q&sup3;</code> choices, minus the <code>q</code> constant ones
      whose stabilizer is really all of <code>A</code>.
    </p>

    <h2>Six subgroups, three types</h2>
    <p>
      The four line rows above are one <code>GL(2,&#120125;&#8323;)</code> orbit &mdash; one line
      per slope <code>0, 1, 2, &infin;</code> &mdash; so as <em>types</em> there are only two
      nontrivial cases, the constant pattern and the striped one. The four rows look different
      because a shear relates them, and a shear is an automorphism of the torus but not a
      symmetry of the square grid. The
      <a href="torus-tutorial.html">torus tutorial</a> names all six subgroups three ways:
      as stabilizers, by generators, and in Chaim Goodman-Strauss&rsquo;s colour notation.
    </p>
    <p class="footnote">
      Generated by <a href="https://github.com/yaroslavvb/animated-groups/blob/main/scripts/generate_torus_patterns.py">scripts/generate_torus_patterns.py</a>.
    </p>
  </main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify the committed page matches this generator")
    args = parser.parse_args()
    page = build_page()
    if args.check:
        if not PAGE.exists() or PAGE.read_text(encoding="utf-8") != page:
            print(f"stale: {PAGE.relative_to(ROOT)}")
            return 1
        print("torus pattern page is current")
        return 0
    PAGE.write_text(page, encoding="utf-8")
    print(f"wrote {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

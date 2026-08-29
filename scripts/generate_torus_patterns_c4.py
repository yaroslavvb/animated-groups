#!/usr/bin/env python3
"""Symmetric 0/1 patterns on the 3x3 torus, with quarter turns allowed.

The ambient group is Gamma = (Z/3)^2 :< C4 of order 36, where the quarter
turn r(a,b) = (-b, a) is an order-4 automorphism of (Z/3)^2.  Gamma is
nonabelian, so unlike the translation-only case the patterns in one orbit
generally have *conjugate* rather than *equal* stabilizers.  This page shows
every pattern with a nontrivial stabilizer, grouped by conjugacy class of
stabilizer and then by orbit.

Run with --check to verify the committed page is current.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
from html import escape
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "torus-patterns-c4.html"

N = 3
CELLS = [(a, b) for a in range(N) for b in range(N)]
INDEX = {cell: i for i, cell in enumerate(CELLS)}

FILL, EMPTY, EDGE = "#0072B2", "#e9e4d7", "#c8c1b0"


def rotate(quarters: int, cell: tuple[int, int]) -> tuple[int, int]:
    a, b = cell
    for _ in range(quarters):
        a, b = (-b) % N, a % N
    return a, b


GAMMA = [(t, m) for m in range(4) for t in CELLS]


def permutation(element: tuple[tuple[int, int], int]) -> tuple[int, ...]:
    t, m = element
    return tuple(
        INDEX[(((p := rotate(m, c))[0] + t[0]) % N, (p[1] + t[1]) % N)] for c in CELLS
    )


PERMS = {element: permutation(element) for element in GAMMA}
PERM_LIST = list(PERMS.values())


def compose(p: tuple[int, ...], q: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(p[q[i]] for i in range(len(q)))


def invert(p: tuple[int, ...]) -> tuple[int, ...]:
    out = [0] * len(p)
    for i, v in enumerate(p):
        out[v] = i
    return tuple(out)


def apply(p: tuple[int, ...], pattern: tuple[int, ...]) -> tuple[int, ...]:
    out = [0] * len(pattern)
    for i, v in enumerate(pattern):
        out[p[i]] = v
    return tuple(out)


def stabilizer(pattern: tuple[int, ...]) -> frozenset[tuple[int, ...]]:
    return frozenset(p for p in PERM_LIST if apply(p, pattern) == pattern)


def conjugacy_key(subgroup: frozenset[tuple[int, ...]]) -> tuple:
    return min(
        tuple(sorted(frozenset(compose(compose(g, h), invert(g)) for h in subgroup)))
        for g in PERM_LIST
    )


def is_abelian(subgroup: frozenset[tuple[int, ...]]) -> bool:
    return all(compose(x, y) == compose(y, x) for x in subgroup for y in subgroup)


ROW_NOTES = {
    36: ("&Gamma; itself", "C&#8323;&times;C&#8323; &#8906; C&#8324;, everything",
         "The constant patterns. Nothing can distinguish any cell, so the whole "
         "ambient group fixes them."),
    6: ("S&#8323; = D&#8323;", "three translations along a line, inverted by half-turns",
        "A striped pattern. The stripe direction is preserved by translations along "
        "it and by half-turns about points on it, but a quarter turn tilts it."),
    4: ("C&#8324;", "quarter turns about a single cell",
        "Patterns built from full quarter-turn orbits around one fixed cell."),
    2: ("C&#8322;", "one half-turn",
        "Patterns symmetric under a 180° turn about a point, but nothing more."),
}


def collect() -> dict[str, object]:
    patterns = list(product((0, 1), repeat=len(CELLS)))
    stabs = {pattern: stabilizer(pattern) for pattern in patterns}

    seen: set[tuple[int, ...]] = set()
    orbits: list[list[tuple[int, ...]]] = []
    for pattern in patterns:
        if pattern in seen:
            continue
        block = sorted({apply(p, pattern) for p in PERM_LIST})
        seen.update(block)
        orbits.append(block)

    classes: dict[tuple, dict[str, object]] = defaultdict(
        lambda: {"orbits": [], "subgroups": set(), "order": 0}
    )
    for block in orbits:
        subgroup = stabs[block[0]]
        key = conjugacy_key(subgroup)
        entry = classes[key]
        entry["orbits"].append(block)          # type: ignore[union-attr]
        entry["order"] = len(subgroup)
        for pattern in block:
            entry["subgroups"].add(stabs[pattern])   # type: ignore[union-attr]

    records = []
    for key, entry in sorted(classes.items(), key=lambda kv: -kv[1]["order"]):
        order = int(entry["order"])
        blocks = entry["orbits"]
        assert isinstance(blocks, list)
        subgroup = frozenset(key)
        # Distinguish the two order-6 classes by the direction of their stripes.
        label, gens, blurb = ROW_NOTES.get(order, ("trivial", "nothing",
                                                   "Patterns with no symmetry at all."))
        if order == 6:
            representative = min(blocks[0], key=sum)
            filled = [c for c, v in zip(CELLS, representative) if v]
            axis = "rows and columns" if len({c[0] for c in filled}) == 1 or \
                   len({c[1] for c in filled}) == 1 else "diagonals"
            label = f"S&#8323; &mdash; {axis}"
        records.append({
            "order": order,
            "orbit_size": len(GAMMA) // order,
            "orbits": blocks,
            "patterns": sum(len(b) for b in blocks),
            "subgroups": len(entry["subgroups"]),   # type: ignore[arg-type]
            "same_within_orbit": all(
                len({stabs[c] for c in b}) == 1 for b in blocks
            ),
            "abelian": is_abelian(subgroup),
            "label": label,
            "gens": gens,
            "blurb": blurb,
        })

    burnside = Fraction(
        sum(2 ** _cycles(p) for p in PERM_LIST), len(PERM_LIST)
    )
    return {"records": records, "orbits": len(orbits), "burnside": burnside,
            "subgroups": len({stabs[p] for p in patterns})}


def _cycles(p: tuple[int, ...]) -> int:
    seen: set[int] = set()
    count = 0
    for start in range(len(p)):
        if start in seen:
            continue
        count += 1
        x = start
        while x not in seen:
            seen.add(x)
            x = p[x]
    return count


def validate(data: dict[str, object]) -> None:
    records = data["records"]
    assert isinstance(records, list)
    if len(PERM_LIST) != 36 or len(set(PERM_LIST)) != 36:
        raise ValueError("the action of Gamma on the nine cells must be faithful")
    if data["orbits"] != data["burnside"]:
        raise ValueError(f"orbit count {data['orbits']} != Burnside {data['burnside']}")
    total_patterns = sum(int(r["patterns"]) for r in records)
    total_orbits = sum(len(r["orbits"]) for r in records)      # type: ignore[arg-type]
    if total_patterns != 512:
        raise ValueError(f"patterns total {total_patterns}, expected 512")
    if total_orbits != data["orbits"]:
        raise ValueError("orbit totals disagree")
    for record in records:
        for block in record["orbits"]:                        # type: ignore[union-attr]
            if len(block) != record["orbit_size"]:
                raise ValueError(
                    f"orbit size {len(block)} != 36/{record['order']}"
                )
    if len(records) != 6:
        raise ValueError(f"expected 6 conjugacy classes, found {len(records)}")


def pattern_svg(pattern: tuple[int, ...], cell: int = 15, gap: int = 2) -> str:
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


def row_html(record: dict[str, object], position: int) -> str:
    blocks = record["orbits"]
    assert isinstance(blocks, list)
    if record["order"] == 1:
        body = (f'<p class="row-note">{record["patterns"]} patterns in '
                f'{len(blocks)} orbits of size 36 — not drawn.</p>')
    else:
        body = '<div class="orbits">' + "".join(
            '<div class="orbit"><p class="orbit-label">orbit '
            f'{i + 1} &middot; {len(block)} patterns</p><div class="orbit-pats">'
            + "".join(pattern_svg(p) for p in block)
            + "</div></div>"
            for i, block in enumerate(blocks)
        ) + "</div>"
    conj = ("every pattern in an orbit has the <strong>same</strong> stabilizer"
            if record["same_within_orbit"] else
            "patterns in one orbit have <strong>conjugate but different</strong> "
            "stabilizers")
    return f"""
    <section class="stab-row" id="class-{position}">
      <header class="row-head">
        <h3>|K| = {record['order']} &mdash; {record['label']}</h3>
        <p class="row-meta"><span>orbit size {record['orbit_size']}</span>
          <span>{len(blocks)} orbit{'s' if len(blocks) != 1 else ''}</span>
          <span>{record['patterns']} patterns</span>
          <span>{record['subgroups']} subgroup{'s' if record['subgroups'] != 1 else ''} in the class</span>
          <span>{'abelian' if record['abelian'] else 'nonabelian'}</span></p>
      </header>
      <dl class="row-data">
        <dt>Stabilizer</dt>
        <dd>Generated by {record['gens']}. {escape(str(record['blurb']))}</dd>
        <dt>Orbits</dt>
        <dd>Orbit&ndash;stabilizer forces every orbit to have size
            36 / {record['order']} = {record['orbit_size']}. Here {conj}.</dd>
      </dl>
      {body}
    </section>"""


STYLE = """
  :root { --ink:#1b2430; --muted:#5a6470; --paper:#faf8f2; --rule:#ded8c9;
          --card:#ffffff; --accent:#0072B2; }
  body { background:var(--paper); color:var(--ink); }
  .patterns { max-width:1180px; margin:0 auto; padding:0 20px 72px; }
  .patterns h1 { font-size:2rem; line-height:1.2; margin:.2em 0 .3em; }
  .patterns h2 { font-size:1.32rem; margin:2.4rem 0 .7rem;
                 border-bottom:1px solid var(--rule); padding-bottom:.35rem; }
  .patterns h3 { font-size:1.02rem; margin:0 0 .2rem; }
  .overline { text-transform:uppercase; letter-spacing:.12em; font-size:.74rem;
              color:var(--muted); margin:2rem 0 0; }
  .lead { font-size:1.05rem; color:var(--muted); max-width:64ch; }
  .patterns p, .patterns li { max-width:76ch; }
  code { background:#eef1f4; padding:.08em .34em; border-radius:4px; font-size:.92em; }
  .stab-row { background:var(--card); border:1px solid var(--rule); border-radius:12px;
              padding:16px 18px; margin-bottom:16px; }
  .row-meta { margin:.1rem 0 .8rem; font-size:.78rem; color:var(--muted); }
  .row-meta span { display:inline-block; background:#eef1f4; border-radius:20px;
                   padding:.14em .7em; margin:0 .3em .3em 0; }
  .row-data { margin:0 0 .9rem; }
  .row-data dt { font-size:.74rem; text-transform:uppercase; letter-spacing:.08em;
                 color:var(--accent); margin-top:.6rem; }
  .row-data dd { margin:.2rem 0 0; font-size:.9rem; }
  .row-note { font-size:.88rem; color:var(--muted); }
  .orbits { display:flex; flex-wrap:wrap; gap:10px; }
  .orbit { border:1px dashed var(--rule); border-radius:9px; padding:7px 9px 5px; }
  .orbit-label { margin:0 0 5px; font-size:.68rem; color:var(--muted);
                 text-transform:uppercase; letter-spacing:.06em; }
  .orbit-pats { display:flex; gap:6px; flex-wrap:wrap; max-width:420px; }
  .pat { display:block; }
  .table-scroll { overflow-x:auto; }
  table { border-collapse:collapse; font-size:.9rem; min-width:540px; }
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
        <a href="torus-patterns.html">Translation symmetries</a>
        <a href="torus-patterns-c4.html" aria-current="page">With rotations</a>
        <a href="torus-cayley.html">Cayley graphs</a>
        <a href="torus-nonregular.html">Non-regular</a>
        <a href="color-pattern-catalog.html">Patterns</a>
        <a href="https://github.com/yaroslavvb/animated-groups">Source</a>
      </nav>
    </div>
  </header>
"""


def build_page() -> str:
    data = collect()
    validate(data)
    records = data["records"]
    assert isinstance(records, list)
    rows = "".join(row_html(r, i) for i, r in enumerate(records))
    summary = "".join(
        f"<tr><td>|K| = {r['order']} &mdash; {r['label']}</td>"
        f"<td class='num'>{r['orbit_size']}</td>"
        f"<td class='num'>{len(r['orbits'])}</td>"
        f"<td class='num'>{r['patterns']}</td>"
        f"<td class='num'>{r['subgroups']}</td>"
        f"<td>{'same' if r['same_within_orbit'] else 'conjugate only'}</td></tr>"
        for r in records
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Binary patterns on the 3x3 torus under translations and quarter turns: a nonabelian ambient group of order 36, where orbit-mates have conjugate rather than equal stabilizers.">
  <meta name="theme-color" content="#ffffff">
  <title>3×3 torus patterns with quarter turns</title>
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="site-controls-v2.css">
  <style>{STYLE}</style>
</head>
<body>
  <a class="skip-link" href="#patterns">Skip to patterns</a>
{NAV}
  <main id="patterns" class="patterns">
    <p class="overline">Same torus, bigger ambient group</p>
    <h1>3&times;3 torus patterns with quarter turns</h1>
    <p class="lead">
      Allow rotation as well as translation and the ambient group grows from 9 elements to 36 —
      and stops being abelian. That single change alters what a stabilizer even is: patterns in
      one orbit no longer share a stabilizer, they only share a <em>conjugacy class</em>.
    </p>

    <h2>The ambient group</h2>
    <p>
      The quarter turn <code>r(a,b) = (&minus;b, a)</code> is an order-4 automorphism of
      <code>(&#8484;/3)&sup2;</code>, so it acts on the wrapped 3&times;3 grid. Together with the
      nine translations it generates
    </p>
    <p><code>&Gamma; = (&#8484;/3)&sup2; &#8906; C&#8324;</code>, of order <strong>36</strong>,
       acting faithfully on the nine cells.</p>
    <p>
      A cell has orbit 9 and stabilizer of order 4 (the quarter turns about it), and
      9 &times; 4 = 36 — the same frame-counting argument as for the square grid, with the
      four reflections dropped.
    </p>

    <h2>What changes</h2>
    <div class="table-scroll">
      <table>
        <thead><tr><th></th><th class="num">translations only</th>
          <th class="num">with quarter turns</th></tr></thead>
        <tbody>
          <tr><td>ambient order</td><td class="num">9</td><td class="num">36</td></tr>
          <tr><td>abelian?</td><td class="num">yes</td><td class="num">no</td></tr>
          <tr><td>orbits of the 512 patterns</td><td class="num">64</td><td class="num">28</td></tr>
          <tr><td>distinct stabilizer subgroups</td><td class="num">6</td><td class="num">32</td></tr>
          <tr><td>conjugacy classes of stabilizers</td><td class="num">6</td><td class="num">6</td></tr>
          <tr><td>patterns with nontrivial stabilizer</td><td class="num">26</td><td class="num">224</td></tr>
        </tbody>
      </table>
    </div>

    <h2>The new phenomenon</h2>
    <p>
      With only translations, the ambient group was abelian, so
      <code>Stab(t&middot;P) = t&middot;Stab(P)&middot;t&#8315;&sup1; = Stab(P)</code> — orbit-mates
      had <em>identical</em> stabilizers. That fails here. Take the nine patterns with a single
      filled cell: they form one orbit, and each is fixed by the quarter turns about
      <em>its own</em> cell, so the orbit carries <strong>nine different</strong> subgroups of
      order 4, all conjugate.
    </p>
    <p>
      That is why the table above shows 32 subgroups but still only 6 classes, and it is the same
      distinction that forces Conway&rsquo;s <code>G/H/K</code> notation: the three colour
      stabilizers of an <code>S&#8323;</code> colouring are conjugate but distinct. The abelian
      torus cannot show it; this one can.
    </p>

    <h2>The six classes</h2>
    <p>
      Filled cells are 1, outlined cells are 0. Rows are ordered by stabilizer size; every pattern
      with a nontrivial stabilizer is drawn, grouped by orbit.
    </p>
{rows}

    <h2>Summary</h2>
    <div class="table-scroll">
      <table>
        <thead><tr><th>class</th><th class="num">orbit size</th><th class="num">orbits</th>
          <th class="num">patterns</th><th class="num">subgroups</th>
          <th>within an orbit</th></tr></thead>
        <tbody>{summary}</tbody>
      </table>
    </div>
    <p class="footnote">
      Checks: orbit sizes are exactly <code>36 / |K|</code>; the orbit total is 28, matching
      Burnside&rsquo;s lemma over &Gamma; independently; and the pattern total is 512.
    </p>

    <h2>Why the four lines became two classes</h2>
    <p>
      In the <a href="torus-patterns.html">translation-only version</a> the four line subgroups —
      rows, columns, and the two diagonals — were four separate rows, fused only by
      <code>GL(2,&#120125;&#8323;)</code> at the classification level. The quarter turn is now
      <em>inside</em> the group: it carries rows to columns and each diagonal to the other. So
      they merge into two classes of six subgroups each, and the merging happens in the ambient
      group rather than in the equivalence on groups.
    </p>
    <p>
      Note also that the striped stabilizers are <code>S&#8323;</code>, not <code>C&#8326;</code>:
      three translations along the stripe, inverted by the half-turns about points on it. The
      smallest nonabelian group appears here without being asked for.
    </p>
    <p class="footnote">
      Generated by <a href="https://github.com/yaroslavvb/animated-groups/blob/main/scripts/generate_torus_patterns_c4.py">scripts/generate_torus_patterns_c4.py</a>.
      Companion to the <a href="torus-tutorial.html">torus tutorial</a> and the
      <a href="torus-patterns.html">translation-only pattern page</a>.
    </p>
  </main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify the committed page is current")
    args = parser.parse_args()
    page = build_page()
    if args.check:
        if not PAGE.exists() or PAGE.read_text(encoding="utf-8") != page:
            print(f"stale: {PAGE.relative_to(ROOT)}")
            return 1
        print("rotation pattern page is current")
        return 0
    PAGE.write_text(page, encoding="utf-8")
    print(f"wrote {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

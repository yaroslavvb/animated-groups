#!/usr/bin/env python3
"""Cayley graphs of the 2x2 torus group and every one of its subgroups.

The ambient group is Gamma = (Z/2)^2 :< <s> of order 8, where s(a,b) = (b,a).
Mod 2 the quarter turn degenerates to this diagonal flip, so Gamma is the
dihedral group D4 acting on the four cells as a Sylow 2-subgroup of S4.

Every Cayley graph is drawn with one colour per generator.  Each subgroup is
paired with its orbit colouring, which is how a subgroup gets specified by
drawing a pattern.

Run with --check to verify the committed page is current.
"""

from __future__ import annotations

import argparse
from html import escape
from itertools import product
from math import cos, pi, sin
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "torus-cayley.html"

N = 2
CELLS = [(a, b) for a in range(N) for b in range(N)]
INDEX = {cell: i for i, cell in enumerate(CELLS)}
IDENT = tuple(range(len(CELLS)))


def rotate(m: int, cell: tuple[int, int]) -> tuple[int, int]:
    a, b = cell
    for _ in range(m):
        a, b = (-b) % N, a % N
    return a, b


def element(t: tuple[int, int], m: int) -> tuple[int, ...]:
    return tuple(
        INDEX[(((p := rotate(m, c))[0] + t[0]) % N, (p[1] + t[1]) % N)] for c in CELLS
    )


GAMMA = sorted({element(t, m) for m in range(4) for t in CELLS})


def mul(p: tuple[int, ...], q: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(p[q[i]] for i in range(len(q)))


def order(p: tuple[int, ...]) -> int:
    k, x = 1, p
    while x != IDENT:
        x = mul(x, p)
        k += 1
    return k


X = element((1, 0), 0)
Y = element((0, 1), 0)
S = element((0, 0), 1)
XY = mul(X, Y)
XS = mul(X, S)
YS = mul(Y, S)
XYS = mul(XY, S)

LABEL = {IDENT: "e", X: "X", Y: "Y", XY: "XY", S: "s", XS: "Xs", YS: "Ys", XYS: "XYs"}

# One colour per generator, Okabe-Ito.
GEN_COLOUR = {"X": "#0072B2", "Y": "#E69F00", "s": "#009E73",
              "XY": "#56B4E9", "Xs": "#CC79A7", "XYs": "#D55E00"}
CELL_COLOURS = ["#0072B2", "#E69F00", "#009E73", "#CC79A7"]
INK, MUTED = "#1b2430", "#6c7681"


def close(generators: tuple[tuple[int, ...], ...]) -> frozenset[tuple[int, ...]]:
    seen, frontier = {IDENT}, [IDENT]
    while frontier:
        x = frontier.pop()
        for g in generators:
            y = mul(x, g)
            if y not in seen:
                seen.add(y)
                frontier.append(y)
    return frozenset(seen)


def all_subgroups() -> list[frozenset[tuple[int, ...]]]:
    found = set()
    for k in range(0, 3):
        for gens in product(GAMMA, repeat=k):
            found.add(close(gens))
    return sorted(found, key=lambda H: (-len(H), sorted(LABEL[p] for p in H)))


def minimal_generators(H: frozenset[tuple[int, ...]]) -> tuple[str, ...]:
    ordered = sorted(H, key=lambda g: LABEL[g])
    for k in range(0, 3):
        best = None
        for gens in product(ordered, repeat=k):
            if close(gens) == H:
                names = tuple(LABEL[g] for g in gens)
                if best is None or names < best:
                    best = names
        if best is not None:
            return best
    return ()


def orbits(H: frozenset[tuple[int, ...]]) -> list[list[int]]:
    seen: set[int] = set()
    out: list[list[int]] = []
    for i in range(len(CELLS)):
        if i in seen:
            continue
        block = sorted({h[i] for h in H})
        seen.update(block)
        out.append(block)
    return out


def partition_stabilizer(blocks: list[list[int]]) -> frozenset[tuple[int, ...]]:
    sets = [set(b) for b in blocks]
    return frozenset(g for g in GAMMA if all({g[i] for i in b} == b for b in sets))


def is_normal(H: frozenset[tuple[int, ...]]) -> bool:
    inv = {g: next(h for h in GAMMA if mul(g, h) == IDENT) for g in GAMMA}
    return all(frozenset(mul(mul(g, h), inv[g]) for h in H) == H for g in GAMMA)


# --------------------------------------------------------------------------
# Drawing

def cayley_svg(elements: list[tuple[int, ...]], gens: tuple[str, ...],
               size: int = 190) -> str:
    """Draw Cay(H, gens); 2-regular graphs are laid out as their cycle."""
    by_name = {"X": X, "Y": Y, "s": S, "XY": XY, "Xs": XS, "XYs": XYS}
    gen_elems = [(name, by_name[name]) for name in gens]
    n = len(elements)
    r = size / 2 - 26

    # Layout: walk the cycle when 2-regular, else two concentric rings by coset.
    adjacency = {g: set() for g in elements}
    for g in elements:
        for _name, s in gen_elems:
            adjacency[g].add(mul(g, s))
            adjacency[g].add(mul(g, next(h for h in elements if mul(s, h) == IDENT)))
    for g in elements:
        adjacency[g].discard(g)

    pos: dict[tuple[int, ...], tuple[float, float]] = {}
    degrees = {len(a) for a in adjacency.values()}
    if n == 1:
        pos[elements[0]] = (size / 2, size / 2)
    elif degrees == {2} and n > 2:
        walk, current, prev = [IDENT], IDENT, None
        while len(walk) < n:
            nxt = next(v for v in adjacency[current] if v != prev)
            walk.append(nxt)
            prev, current = current, nxt
        for i, g in enumerate(walk):
            angle = -pi / 2 + 2 * pi * i / n
            pos[g] = (size / 2 + r * cos(angle), size / 2 + r * sin(angle))
    elif n == 8:
        inner = sorted(close((X, Y)), key=lambda g: LABEL[g])
        outer = [g for g in elements if g not in inner]
        for ring, radius in ((inner, r * 0.5), (outer, r)):
            for i, g in enumerate(ring):
                angle = -pi / 2 + 2 * pi * i / len(ring) + (0 if radius == r else pi / 4)
                pos[g] = (size / 2 + radius * cos(angle), size / 2 + radius * sin(angle))
    else:
        for i, g in enumerate(elements):
            angle = -pi / 2 + 2 * pi * i / n
            pos[g] = (size / 2 + r * cos(angle), size / 2 + r * sin(angle))

    parts = [f'<svg class="cayley" viewBox="0 0 {size} {size}" width="{size}" '
             f'height="{size}" role="img" aria-label="Cayley graph on {n} vertices">']
    defs = []
    drawn: set[tuple] = set()
    for name, s in gen_elems:
        colour = GEN_COLOUR[name]
        directed = order(s) > 2
        if directed:
            defs.append(
                f'<marker id="a-{name}" viewBox="0 0 8 8" refX="7" refY="4" '
                f'markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
                f'<path d="M0,0 L8,4 L0,8 z" fill="{colour}"/></marker>'
            )
        for g in elements:
            h = mul(g, s)
            key = (name, g, h) if directed else (name, *sorted([g, h]))
            if key in drawn:
                continue
            drawn.add(key)
            (x1, y1), (x2, y2) = pos[g], pos[h]
            arrow = f' marker-end="url(#a-{name})"' if directed else ""
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{colour}" stroke-width="2.6" stroke-linecap="round"{arrow}/>'
            )
    if defs:
        parts.insert(1, "<defs>" + "".join(defs) + "</defs>")
    for g, (x, y) in pos.items():
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11" fill="#ffffff" '
                     f'stroke="{INK}" stroke-width="1.4"/>')
        parts.append(f'<text x="{x:.1f}" y="{y + 3.6:.1f}" text-anchor="middle" '
                     f'font-size="9.5" font-weight="700" fill="{INK}">{LABEL[g]}</text>')
    parts.append("</svg>")
    return "".join(parts)


def pattern_svg(blocks: list[list[int]], cell: int = 26, gap: int = 3) -> str:
    label = {}
    for i, block in enumerate(blocks):
        for c in block:
            label[c] = i
    size = N * cell + gap
    parts = [f'<svg class="pat" viewBox="0 0 {size} {size}" width="{size}" '
             f'height="{size}" role="img" aria-label="orbit colouring">']
    for i, (a, b) in enumerate(CELLS):
        parts.append(
            f'<rect x="{b * (cell + gap)}" y="{a * (cell + gap)}" width="{cell}" '
            f'height="{cell}" rx="4" fill="{CELL_COLOURS[label[i]]}"/>'
        )
    parts.append("</svg>")
    return "".join(parts)


def legend(gens: tuple[str, ...]) -> str:
    return '<p class="legend">' + "".join(
        f'<span><i style="background:{GEN_COLOUR[g]}"></i>{g}'
        f'<em>order {order({"X": X, "Y": Y, "s": S, "XY": XY, "Xs": XS, "XYs": XYS}[g])}</em></span>'
        for g in gens
    ) + "</p>"


FAILURE = {
    frozenset({IDENT, X, Y, XY}):
        "Transitive on the four cells, so the only invariant pattern is constant — "
        "and a constant pattern is fixed by all of &Gamma;.",
    frozenset({IDENT, XY, XS, YS}):
        "Also transitive: its order-4 generator is a single 4-cycle, so again only "
        "the constant pattern survives.",
    frozenset({IDENT, XY}):
        "Its orbits force cell&nbsp;0 to match cell&nbsp;3 and cell&nbsp;1 to match "
        "cell&nbsp;2 — but that pattern is then also fixed by both flips, giving the "
        "order-4 group above instead.",
}


def subgroup_card(H: frozenset[tuple[int, ...]], position: int) -> str:
    gens = minimal_generators(H)
    blocks = orbits(H)
    realizable = partition_stabilizer(blocks) == H
    elements = sorted(H, key=lambda g: (order(g), LABEL[g]))
    graph = cayley_svg(elements, gens) if gens else cayley_svg(elements, ())
    names = ", ".join(sorted(LABEL[p] for p in H))
    gen_text = ", ".join(f"<code>{g}</code>" for g in gens) if gens else "none (trivial)"
    if realizable:
        colouring = (
            f"Colour each orbit differently and the stabilizer is exactly this "
            f"subgroup. Needs <strong>{len(blocks)} colour"
            f"{'s' if len(blocks) != 1 else ''}</strong>."
        )
        verdict = '<span class="ok">drawable</span>'
    else:
        colouring = FAILURE[H]
        verdict = '<span class="no">not drawable</span>'
    return f"""
      <article class="sub-card" id="sub-{position}">
        <header>
          <h3>|H| = {len(H)} &middot; {verdict}</h3>
          <p class="elems"><code>{{{escape(names)}}}</code></p>
        </header>
        <div class="art">
          <div>{graph}{legend(gens)}</div>
          <div class="pat-wrap">{pattern_svg(blocks)}
            <span class="pat-caption">orbit colouring</span></div>
        </div>
        <dl>
          <dt>Generators</dt><dd>{gen_text}</dd>
          <dt>Index &amp; normality</dt>
          <dd>index {8 // len(H)} in &Gamma;; {'normal' if is_normal(H) else '<strong>not normal</strong>'}</dd>
          <dt>Orbits on the four cells</dt>
          <dd><code>{escape(str([b for b in blocks]))}</code></dd>
          <dt>Connection with colouring</dt><dd>{colouring}</dd>
        </dl>
      </article>"""


STYLE = """
  :root { --ink:#1b2430; --muted:#5a6470; --paper:#faf8f2; --rule:#ded8c9;
          --card:#ffffff; --accent:#0072B2; }
  body { background:var(--paper); color:var(--ink); }
  .cayley-page { max-width:1140px; margin:0 auto; padding:0 20px 72px; }
  .cayley-page h1 { font-size:2rem; line-height:1.2; margin:.2em 0 .3em; }
  .cayley-page h2 { font-size:1.32rem; margin:2.4rem 0 .7rem;
                    border-bottom:1px solid var(--rule); padding-bottom:.35rem; }
  .cayley-page h3 { font-size:1rem; margin:0 0 .15rem; }
  .overline { text-transform:uppercase; letter-spacing:.12em; font-size:.74rem;
              color:var(--muted); margin:2rem 0 0; }
  .lead { font-size:1.05rem; color:var(--muted); max-width:64ch; }
  .cayley-page p, .cayley-page li { max-width:74ch; }
  code { background:#eef1f4; padding:.08em .34em; border-radius:4px; font-size:.92em; }
  .legend { display:flex; flex-wrap:wrap; gap:9px; margin:.4rem 0 0; font-size:.76rem; }
  .legend span { display:inline-flex; align-items:center; gap:5px; color:var(--muted); }
  .legend i { width:14px; height:4px; border-radius:2px; display:inline-block; }
  .legend em { font-style:normal; opacity:.65; }
  .big-graphs { display:grid; gap:18px;
                grid-template-columns:repeat(auto-fit,minmax(min(300px,100%),1fr)); }
  .big-graphs figure { background:var(--card); border:1px solid var(--rule);
                       border-radius:12px; padding:14px 16px; margin:0; }
  .big-graphs figcaption { font-size:.86rem; color:var(--muted); margin-top:.4rem; }
  .sub-grid { display:grid; gap:16px;
              grid-template-columns:repeat(auto-fit,minmax(min(320px,100%),1fr)); }
  .sub-card { background:var(--card); border:1px solid var(--rule); border-radius:12px;
              padding:14px 16px 8px; }
  .elems { margin:.1rem 0 .6rem; font-size:.82rem; }
  .art { display:flex; gap:14px; align-items:flex-start; flex-wrap:wrap; }
  .pat-wrap { display:flex; flex-direction:column; gap:4px; }
  .pat-caption { font-size:.66rem; color:var(--muted); }
  .ok { color:#046a38; font-weight:700; }
  .no { color:#a03000; font-weight:700; }
  .sub-card dl { margin:.6rem 0 0; }
  .sub-card dt { font-size:.72rem; text-transform:uppercase; letter-spacing:.07em;
                 color:var(--accent); margin-top:.5rem; }
  .sub-card dd { margin:.15rem 0 0; font-size:.86rem; }
  .table-scroll { overflow-x:auto; }
  table { border-collapse:collapse; font-size:.9rem; min-width:540px; }
  th, td { text-align:left; padding:.42em .8em; border-bottom:1px solid var(--rule); }
  th { font-size:.76rem; text-transform:uppercase; letter-spacing:.07em; color:var(--muted); }
  td.num, th.num { text-align:right; font-variant-numeric:tabular-nums; }
  .footnote { color:var(--muted); font-size:.86rem; }
  svg.cayley, svg.pat { display:block; max-width:100%; height:auto; }
  @media (prefers-color-scheme: dark) {
    :root { --ink:#e8e6e1; --muted:#a8b0ba; --paper:#161a1f; --rule:#333a42;
            --card:#1e242b; --accent:#56B4E9; }
    code { background:#2a323a; }
    .ok { color:#5fd39b; } .no { color:#ff9d6b; }
  }
"""

NAV = """
  <header class="site-header">
    <div class="header-inner">
      <a class="site-name" href="./">Spacetime-group visualizations</a>
      <nav aria-label="Project links">
        <a href="./">Gallery</a>
        <a href="color-pattern-catalog.html">Patterns</a>
        <a href="torus-tutorial.html">Torus tutorial</a>
        <a href="torus-patterns.html">Torus patterns</a>
        <a href="torus-patterns-c4.html">With rotations</a>
        <a href="torus-cayley.html" aria-current="page">Cayley graphs</a>
        <a href="https://github.com/yaroslavvb/animated-groups">Source</a>
      </nav>
    </div>
  </header>
"""


def build_page() -> str:
    subs = all_subgroups()
    if len(subs) != 10:
        raise ValueError(f"expected 10 subgroups of D4, found {len(subs)}")
    drawable = [H for H in subs if partition_stabilizer(orbits(H)) == H]
    if len(drawable) != 7:
        raise ValueError(f"expected 7 drawable subgroups, found {len(drawable)}")
    cards = "".join(subgroup_card(H, i) for i, H in enumerate(subs))
    rows = "".join(
        f"<tr><td class='num'>{len(H)}</td>"
        f"<td><code>{escape(', '.join(minimal_generators(H)) or '—')}</code></td>"
        f"<td class='num'>{8 // len(H)}</td>"
        f"<td>{'yes' if is_normal(H) else 'no'}</td>"
        f"<td class='num'>{len(orbits(H))}</td>"
        f"<td>{'drawable' if partition_stabilizer(orbits(H)) == H else 'not drawable'}</td></tr>"
        for H in subs
    )
    octagon = cayley_svg(sorted(GAMMA, key=lambda g: LABEL[g]), ("X", "s"), size=280)
    layered = cayley_svg(sorted(GAMMA, key=lambda g: LABEL[g]), ("X", "Y", "s"), size=280)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Cayley graphs of the 2x2 torus group D4 and all ten of its subgroups, with one edge colour per generator and the orbit colouring that specifies each subgroup.">
  <meta name="theme-color" content="#ffffff">
  <title>Cayley graphs of the 2×2 torus group</title>
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="site-controls-v2.css">
  <style>{STYLE}</style>
</head>
<body>
  <a class="skip-link" href="#cayley">Skip to graphs</a>
{NAV}
  <main id="cayley" class="cayley-page">
    <p class="overline">Eight elements, ten subgroups, one octagon</p>
    <h1>Cayley graphs of the 2&times;2 torus group</h1>
    <p class="lead">
      Translations of the wrapped 2&times;2 grid together with the diagonal flip give a group of
      order 8. Small enough to draw completely — every element, every subgroup, and the pattern
      that picks each subgroup out.
    </p>

    <h2>The group</h2>
    <p>
      Mod 2 the quarter turn <code>r(a,b) = (&minus;b, a)</code> becomes the diagonal flip
      <code>s(a,b) = (b,a)</code>, because <code>&minus;1 &equiv; 1</code>. So there is no genuine
      rotation here, and <code>r&sup2; = 1</code>. With the four translations this generates
    </p>
    <p><code>&Gamma; = (&#8484;/2)&sup2; &#8906; &#10216;s&#10217;</code> of order <strong>8</strong>,
       which is <code>D&#8324;</code> — acting on the four cells as a Sylow 2-subgroup of
       <code>S&#8324;</code>.</p>
    <p>
      Writing <code>X</code> and <code>Y</code> for the two translations, the flip conjugates one
      into the other: <code>s X s&#8315;&sup1; = Y</code>. So <code>Y</code> is redundant and
      <code>&Gamma; = &#10216;X, s&#10217;</code> — and since <code>X&sup2; = s&sup2; = 1</code>
      with <code>(Xs)</code> of order 4, this is the dihedral presentation
      <code>&#10216;X, s | X&sup2; = s&sup2; = (Xs)&#8308; = 1&#10217;</code>.
    </p>

    <h2>Two views of &Gamma;</h2>
    <div class="big-graphs">
      <figure>{octagon}{legend(("X", "s"))}
        <figcaption><strong>Cay(&Gamma;, {{X, s}})</strong> — 8 vertices, 8 edges, degree 2.
        Both generators are involutions, so each contributes one undirected edge per vertex and
        the graph is a single <strong>octagon</strong> with edges alternating <code>X</code>,
        <code>s</code>. Girth 8, diameter 4.</figcaption></figure>
      <figure>{layered}{legend(("X", "Y", "s"))}
        <figcaption><strong>Cay(&Gamma;, {{X, Y, s}})</strong> — 8 vertices, 12 edges, degree 3.
        Keeping the redundant <code>Y</code> splits the group into two squares (the cosets of the
        translation subgroup) joined by a perfect matching of <code>s</code>-edges. Girth 4,
        diameter 3.</figcaption></figure>
    </div>
    <p class="footnote">
      Dropping <code>s</code> altogether disconnects the graph into two components — the index of
      the translation subgroup, visible as connected components.
    </p>

    <h2>All ten subgroups</h2>
    <p>
      Each card shows <code>Cay(H, gens)</code> with one colour per generator, next to the
      <em>orbit colouring</em>: colour each orbit of <code>H</code> on the four cells a different
      colour. That colouring is how you specify a subgroup by drawing — but it only works for
      seven of the ten, and the three failures are labelled with their reason.
    </p>
    <div class="sub-grid">{cards}
    </div>

    <h2>Summary</h2>
    <div class="table-scroll">
      <table>
        <thead><tr><th class="num">|H|</th><th>generators</th><th class="num">index</th>
          <th>normal</th><th class="num">orbits</th><th>as a stabilizer</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <p class="footnote">
      Seven of the ten subgroups are stabilizers of some pattern. The three exceptions fail for
      two distinct reasons: the translation subgroup and the cyclic <code>C&#8324;</code> are
      <em>transitive</em>, so they force the constant pattern; the centre
      <code>{{e, XY}}</code> forces a pattern that carries strictly more symmetry than asked for.
      Realizable subgroups are exactly the partition stabilizers, and they form a closure system.
    </p>
    <p class="footnote">
      Generated by <a href="https://github.com/yaroslavvb/animated-groups/blob/main/scripts/generate_torus_cayley.py">scripts/generate_torus_cayley.py</a>.
      Companion to the <a href="torus-tutorial.html">torus tutorial</a>.
    </p>
  </main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    page = build_page()
    if args.check:
        if not PAGE.exists() or PAGE.read_text(encoding="utf-8") != page:
            print(f"stale: {PAGE.relative_to(ROOT)}")
            return 1
        print("cayley page is current")
        return 0
    PAGE.write_text(page, encoding="utf-8")
    print(f"wrote {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

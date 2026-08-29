#!/usr/bin/env python3
"""Visualize the non-regular colourings of the 2x2 torus group.

Gamma = (Z/2)^2 :< <s> of order 8 has four non-normal subgroups, all of order
two, in two conjugacy classes.  Each has trivial core, so the coset colouring
it defines has four colours but a colour group of order eight -- non-regular,
Conway's double slash.

The point of the page: <s> and <X> give the *same* G, the *same* K, the same
number of colours and therefore the same symbol Gamma^4//{e}, yet they are
genuinely different colourings, because the two subgroups are not conjugate.
That is precisely why the notation has to name H.

Run with --check to verify the committed page is current.
"""

from __future__ import annotations

import argparse
from html import escape
from itertools import product
from math import cos, pi, sin
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "torus-nonregular.html"

N = 2
CELLS = [(a, b) for a in range(N) for b in range(N)]
INDEX = {c: i for i, c in enumerate(CELLS)}
IDENT = tuple(range(len(CELLS)))


def rotate(m, cell):
    a, b = cell
    for _ in range(m):
        a, b = (-b) % N, a % N
    return a, b


def element(t, m):
    return tuple(
        INDEX[(((p := rotate(m, c))[0] + t[0]) % N, (p[1] + t[1]) % N)] for c in CELLS
    )


GAMMA = sorted({element(t, m) for m in range(4) for t in CELLS})


def mul(p, q):
    return tuple(p[q[i]] for i in range(len(q)))


def inv(p):
    out = [0] * len(p)
    for i, v in enumerate(p):
        out[v] = i
    return tuple(out)


def order(p):
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

PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7"]
NAMES = "ABCD"
GEN_COLOUR = {"X": "#0072B2", "s": "#009E73"}
INK = "#1b2430"


def core(H):
    return frozenset(h for h in H if all(mul(mul(inv(g), h), g) in H for g in GAMMA))


def cosets(H):
    """Left cosets gH, with H first so it receives the label A."""
    seen, out = set(), []
    for g in (IDENT, *(x for x in GAMMA if x != IDENT)):
        block = frozenset(mul(g, h) for h in H)
        if block not in seen:
            seen.add(block)
            out.append(sorted(block, key=lambda p: LABEL[p]))
    return out


def permutation_string(p):
    if p == IDENT:
        return "identity"
    parts, seen = [], set()
    for i in range(len(CELLS)):
        if i in seen:
            continue
        cycle, x = [i], p[i]
        while x != i:
            cycle.append(x)
            seen.add(x)
            x = p[x]
        seen.add(i)
        if len(cycle) > 1:
            parts.append("(" + "&thinsp;".join(NAMES[j] for j in cycle) + ")")
    return " ".join(parts)


# --------------------------------------------------------------------------

def pattern_svg(colouring, cell=40, gap=4, title=""):
    size = N * cell + gap
    parts = [f'<svg class="pat" viewBox="0 0 {size} {size}" width="{size}" '
             f'height="{size}" role="img" aria-label="{escape(title)}">']
    for i, (a, b) in enumerate(CELLS):
        parts.append(
            f'<rect x="{b * (cell + gap)}" y="{a * (cell + gap)}" width="{cell}" '
            f'height="{cell}" rx="6" fill="{PALETTE[colouring[i]]}"/>'
        )
        parts.append(
            f'<text x="{b * (cell + gap) + cell / 2}" y="{a * (cell + gap) + cell / 2 + 5}" '
            f'text-anchor="middle" font-size="15" font-weight="700" fill="#fffaf1">'
            f'{NAMES[colouring[i]]}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def octagon_svg(H, size=300):
    """Cay(Gamma,{X,s}) as an octagon with each coset of H tinted."""
    walk, current, use_s = [IDENT], IDENT, True
    while len(walk) < 8:
        current = mul(current, S if use_s else X)
        walk.append(current)
        use_s = not use_s
    pos = {}
    r = size / 2 - 34
    for i, g in enumerate(walk):
        ang = -pi / 2 + 2 * pi * i / 8
        pos[g] = (size / 2 + r * cos(ang), size / 2 + r * sin(ang))
    block_of = {}
    for idx, block in enumerate(cosets(H)):
        for g in block:
            block_of[g] = idx
    parts = [f'<svg class="oct" viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
             f'role="img" aria-label="octagon with cosets tinted">']
    for i, g in enumerate(walk):
        h = walk[(i + 1) % 8]
        same = block_of[g] == block_of[h]
        colour = PALETTE[block_of[g]] if same else "#c3bdae"
        width = 7 if same else 2.4
        (x1, y1), (x2, y2) = pos[g], pos[h]
        parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                     f'stroke="{colour}" stroke-width="{width}" stroke-linecap="round"/>')
    for g, (x, y) in pos.items():
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="15" '
                     f'fill="{PALETTE[block_of[g]]}" stroke="{INK}" stroke-width="1.4"/>')
        parts.append(f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" '
                     f'font-size="10.5" font-weight="700" fill="#fffaf1">{LABEL[g]}</text>')
    parts.append("</svg>")
    return "".join(parts)


def action_table(H):
    rows = []
    for g in sorted(GAMMA, key=lambda g: (order(g), LABEL[g])):
        in_h = g in H
        in_k = g == IDENT
        cls = "in-k" if in_k else ("in-h" if in_h else "")
        rows.append(
            f'<tr class="{cls}"><td><code>{LABEL[g]}</code></td>'
            f'<td class="num">{order(g)}</td>'
            f'<td>{permutation_string(g)}</td>'
            f'<td>{"&check;" if in_h else ""}</td>'
            f'<td>{"&check;" if in_k else ""}</td></tr>'
        )
    return "".join(rows)


def case(H, key, title, note):
    blocks = cosets(H)
    K = core(H)
    block_sets = [frozenset(block) for block in blocks]
    block_index = {block: i for i, block in enumerate(block_sets)}
    base = frozenset(H)
    if block_index.get(base) != 0:
        raise ValueError("the base coset H must receive the label A")
    stab = {
        i: frozenset(
            g for g in GAMMA
            if frozenset(mul(g, x) for x in block) == block
        )
        for i, block in enumerate(block_sets)
    }
    distinct = {frozenset(v) for v in stab.values()}
    names = ", ".join(sorted(LABEL[p] for p in H))
    stab_rows = "".join(
        f"<tr><td><strong>{NAMES[i]}</strong></td>"
        f"<td><code>{{{', '.join(sorted(LABEL[g] for g in stab[i]))}}}</code></td></tr>"
        for i in range(4)
    )
    coset_rows = "".join(
        f"<tr><td>{NAMES[i]}</td><td><code>{{{', '.join(LABEL[g] for g in b)}}}</code></td>"
        f"<td>sends <strong>A</strong> &rarr; "
        f"<strong>{NAMES[block_index[frozenset(mul(b[0], h) for h in H)]]}</strong></td></tr>"
        for i, b in enumerate(blocks)
    )
    return f"""
    <section class="case" id="case-{key}">
      <h3>{escape(title)}</h3>
      <p class="case-note"><code>H = {{{escape(names)}}}</code>. {note}</p>
      <div class="case-art">
        <div>{octagon_svg(H)}
          <p class="cap">Each thick coloured edge is one coset of <code>H</code> —
             one colour. Thin grey edges change the colour.</p></div>
        <div class="side">
          <table class="mini"><caption>the four cosets</caption><tbody>{coset_rows}</tbody></table>
          <table class="mini"><caption>colour stabilizers</caption><tbody>{stab_rows}</tbody></table>
          <p class="cap">{len(distinct)} distinct stabilizers for 4 colours, since
             |N(H)|/|H| = {8 // len(distinct) if distinct else 0}&thinsp;/&thinsp;{len(H)}.</p>
        </div>
      </div>
      <p class="triple"><code>G</code> = &Gamma; (8) &nbsp;&middot;&nbsp;
        <code>H</code> = order {len(H)}, index {8 // len(H)} &nbsp;&middot;&nbsp;
        <code>K</code> = core(H) = <code>{{{', '.join(sorted(LABEL[g] for g in K))}}}</code>
        &nbsp;&middot;&nbsp; 4 colours, colour group of order {8 // len(K)}
        &rarr; <strong>non-regular</strong></p>
    </section>"""


STYLE = """
  :root { --ink:#1b2430; --muted:#5a6470; --paper:#faf8f2; --rule:#ded8c9;
          --card:#ffffff; --accent:#0072B2; }
  body { background:var(--paper); color:var(--ink); }
  .nr { max-width:1120px; margin:0 auto; padding:0 20px 72px; }
  .nr h1 { font-size:2rem; line-height:1.2; margin:.2em 0 .3em; }
  .nr h2 { font-size:1.32rem; margin:2.4rem 0 .7rem;
           border-bottom:1px solid var(--rule); padding-bottom:.35rem; }
  .nr h3 { font-size:1.05rem; margin:0 0 .2rem; }
  .overline { text-transform:uppercase; letter-spacing:.12em; font-size:.74rem;
              color:var(--muted); margin:2rem 0 0; }
  .lead { font-size:1.05rem; color:var(--muted); max-width:64ch; }
  .nr p, .nr li { max-width:74ch; }
  code { background:#eef1f4; padding:.08em .34em; border-radius:4px; font-size:.92em; }
  .compare { display:grid; gap:18px;
             grid-template-columns:repeat(auto-fit,minmax(min(280px,100%),1fr)); }
  .compare figure { background:var(--card); border:1px solid var(--rule);
                    border-radius:12px; padding:14px 16px; margin:0; }
  .compare figcaption { font-size:.86rem; color:var(--muted); margin-top:.5rem; }
  .case { background:var(--card); border:1px solid var(--rule); border-radius:12px;
          padding:16px 18px; margin-bottom:16px; }
  .case-note { font-size:.9rem; color:var(--muted); margin:.1rem 0 .8rem; }
  .case-art { display:flex; gap:20px; flex-wrap:wrap; align-items:flex-start; }
  .side { display:flex; flex-direction:column; gap:10px; min-width:240px; }
  .cap { font-size:.76rem; color:var(--muted); margin:.4rem 0 0; max-width:34ch; }
  .triple { margin:.9rem 0 0; font-size:.88rem; padding-top:.7rem;
            border-top:1px solid var(--rule); }
  table { border-collapse:collapse; font-size:.88rem; }
  th, td { text-align:left; padding:.34em .7em; border-bottom:1px solid var(--rule); }
  th { font-size:.74rem; text-transform:uppercase; letter-spacing:.07em; color:var(--muted); }
  td.num, th.num { text-align:right; font-variant-numeric:tabular-nums; }
  caption { font-size:.72rem; text-transform:uppercase; letter-spacing:.07em;
            color:var(--muted); text-align:left; padding-bottom:.25em; }
  .mini { min-width:0; }
  .action tr.in-h td { background:rgba(0,158,115,.13); }
  .action tr.in-k td { background:rgba(0,158,115,.28); font-weight:700; }
  .table-scroll { overflow-x:auto; }
  .footnote { color:var(--muted); font-size:.86rem; }
  svg.pat, svg.oct { display:block; max-width:100%; height:auto; }
  @media (prefers-color-scheme: dark) {
    :root { --ink:#e8e6e1; --muted:#a8b0ba; --paper:#161a1f; --rule:#333a42;
            --card:#1e242b; --accent:#56B4E9; }
    code { background:#2a323a; }
    .action tr.in-h td { background:rgba(0,158,115,.22); }
    .action tr.in-k td { background:rgba(0,158,115,.4); }
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
        <a href="torus-patterns-c4.html">With rotations</a>
        <a href="torus-cayley.html">Cayley graphs</a>
        <a href="torus-nonregular.html" aria-current="page">Non-regular</a>
        <a href="color-pattern-catalog.html">Patterns</a>
        <a href="https://github.com/yaroslavvb/animated-groups">Source</a>
      </nav>
    </div>
  </header>
"""


def build_page():
    Hs = frozenset({IDENT, S})
    Hx = frozenset({IDENT, X})
    Hv = frozenset({IDENT, XY, S, XYS})          # normal, gives a regular colouring
    for H in (Hs, Hx):
        if core(H) != frozenset({IDENT}):
            raise ValueError("expected trivial core")
        if len(cosets(H)) != 4:
            raise ValueError("expected four cosets")
    if core(Hv) != Hv:
        raise ValueError("the comparison subgroup must be normal")
    rainbow = (0, 1, 2, 3)
    regular = (0, 1, 1, 0)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Non-regular colourings of the 2x2 torus group: two non-conjugate subgroups give the same symbol but different colourings, which is why Conway's notation must name H.">
  <meta name="theme-color" content="#ffffff">
  <title>Non-regular colourings and why H must be named</title>
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="site-controls-v2.css">
  <style>{STYLE}</style>
</head>
<body>
  <a class="skip-link" href="#nr">Skip to content</a>
{NAV}
  <main id="nr" class="nr">
    <p class="overline">Where the double slash comes from</p>
    <h1>Non-regular colourings, and why <code>H</code> must be named</h1>
    <p class="lead">
      The 2&times;2 torus group has four non-normal subgroups. Each defines a colouring with
      four colours but a colour group of order eight — non-regular. Two of them produce the
      same Conway symbol and yet are different colourings.
    </p>

    <h2>Regular versus non-regular</h2>
    <p>
      A colouring is <em>regular</em> when the number of colours equals the order of the colour
      group, which happens exactly when <code>H = K</code>. Compare:
    </p>
    <div class="compare">
      <figure>{pattern_svg(regular, title="regular two-colouring")}
        <figcaption><strong>Regular.</strong> <code>H = K = {{e, XY, s, XYs}}</code>, a
        <em>normal</em> subgroup of index 2. Two colours, colour group <code>C&#8322;</code> of
        order 2. Colours = group order, so <code>H</code> is recoverable from <code>K</code> and
        Conway writes a single slash.</figcaption></figure>
      <figure>{pattern_svg(rainbow, title="non-regular four-colouring")}
        <figcaption><strong>Non-regular.</strong> <code>H</code> has order 2 and
        <code>K = core(H) = {{e}}</code>. Four colours, colour group of order <strong>8</strong>.
        Eight &ne; four, so <code>H</code> is <em>not</em> recoverable — double slash. The picture
        is trivial; all the structure is in the action.</figcaption></figure>
    </div>

    <h2>The action is where the content is</h2>
    <p>
      For the rainbow pattern every element of &Gamma; permutes the four colours. Rows shaded
      green lie in <code>H</code> (they fix colour <strong>A</strong>); the darker row is
      <code>K</code>.
    </p>
    <div class="table-scroll">
      <table class="action">
        <thead><tr><th>element</th><th class="num">order</th><th>colour permutation</th>
          <th>fixes A</th><th>in K</th></tr></thead>
        <tbody>{action_table(Hs)}</tbody>
      </table>
    </div>
    <p>
      Only the identity fixes every colour, so <code>K = {{e}}</code>. Two elements fix
      <strong>A</strong>, so <code>H</code> has order 2 and index 4 — the four colours. The map
      &Gamma; &rarr; S&#8324; is injective but lands in a subgroup of index 3, which is exactly
      the gap between 8 and 4.
    </p>

    <h2>The two cases</h2>
{case(Hs, "s", "H = ⟨s⟩ — the diagonal flip",
      "This one is realized by the grid itself: the four cells <em>are</em> the coset space "
      "&Gamma;/&#10216;s&#10217;, and the rainbow pattern is its colouring.")}
{case(Hx, "x", "H = ⟨X⟩ — a translation",
      "This one is not realized by the cells: &#10216;X&#10217; has only two orbits on them, "
      "so the colouring needs a different four-element &Gamma;-set. Drawn abstractly, as the "
      "four cosets.")}

    <h2>Why the symbol is not enough</h2>
    <p>
      Both cases give identical <code>G</code>, identical <code>K</code>, and the same number of
      colours — therefore the same Conway symbol <code>&Gamma;&#8308;//{{e}}</code>:
    </p>
    <div class="table-scroll">
      <table>
        <thead><tr><th></th><th><code>H = &#10216;s&#10217;</code></th>
          <th><code>H = &#10216;X&#10217;</code></th></tr></thead>
        <tbody>
          <tr><td><code>G</code></td><td>&Gamma;, order 8</td><td>&Gamma;, order 8</td></tr>
          <tr><td><code>K = core(H)</code></td><td><code>{{e}}</code></td><td><code>{{e}}</code></td></tr>
          <tr><td>colours</td><td>4</td><td>4</td></tr>
          <tr><td>symbol</td><td><code>&Gamma;&#8308;//{{e}}</code></td><td><code>&Gamma;&#8308;//{{e}}</code></td></tr>
          <tr><td>realized on the cells?</td><td>yes</td><td>no</td></tr>
          <tr><td>the colourings are</td><td colspan="2"><strong>different</strong></td></tr>
        </tbody>
      </table>
    </div>
    <p>
      They differ because <code>&#10216;s&#10217;</code> and <code>&#10216;X&#10217;</code> are
      <strong>not conjugate</strong> — they lie in the two separate classes of non-normal
      subgroups — so the &Gamma;-sets <code>&Gamma;/&#10216;s&#10217;</code> and
      <code>&Gamma;/&#10216;X&#10217;</code> are not isomorphic. Same symbol, two colourings.
    </p>
    <p>
      That is the whole reason Conway's notation carries three groups rather than two. The double
      slash in <code>G&#8319;//K</code> is a <em>warning</em> that <code>H</code> has been
      suppressed and cannot be reconstructed; the full form <code>G&#8319;/H/K</code> names it.
      On an abelian ambient this never arises — every subgroup is normal, <code>H = K</code>
      always, and a single slash suffices.
    </p>
    <p class="footnote">
      Generated by <a href="https://github.com/yaroslavvb/animated-groups/blob/main/scripts/generate_torus_nonregular.py">scripts/generate_torus_nonregular.py</a>.
      Companion to the <a href="torus-cayley.html">Cayley graph page</a> and the
      <a href="torus-tutorial.html">torus tutorial</a>.
    </p>
  </main>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    page = build_page()
    if args.check:
        if not PAGE.exists() or PAGE.read_text(encoding="utf-8") != page:
            print(f"stale: {PAGE.relative_to(ROOT)}")
            return 1
        print("non-regular page is current")
        return 0
    PAGE.write_text(page, encoding="utf-8")
    print(f"wrote {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

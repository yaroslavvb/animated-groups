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


def colouring_svg(colouring: tuple[int, ...], cell: int = 24, gap: int = 3) -> str:
    size = N * cell + gap
    parts = [f'<svg class="pat" viewBox="0 0 {size} {size}" width="{size}" '
             f'height="{size}" role="img" aria-label="colouring '
             f'{"".join(str(v) for v in colouring)}">']
    for i, (a, b) in enumerate(CELLS):
        parts.append(
            f'<rect x="{b * (cell + gap)}" y="{a * (cell + gap)}" width="{cell}" '
            f'height="{cell}" rx="4" fill="{CELL_COLOURS[colouring[i]]}"/>'
        )
    parts.append("</svg>")
    return "".join(parts)


def automorphisms() -> list[dict]:
    """All automorphisms of Gamma, by extending images of two generators."""
    from collections import deque
    gens = next([a, b] for a, b in product(GAMMA, repeat=2) if close((a, b)) == set(GAMMA))
    out = []
    for images in product(GAMMA, repeat=2):
        phi, queue, ok = {IDENT: IDENT}, deque([IDENT]), True
        while queue and ok:
            x = queue.popleft()
            for s, t in zip(gens, images):
                y, z = mul(x, s), mul(phi[x], t)
                if y in phi:
                    if phi[y] != z:
                        ok = False
                        break
                else:
                    phi[y] = z
                    queue.append(y)
        if ok and len(set(phi.values())) == len(GAMMA):
            if all(phi[mul(a, b)] == mul(phi[a], phi[b]) for a in GAMMA for b in GAMMA):
                out.append(phi)
    return out


AUTS = automorphisms()


def colour_groups(q: int) -> list[dict]:
    """All (G, H, K) colour groups for chromatic q-colourings, up to Aut(Gamma)."""
    found: dict[tuple, dict] = {}
    for colouring in product(range(q), repeat=len(CELLS)):
        if len(set(colouring)) != q:
            continue
        acting, rho = [], {}
        for g in GAMMA:
            image, ok = {}, True
            for i in range(len(CELLS)):
                src, dst = colouring[i], colouring[g[i]]
                if image.setdefault(src, dst) != dst:
                    ok = False
                    break
            if ok and len(set(image.values())) == len(image):
                acting.append(g)
                rho[g] = tuple(image[c] for c in range(q))
        reach, frontier = {0}, [0]
        while frontier:
            c = frontier.pop()
            for g in acting:
                d = rho[g][c]
                if d not in reach:
                    reach.add(d)
                    frontier.append(d)
        if len(reach) != q:                      # not chromatic
            continue
        G = frozenset(acting)
        K = frozenset(g for g in acting if rho[g] == tuple(range(q)))
        H = frozenset(g for g in acting if rho[g][0] == 0)
        key = min((tuple(sorted(phi[y] for y in G)), tuple(sorted(phi[y] for y in H)),
                   tuple(sorted(phi[y] for y in K))) for phi in AUTS)
        entry = found.setdefault(key, {"G": G, "H": H, "K": K, "rho": rho,
                                      "colourings": []})
        entry["colourings"].append(colouring)
    return sorted(found.values(), key=lambda e: (-len(e["G"]), -len(e["K"])))


def set_html(H) -> str:
    return "{" + ", ".join(sorted(LABEL[p] for p in H)) + "}"


BY_NAME = {"e": IDENT, "X": X, "Y": Y, "XY": XY, "s": S, "Xs": XS, "Ys": YS, "XYs": XYS}
PREFERENCE = ("X", "s", "Y", "XY", "Xs", "Ys", "XYs")

# Presentations for the subgroups that actually occur as a colour group's G.
# A relator (word, exponent) means (word)^exponent = 1.
PRESENTATIONS: dict[tuple[str, ...], tuple[tuple[tuple[str, ...], int], ...]] = {
    ("X", "s"): ((("X",), 2), (("s",), 2), (("X", "s"), 4)),      # D4
    ("X", "Y"): ((("X",), 2), (("Y",), 2), (("X", "Y"), 2)),      # V4
}


def preferred_generators(H) -> tuple[str, ...]:
    """Smallest generating set drawn from PREFERENCE, in that order."""
    inside = [name for name in PREFERENCE if BY_NAME[name] in H]
    for size in range(0, 3):
        for combo in product(inside, repeat=size):
            if close(tuple(BY_NAME[c] for c in combo)) == set(H):
                return combo
    raise ValueError("no small generating set found")


def evaluate(word: tuple[str, ...], exponent: int, value, compose, identity):
    """Evaluate (word)^exponent under an arbitrary composition law."""
    result = identity
    for _ in range(exponent):
        for name in word:
            result = compose(result, value(name))
    return result


def relator_html(gens: tuple[str, ...]) -> str:
    def show(word, exponent):
        body = "".join(word)
        if len(word) > 1:
            body = f"({body})"
        return f"{body}<sup>{exponent}</sup>"
    rels = PRESENTATIONS[gens]
    return " = ".join(show(w, e) for w, e in rels) + " = 1"


def permutation_name(p: tuple[int, ...], k: int) -> str:
    labels = "ABCD"[:k]
    if all(p[i] == i for i in range(k)):
        return "1"
    parts, seen = [], set()
    for i in range(k):
        if i in seen:
            continue
        cycle, x = [i], p[i]
        while x != i:
            cycle.append(x)
            seen.add(x)
            x = p[x]
        seen.add(i)
        if len(cycle) > 1:
            parts.append("(" + "".join(labels[j] for j in cycle) + ")")
    return "".join(parts)


def permutation_order(p: tuple[int, ...], k: int) -> int:
    identity = tuple(range(k))
    current, steps = p, 1
    while current != identity:
        current = tuple(p[i] for i in current)
        steps += 1
    return steps


def presentation_block(entry: dict, q: int) -> str:
    """Generators, their colour permutations, the signature, and the relator check."""
    G = entry["G"]
    gens = preferred_generators(G)
    rho = entry["rho"]
    identity = tuple(range(q))

    def pcompose(a, b):
        return tuple(a[b[i]] for i in range(q))

    rows = "".join(
        f"<tr><td><code>{g}</code></td><td>&#8614;</td>"
        f"<td><code>{permutation_name(rho[BY_NAME[g]], q)}</code></td>"
        f"<td class='num'>order {permutation_order(rho[BY_NAME[g]], q)}</td></tr>"
        for g in gens
    )
    checks = []
    for word, exponent in PRESENTATIONS[gens]:
        in_group = evaluate(word, exponent, lambda nm: BY_NAME[nm], mul, IDENT)
        in_colours = evaluate(word, exponent, lambda nm: rho[BY_NAME[nm]], pcompose, identity)
        if in_group != IDENT or in_colours != identity:
            raise ValueError(f"relator {word}^{exponent} fails")
        checks.append(f"&rho;({''.join(word)})<sup>{exponent}</sup> = 1 &check;")
    long_sig = " ".join(
        f"{g}<sup>{permutation_name(rho[BY_NAME[g]], q)}</sup>" for g in gens
    )
    short_sig = " ".join(
        f"{g}<sup>{permutation_order(rho[BY_NAME[g]], q)}</sup>" for g in gens
    )
    return f"""
        <div class="pres">
          <p class="pres-line"><code>G = &#10216; {', '.join(gens)} |
            {relator_html(gens)} &#10217;</code></p>
          <table class="rho"><tbody>{rows}</tbody></table>
          <p class="sig"><span>signature</span> <code>{long_sig}</code></p>
          <p class="sig"><span>short form</span> <code>{short_sig}</code></p>
          <p class="checks">{' &nbsp; '.join(checks)}</p>
        </div>"""


def colour_group_card(entry: dict, q: int) -> str:
    G, H, K = entry["G"], entry["H"], entry["K"]
    regular = len(G) // len(K) == q
    slash = "/" if regular else "//"
    pats = "".join(colouring_svg(c) for c in entry["colourings"][:8])
    more = ("" if len(entry["colourings"]) <= 8
            else f'<span class="more">+{len(entry["colourings"]) - 8} more</span>')
    return f"""
      <article class="cg-card">
        <header>
          <h3><code>G<sup>{q}</sup>{slash}K</code></h3>
          <p class="cg-meta"><span>{q} colours</span>
            <span>|G/K| = {len(G) // len(K)}</span>
            <span class="{'reg' if regular else 'nonreg'}">
              {'regular' if regular else 'non-regular'}</span>
            <span>{len(entry['colourings'])} colourings</span></p>
        </header>
        <div class="cg-pats">{pats}{more}</div>
        {presentation_block(entry, q)}
        <table class="ghk">
          <tbody>
            <tr><th>G</th><td><code>{set_html(G)}</code></td><td class="num">order {len(G)}</td></tr>
            <tr><th>H</th><td><code>{set_html(H)}</code></td><td class="num">index {len(G) // len(H)}</td></tr>
            <tr><th>K</th><td><code>{set_html(K)}</code></td><td class="num">order {len(K)}</td></tr>
          </tbody>
        </table>
      </article>"""


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
  .cg-head { font-size:1rem; margin:1.6rem 0 .5rem; color:var(--muted);
             text-transform:uppercase; letter-spacing:.07em; font-size:.78rem; }
  .cg-grid { display:grid; gap:16px;
             grid-template-columns:repeat(auto-fit,minmax(min(320px,100%),1fr)); }
  .cg-card { background:var(--card); border:1px solid var(--rule); border-radius:12px;
             padding:14px 16px 10px; }
  .cg-card h3 { font-size:1.05rem; margin:0 0 .2rem; }
  .cg-meta { margin:.1rem 0 .7rem; font-size:.76rem; color:var(--muted); }
  .cg-meta span { display:inline-block; background:#eef1f4; border-radius:20px;
                  padding:.14em .7em; margin:0 .3em .3em 0; }
  .cg-meta .reg { background:rgba(0,158,115,.18); color:#046a38; font-weight:700; }
  .cg-meta .nonreg { background:rgba(213,94,0,.18); color:#a03000; font-weight:700; }
  .cg-pats { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:.7rem; }
  .cg-pats .more { font-size:.72rem; color:var(--muted); }
  table.ghk { font-size:.84rem; width:100%; min-width:0; table-layout:fixed; }
  table.ghk th { width:1.6em; color:var(--accent); font-weight:700; text-transform:none;
                 letter-spacing:0; font-size:.9rem; }
  table.ghk td { overflow-wrap:anywhere; }
  table.ghk td.num { width:5.4em; white-space:nowrap; }
  .pres { border-top:1px solid var(--rule); margin-top:.7rem; padding-top:.6rem; }
  .pres-line { margin:0 0 .5rem; font-size:.86rem; }
  table.rho { font-size:.86rem; width:auto; min-width:0; margin:0 0 .5rem; }
  table.rho td { border-bottom:none; padding:.12em .5em .12em 0; }
  table.rho td.num { color:var(--muted); font-size:.78rem; }
  .sig { margin:.15rem 0; font-size:.84rem; }
  .sig span { display:inline-block; min-width:6.4em; color:var(--muted);
              font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; }
  .checks { margin:.5rem 0 0; font-size:.76rem; color:#046a38; }
  @media (prefers-color-scheme: dark) { .checks { color:#5fd39b; } }
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
        <a href="brownian.html">brownian</a>
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
    two = colour_groups(2)
    three = colour_groups(3)
    four = colour_groups(4)
    if len(two) != 2 or len(three) != 0 or len(four) != 1:
        raise ValueError(f"unexpected colour-group census: {len(two)}, {len(three)}, {len(four)}")
    cg_two = "".join(colour_group_card(e, 2) for e in two)
    cg_four = "".join(colour_group_card(e, 4) for e in four)
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

    <h2>Colour groups</h2>
    <p>
      The subgroups above are single groups. A <em>colour group</em> records the whole triple
      that a colouring produces:
      <code>G</code> the symmetries permuting the colours,
      <code>H</code> those fixing one chosen colour, and
      <code>K</code> those fixing every colour. All three are stabilizers —
      of the unordered partition, of one block, and of the labelled partition respectively —
      and <code>K &sube; H &sube; G</code>. The colouring is <strong>regular</strong> when
      <code>|G/K|</code> equals the number of colours, which happens exactly when
      <code>H = K</code>; Conway then writes a single slash.
    </p>

    <h3 class="cg-head">Two colours &mdash; every colour group</h3>
    <div class="cg-grid">{cg_two}
    </div>
    <p class="footnote">
      Both are regular, so <code>H = K</code> and a single slash suffices. The first is the
      checkerboard, whose symmetry is all of &Gamma;; the second is the striped colouring, where
      the diagonal flip fails to act and <code>G</code> drops to the translation subgroup. Six
      chromatic two-colourings in total &mdash; the colour classes must have equal size, so only
      the three 2+2 partitions qualify, each with two labellings.
    </p>

    <h3 class="cg-head">Three colours &mdash; none</h3>
    <p>
      There are <strong>no</strong> chromatic three-colourings: the colour group permutes the
      colour classes transitively, so they must all have the same size, and
      <code>3 &#8740; 4</code>. Only <code>k</code> dividing 4 is possible &mdash; one, two or
      four colours.
    </p>

    <h3 class="cg-head">Four colours &mdash; the non-regular one</h3>
    <div class="cg-grid">{cg_four}
    </div>
    <p class="footnote">
      Here <code>|G/K| = 8</code> but there are only 4 colours, so <code>H &ne; K</code> and the
      symbol carries a double slash. This is the rainbow colouring; the
      <a href="torus-nonregular.html">non-regular page</a> works through why <code>H</code> has
      to be named separately.
    </p>

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

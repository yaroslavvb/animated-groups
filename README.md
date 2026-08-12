# Visualizations of two-dimensional spacetime groups

This repository constructs finite periodic renderings of exact equivariant
motif models for selected `(2+1)`-dimensional spacetime-group operations
appearing in, or motivated by, the classification of Chenhang Ke and Congjun
Wu. The web catalog contains eleven actions, each represented by three motif
families. Four rows reproduce coordinate operations stated in the paper, one
realizes the coordinate action of the listed `4′` magnetic point group, and six
are project-specific finite-loop specializations or constructions in the same
affine framework. The canonical artifacts remain infinitely looping GIFs; the
web page uses seekable H.264 playback proxies so that every motif has an
independent Play/Pause button and a 60-position phase slider.

**Live gallery:** [yaroslavvb.github.io/animated-groups](https://yaroslavvb.github.io/animated-groups/)

The site also includes the [colour-group census](https://yaroslavvb.github.io/animated-groups/future-directions.html)
and an exact [51-row nontrivial clockwork/coloring correspondence](https://yaroslavvb.github.io/animated-groups/clockwork-coloring-correspondence.html),
backed by the complete 68-record audit, with Conway orbifold pairs and static coloured-wallpaper plates.
The companion [cyclic-colouring/polar-space-group atlas](https://yaroslavvb.github.io/animated-groups/space-group-correspondence.html)
pairs each of the 51 more-than-one-colour plates with its current Hermann–Mauguin space-group
name, UCL/Birkbeck reference page, and an exact presentation relative to the displayed lift cell.
The 17 one-colour products remain as muted audit notes, while the JSON and generated plate set
retain all 68 records. The copyrighted UCL HTML and GIF files are not redistributed.

Every displayed action admits the pure temporal period
`U:(x,t) -> (x,t+T)`, which acts trivially on the represented state. The action
therefore descends to periodic time `S^1_T = R/TZ`. The catalog is a restricted
selection from the Ke–Wu classification, not a realization of all 275 groups;
groups without a pure temporal period are outside the scope of the faithful
periodic representations considered here.

## Relation to Ke–Wu

In [*Two-Dimensional Space-Time Groups: Classification and Applications*](https://arxiv.org/abs/2604.05619),
Chenhang Ke and Congjun Wu write a general space-time operation as
`(r,t) -> (Rr+u, st+tau)` in
[Eq. (1)](https://arxiv.org/html/2604.05619v1#S2.E1). Rows 01, 02, 04, and
05 visualize coordinate operations stated explicitly in the paper: the
[time glide](https://arxiv.org/html/2604.05619v1#S4.F2),
[quarter-period time screw](https://arxiv.org/html/2604.05619v1#S2.SS2.SSS0.Px3),
[mixed glide](https://arxiv.org/html/2604.05619v1#S2.SS2.SSS0.Px1), and the
coordinate part of
[glide time reversal](https://arxiv.org/html/2604.05619v1#S2.SS2.SSS0.Px2).
Row 06 realizes the coordinate action of the listed `4′` magnetic point group in
[Table 1](https://arxiv.org/html/2604.05619v1#S2.T1). Rows 07, 08, and 10
are finite-loop specializations or combinations of paper-supported point
mechanisms, including the
[threefold screw](https://arxiv.org/html/2604.05619v1#S3.E4). Rows 03, 09,
and 11 are this project's mixed-translation/phase-graph constructions,
grounded in the paper's
[space-time translation lattice](https://arxiv.org/html/2604.05619v1#S2.p3)
and [Bravais-lattice framework](https://arxiv.org/html/2604.05619v1#S2.F1).

The paper does not use the proposed double-bracket notation below. The
`C_n` and `D_n` names in this gallery denote phase-circle quotients or relay
orders, not official identifiers among the 275 classified groups. Likewise,
the gallery's **graph non-product** label refers to a graph subgroup defined by
a nontrivial phase homomorphism; it is not synonymous with Ke and Wu's
crystallographic
[non-symmorphic condition](https://arxiv.org/html/2604.05619v1#S2.p4) for a
fractional lift `(g|u)` relative to the translation lattice. In the
visualizations, `iota` denotes reversal of the periodic time coordinate, not
antiunitary quantum time reversal; the paper makes that distinction in
[its coordinate-space discussion](https://arxiv.org/html/2604.05619v1#S4.p7).

## Proposed spacetime-orbifold notation

The gallery labels each action as `Q ⟦g ↦ τ_a, h ↦ ι_b⟧`.  The prefix `Q`
is the standard Conway orbifold or rosette signature of the projected spatial
action.  The brackets are a proposed extension—not standard orbifold
notation—that record its action on periodic time: `τ_a` sends `t` to `t+aT`,
while `ι_b` sends `t` to `-t+bT`. The precise convention, all eleven
labels, and their limitations are documented in
[the orbifold, clockwork, and colour notation guide](docs/orbifold_notation.html).

## Generate everything

```bash
python3 -m pip install -r requirements.txt
python3 scripts/generate_all.py
```

This writes all seven GIFs and a machine-readable loop audit to `output/`.
Each generator can also be run separately:

```bash
python3 scripts/generate_time_glide.py
python3 scripts/generate_time_screw.py --order 3 --frames 60
python3 scripts/generate_time_screw.py --order 6 --frames 60
python3 scripts/generate_diagonal_relay.py --order 3
python3 scripts/generate_mixed_time_glide.py
python3 scripts/generate_glide_time_reversal.py
python3 scripts/generate_rotary_time_reversal.py
python3 scripts/generate_dihedral_choreography.py
```

## Generate the systematic catalog

```bash
python3 scripts/generate_catalog.py
```

This keeps the original seven-example gallery unchanged and writes a separate
catalog to `output/systematic_catalog/`: exact JSON, a flattened CSV, a readable
Markdown index, the selected representative manifest, four GIFs in `gifs/`,
and an independent loop audit.

The bounded enumeration covers phase moduli 2 through 12 using
crystallographic point groups, square-lattice translation characters, and
canonical reversible relays.  It is exhaustive inside that declared scope,
not a claim to implement all 275 groups of the Ke–Wu classification.  The
equivalence convention, decomposition labels, and deferred families are
spelled out in
[docs/systematic_catalog.md](docs/systematic_catalog.md).

Generate the two additional motif families with:

```bash
python3 scripts/generate_motif_variants.py
```

This writes 22 more audited loops to `output/motif_variants/`, giving three
visual realizations for each symmetry in the web gallery.

After generating the GIF catalog, create the web posters and seekable playback
proxies with:

```bash
python3 scripts/generate_posters.py
python3 scripts/generate_videos.py
```

The video step requires `ffmpeg` on `PATH`. It produces a 60-frame, 20 fps H.264
proxy for each GIF. These files support individual pause and phase seeking in
the browser; they do not replace the GIFs or their loop audits.

The base and catalog renders default to 600 x 600; the motif variants default
to 420 x 420.  All use 60 frames at 20 fps.  A frame count must be
divisible by each example's phase/sampling order so every fractional time
translation is an integer number of frames.  The `all` command therefore requires at least 12 frames, a
multiple of 12, and a canvas size divisible by 6.  GIF timing is stored in 10 ms units; non-exact requested
rates are rounded to the nearest representable delay and the CLI reports the
effective frame rate.

Color is part of the exact state-level equivariance data, not decoration: each
mixed generator acts through the permutation `rho` stated below.  Consequently,
a transformed frame agrees with the later frame after that palette permutation;
it need not agree as literal RGB pixels before the colors are permuted.  The
neutral guides are designed to be invariant without recoloring.  Raster
anti-aliasing can introduce subpixel discrepancies; the exact identities are
regression-tested on the continuous motif states.

## Initial three constructions

### Time glide: reflection plus half a period

Let `m(x, y) = (-x, y)` and normalize the loop period to one.  The generator is

```text
G: (x, y, t) -> (-x, y, t + 1/2),       G^2 = (identity, t + 1).
```

The two chiral kites occupy mirror-related cells and are half a cycle out of
phase.  Reflection alone and a half-period time shift alone both fail; their
combination succeeds.  The color representation is the transposition
`rho(G) = (turquoise coral)`.

### Time screw: rotation plus a fractional period

For `n = 3, 4, or 6`,

```text
S: (x, t) -> (R_(2 pi/n) x, t + 1/n),   S^n = (identity, t + 1).
```

The default is the canonical quarter-turn screw (`n=4`).  Four applications
give a full spatial turn and one full animation period.  The generator carries
the color cycle `(0 1 ... n-1)`.  A generic snapshot deliberately does not have
ordinary `C_n` rotational symmetry—the symmetry only appears through time.

### Diagonal relay: a non-product spacetime subgroup

Put three cells on a spatial circle and write `a` for a one-cell translation.
The generator is

```text
D: (x, t) -> (x + a, t + 1/3),          D^3 = (x + 3a, t + 1).
```

On the three-cell spatial torus, `x + 3a` is the identity.  Neither the
one-cell translation `(x + a, t)` nor the fractional time shift
`(x, t + 1/3)` is a symmetry, while their coupled operation is.  Thus the
symmetry subgroup is the diagonal `C3`, not a direct product of an independent
spatial `C3` and temporal `C3`.  Its color action is `(0 1 2)`.

Every individual ambient operation can of course be written formally as a
spatial map followed by a time map.  “Non-product” here means that those two
factors are not themselves members of the symmetry group.

## Four additional non-product actions

| Example | Coupled generator(s) | Distinguishing structure |
| --- | --- | --- |
| Mixed spatial–temporal glide | `(-x, y+b/2, t+T/2)` | One generator combines reflection, a spatial half-translation, and temporal translation by `T/2`. |
| Glide time reversal | `(x+a/2, y, -t)` | A non-split extension pairing a spatial half-translation with time-coordinate reversal. |
| Rotary time reversal `4'` | `(R_90 x, -t)` | `Q^2=R_180`; the resulting `C4` is not `C2 x C2`. |
| Dihedral spacetime action | `S=(R_120,t+T/3)`, `M=(mirror,-t)` | Nonabelian diagonal `D3`, with `MSM=S^-1`. |

The precise presentations, non-product proofs, color actions, and literature
links are in [docs/non_product_examples.md](docs/non_product_examples.md).

## Loop construction and verification

The renderer evaluates only

```text
t_k = k / N,  k = 0, ..., N - 1.
```

It never duplicates the `t=1` endpoint.  Every motion parameter is periodic,
and Pillow writes the Netscape loop extension with `loop=0` (infinite).  The
auditor then decodes the saved file and checks:

- the expected frame count;
- `loop == 0`;
- one uniform positive frame duration;
- distinct first and last frames, avoiding a seam pause;
- a last-to-first pixel change comparable to ordinary adjacent changes.

Run the check again at any time:

```bash
python3 scripts/verify_gifs.py output/*.gif --frames 60 --report output/loop_report.json
python3 -m unittest discover -s tests -v
```

The unit tests also verify the defining group equations directly on the
continuous motif states, including the endpoint identification `t=0 mod T`.

## Code map

- `animated_groups/groups.py` — exact group actions, color permutations, poses.
- `animated_groups/rendering.py` — motif art, frame sampling, GIF writer/auditor.
- `animated_groups/motif_variants.py` — disc and bar renderers for the original seven actions.
- `animated_groups/cli.py` — shared command-line interface.
- `animated_groups/catalog/` — exact enumeration, pattern recipes, catalog renderer, and motif variants.
- `scripts/` — small entry points for each requested animation.
- `scripts/generate_posters.py` — extracts a lossless first-frame WebP poster for each gallery GIF.
- `scripts/generate_videos.py` — transcodes each gallery GIF to a seekable H.264 playback proxy.
- `site-controls-v2.js` / `site-controls-v2.css` — physically versioned interactive gallery assets.
- `site.js` — backward-compatible GIF controller for stale pre-video gallery markup.
- `future-directions.html` — colour-group and forward-time census through six colours.
- `future-directions.js` / `future-directions.css` — generated census tables and report styles.
- `scripts/generate_color_forward_census.py` — validates the 68-record manifest and regenerates the census downloads.
- `data/color-forward-*` — pinned forward manifest, JSON census, and CSV audit tables.
- `clockwork-coloring-correspondence.html` / `.css` — the 51-row nontrivial orbifold-pair atlas, backed by 68 audited records, and its responsive styles.
- `scripts/generate_clockwork_coloring_correspondence.py` — validates the phase characters and regenerates the atlas, JSON, and 68 static plates.
- `data/clockwork-coloring-correspondence.json` / `output/clockwork-colorings/` — the pinned correspondence records and lossless WebP visualizations.
- `space-group-correspondence.html` / `.css` / `.js` — the 51-entry colouring/space-group atlas with classical names, UCL links, relative-cell presentations, and 17 one-colour audit notes.
- `scripts/generate_space_group_correspondence.py` — validates the 68 International-number mappings and exact lifted relations, then regenerates the atlas, JSON, and data plates.
- `data/space-group-correspondence.json` / `output/space-groups/` — the pinned polar-space-group records and deterministic unit-cell views.
- `tests/` — group-law, motif-equivariance, and GIF-loop regression tests.
- `docs/orbifold_notation.html` — guide to spatial orbifolds, clockwork phase marks, and colour notation.
- `docs/orbifold-notation.css` — responsive styles for the notation guide.
- `docs/non_product_examples.md` — presentations and decomposition arguments.
- `docs/systematic_catalog.md` — bounded scope, equivalence convention, and catalog tiers.

Related orbit-sum constructions appear in
[Choreographic Crystals](https://arxiv.org/abs/1407.5876) and the phase-decorated
space groups of [Padmanabhan et al.](https://arxiv.org/abs/1701.04088).

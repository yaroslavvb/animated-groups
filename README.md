# Animated spacetime groups

Small Pillow programs turn exact continuous colored-spacetime-group state
models into seamless, infinitely looping GIFs.  The original gallery contains
seven sparse motif scenes; a separate systematic catalog enumerates bounded
phase actions and experiments with four additional visual languages.

**Live gallery:** [yaroslavvb.github.io/animated-groups](https://yaroslavvb.github.io/animated-groups/)

The catalog is drawn from the looping/Floquet subset of the 2+1-dimensional
space-time groups classified by Ke and Wu in
[Two-Dimensional Space-Time Groups](https://arxiv.org/abs/2604.05619).  All seven
contain the pure period `(identity, T)`, which an ordinary GIF needs.
The paper's genuinely non-Floquet groups without any pure temporal period are
intentionally excluded: no finite GIF can represent them as an exact loop.

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

The default render is 600 x 600, 60 frames, and 20 fps.  A frame count must be
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

## The original three groups

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

## Four more non-product groups

| Example | Coupled generator(s) | Distinguishing structure |
| --- | --- | --- |
| Mixed time glide | `(-x, y+b/2, t+T/2)` | Reflection, spatial half-glide, and half-time are inseparable. |
| Glide time reversal | `(x+a/2, y, -t)` | A genuinely non-split glide/playback-reversal extension. |
| Rotary time reversal `4'` | `(R_90 x, -t)` | `Q^2=R_180`; the resulting `C4` is not `C2 x C2`. |
| Dihedral choreography | `S=(R_120,t+T/3)`, `M=(mirror,-t)` | Nonabelian diagonal `D3`, with `MSM=S^-1`. |

The precise presentations, non-product proofs, color actions, and literature
links are in [docs/non_product_examples.md](docs/non_product_examples.md).

## Why the GIFs loop cleanly

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
continuous motif states, including the hidden equality between phases zero and
one.

## Code map

- `animated_groups/groups.py` — exact group actions, color permutations, poses.
- `animated_groups/rendering.py` — motif art, frame sampling, GIF writer/auditor.
- `animated_groups/cli.py` — shared command-line interface.
- `animated_groups/catalog/` — exact enumeration, exports, pattern recipes, and catalog renderer.
- `scripts/` — small entry points for each requested animation.
- `tests/test_groups.py` — group-law and GIF-loop regression tests.
- `docs/non_product_examples.md` — presentations and decomposition arguments.
- `docs/systematic_catalog.md` — bounded scope, equivalence convention, and catalog tiers.

For more construction ideas, the orbit-sum viewpoint is closely related to
[Choreographic Crystals](https://arxiv.org/abs/1407.5876) and the phase-decorated
space groups of [Padmanabhan et al.](https://arxiv.org/abs/1701.04088).

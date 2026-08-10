# Systematic phase-action catalog

The generated catalog is an exhaustive **bounded** catalog, not a claim to
contain all 275 two-dimensional space-time groups.  It records nontrivial
graph homomorphisms into the isometry group of a periodic phase circle for
phase moduli `2` through `12`.

The phase target is

```text
D_n = <tau, rho | tau^n = rho^2 = 1, rho tau rho = tau^-1>,
tau: t -> t + 1/n,       rho: t -> -t.
```

Every finite phase isometry is stored exactly as `(shift/n, reverses)`, never
as a floating-point approximation.  The catalog currently has three tiers:

1. **Crystallographic point mechanisms.**  All nontrivial maps from the
   embedded planar point groups `C2`, `C3`, `C4`, `C6`, `D1`, `D2`, `D3`,
   `D4`, and `D6` into `D_n` are checked against their defining relations.
   Simultaneous conjugation in the phase target is quotiented out, while
   spatially meaningful domain generators are retained.
2. **Traveling square-lattice characters.**  All nonzero characters
   `Z^2 -> C_n` are recorded in a fixed lattice basis.  Inflated descriptions,
   such as `2/4` and `1/2`, are merged.  A square-lattice `D4` orbit key is
   included so axis, diagonal, and related directions can also be grouped
   geometrically.
3. **Reversible relays.**  The canonical `pm` construction maps a unit
   translation to `tau` and a mirror to `rho`.  It is represented on an
   `n`-cell torus and accompanied by its wallpaper-cover interpretation.

For the default range, the finite enumerator finds 465 target-conjugacy
classes before cross-modulus normalization.  Exact Fraction-valued images
merge those to 192 point rows; 265 normalized square-lattice characters and
11 reversible relays give 468 exported rows total.  A coarser movie
equivalence (allowing geometric normalizers and arbitrary time-origin shifts)
compresses the point tier further to 36 primitive mechanisms.  The machine
catalog intentionally retains the stricter convention and states it in its
metadata.

This separation matters.  Crystallographic point groups can produce primitive
phase-rotation orders only `1`, `2`, `3`, `4`, and `6`.  The other orders up to
`12` appear through translations, not through hidden high-order planar point
rotations.  The `phase_rotation_order` field records the order of the
orientation-preserving temporal subgroup.  The separate
`reduced_phase_order`/`frame_divisor` records the exact denominator of the
chosen phase origin, which can be larger for a time-reversing element.

## “Non-product” versus “non-split”

For a spatial group `H` and a nontrivial phase map `Theta`, the graph

```text
Gamma_Theta = {(h, Theta(h)) : h in H}
```

is not the product of an independent spatial symmetry and an independent
phase symmetry.  Its pure spatial subgroup is `ker(Theta)`, and it contains no
nontrivial pure phase element.

That statement is distinct from whether the exact sequence

```text
1 -> ker(Theta) -> H -> image(Theta) -> 1
```

splits abstractly.  For every finite point entry the exporter searches for an
actual subgroup complement and labels the result `direct_product`,
`split_semidirect`, `non_split`, or `trivial` when one factor is trivial.  A
graph can therefore be non-product as a spacetime subgroup even when this
abstract sequence splits.

For a periodic relay there are two further levels.  The finite torus quotient
has a split projection with trivial kernel, but its lift relative to the chosen
product-period lattice is non-split.  Both facts are stored rather than
collapsed into one ambiguous “nonsymmorphic” flag.  On relay rows,
`extension_type` refers to the wallpaper cover;
`quotient_projection_split=true` and `product_lattice_cover_split=false`
state the two levels directly.

## Four representative motif systems

The four catalog representatives use motif systems distinct from those in the
initial seven examples:

| Pattern | Catalog mechanism | Visual encoding |
| --- | --- | --- |
| Six-petal system | `C6`, rotation plus `T/6` | Six connected petals encode the order-six phase action about a rotation center. |
| Periodic-curve system | lattice translation plus `T/5` | Five periodic Bézier curves represent the five translation–phase classes. |
| Deformable-square system | diagonal `D4` action | Four curved edges realize an order-four time screw and reflection/time reversal. |
| Two-phase cellular system | diagonal half-lattice shift plus `T/2` | A scalar field represents the two phase classes on diagonally related torus cells. |

Every recipe is evaluated at `t = k/N` for `k=0,...,N-1`; the duplicate
endpoint is omitted.  The generated GIFs carry `loop=0`, and the decoded files
are checked for frame count, uniform duration, distinct endpoint samples, and
a regular last-to-first seam.

## Boundary of this release

This catalog does not yet enumerate arbitrary maps from all 17 wallpaper
groups, general subdirect products with independent pure-time kernels, color
stabilizer subgroups, or the non-Floquet groups that lack a pure temporal
period.  Those are genuine additional families.  The next rigorous wallpaper
layer should use verified affine sections and factor sets rather than copying
unaudited finite presentations.

The broader classification is Ke and Wu's
[Two-Dimensional Space-Time Groups](https://arxiv.org/abs/2604.05619).  The
phase-decorated/common-quotient construction is closely related to
[Padmanabhan et al.](https://arxiv.org/abs/1701.04088), and the orbit-based
visual construction to
[Choreographic Crystals](https://arxiv.org/abs/1407.5876).

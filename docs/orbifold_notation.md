# Candidate space-time orbifold notation

## Status of the notation

> **Only the Conway/rosette prefix is standard notation. The double-bracket
> time-monodromy decoration introduced here is our proposal. It is not standard
> or established Conway, IUCr, or space-time-group notation.**

The purpose of this notation is modest: give the animations in this repository
short labels that retain familiar spatial orbifold information while making an
intertwined action on animation time visible. It is designed to sit beside the
full affine formulas, not replace them.

Normalize the animation phase to

\[
\theta=t/T\in\mathbb R/\mathbb Z.
\]

Two isometries of the phase circle will be used:

\[
\tau_\alpha(\theta)=\theta+\alpha,
\qquad
\iota_\beta(\theta)=-\theta+\beta,
\]

with all phase parameters understood modulo one. Here `tau` advances phase,
whereas `iota` reverses playback and can then change its reference phase. On
the lifted time axis, `tau_1` is the full-period translation `U`; on the phase
circle it is the identity.

After quotienting lifted time by `U`, let `H` be the spatial projection and
let

\[
\Theta:H\longrightarrow \operatorname{Isom}(S^1)\cong O(2)
\]

be its phase monodromy. The double brackets list the images under `Theta` of a
chosen generating set for `H`; equivalently, the coupled action is the graph
of `Theta` on the phase circle.

The proposed syntax is

```text
Q ⟦g_v ↦ τ_a, h_w ↦ ι_b⟧
```

where:

- `Q` is a standard Conway orbifold or planar-rosette symbol for the spatial
  projection of the group;
- `g` and `h` are named spatial generators;
- an optional subscript such as `v` or `w` is the generator's fractional
  spatial translation, written in the stated lattice units;
- `g_v ↦ τ_a` lifts the spatial affine map
  `x ↦ R_g x + v` to `(x,theta) ↦ (R_g x + v,theta+a)`;
- `h_w ↦ ι_b` lifts `x ↦ R_h x + w` to
  `(x,theta) ↦ (R_h x + w,-theta+b)`.

Generators present in the Conway prefix but omitted from the double brackets
have identity time monodromy, `tau_0`. Spatial-vector subscripts are measured
in the lattice basis used by the accompanying formula. They are omitted when
the spatial translation is zero.

The notation records geometric space-time symmetry only. It deliberately
omits the palette permutations used to make equivariance visible in the GIFs.

## Standard spatial prefixes

The following prefix meanings are standard Conway or Conway-style rosette
notation; none of their symbols is being redefined here.

- `n•` is the cyclic planar rosette with an `n`-fold rotation about a fixed
  point. For example, `4•` is the spatial `C4` rosette.
- `*n•` is the dihedral planar rosette with an `n`-fold rotation and mirrors
  through the fixed point. The limiting case `*1•` has one mirror and no
  nontrivial rotation.
- `∞∞` is the translation-only frieze group, with one independent spatial
  translation.
- `o` is the translation-only wallpaper group. Its quotient is a torus, and
  it has two independent spatial translations.
- `××` is the glide-reflection wallpaper orbifold, whose quotient has two
  crosscaps. It is the Conway symbol for the spatial `pg` type.

The bullet in `n•` and `*n•` indicates the fixed point of a non-translational
planar rosette. It also avoids replacing these planar symbols by the related
spherical orbifold signatures `nn` and `*nn`.

For a dihedral prefix `*n•`, choose a rotation `r` and a mirror `m`. Its spatial
relations are

\[
r^n=1,
\qquad m^2=1,
\qquad mrm=r^{-1}.
\]

The proposed decorations respect these relations because

\[
\iota_\beta\tau_\alpha\iota_\beta=\tau_{-\alpha},
\qquad \iota_\beta^2=1.
\]

Consequently, `*n• ⟦r ↦ τ_1/n, m ↦ ι_0⟧` compactly records both the
spatial dihedral relation and its phase-reversing lift. A decoration is valid
only when all relations in the chosen spatial presentation continue to hold
modulo the spatial lattice and `tau_1`.

## The eleven gallery labels

Write

```text
U: (x,y,t) ↦ (x,y,t+T)
X: (x,y,t) ↦ (x+a,y,t)
Y: (x,y,t) ↦ (x,y+b,t)
```

for a full animation period and the displayed spatial lattice translations.

### 1. C2 time glide

```text
Proposed label: *1• ⟦m ↦ τ_1/2⟧
G: (x,y,t) ↦ (-x,y,t+T/2)
G² = (1,T) = U
```

The standard prefix says that the spatial projection is a single mirror. The
proposed decoration says that its lift advances the animation by half a
period. Neither operation is being represented by a new meaning for `*`.

### 2. C4 time screw

```text
Proposed label: 4• ⟦r ↦ τ_1/4⟧
S: (x,t) ↦ (R_(pi/2)x,t+T/4)
S⁴ = (1,T) = U
```

The prefix is a standard fourfold cyclic rosette; the decoration distinguishes
the time screw from an ordinary static `C4` rotation.

### 3. C3 diagonal relay

```text
Proposed label: ∞∞ ⟦a ↦ τ_1/3⟧
D: (x,t) ↦ (x+a,t+T/3)
D³: (x,t) ↦ (x+3a,t+T)
```

The spatial projection is a one-directional translation group. The order
three in the gallery name refers to the phase relay, not to a spatial
threefold rotation.

### 4. Mixed space-time glide

```text
Proposed label: ×× ⟦g_(0,b/2) ↦ τ_1/2⟧
G: (x,y,t) ↦ (-x,y+b/2,t+T/2)
G² = YU
```

The standard `××` prefix identifies the glide-reflection spatial projection.
The vector subscript and the proposed phase decoration retain the particular
half-cell, half-period lift used by the animation.

### 5. Glide time reversal

```text
Proposed label: ∞∞ ⟦q_(a/2,0) ↦ ι_0⟧
Q: (x,y,t) ↦ (x+a/2,y,-t)
Q² = X
QUQ⁻¹ = U⁻¹
```

The spatial projection is translational, while the proposed `iota_0`
decoration records reversal of the animation phase. The square is a full
spatial translation rather than the identity.

### 6. 4-prime rotary time reversal

```text
Proposed label: 4• ⟦r ↦ ι_0⟧
Q: (x,t) ↦ (R_(pi/2)x,-t)
Q² = R_pi
Q⁴ = 1
```

`4•` is the standard spatial rosette. The double brackets, rather than a
redefinition of the Conway prefix, distinguish this reversing lift. The
familiar name `4-prime` comes from magnetic point-group notation, not Conway
orbifold notation.

### 7. D3 dihedral choreography

```text
Proposed label: *3• ⟦r ↦ τ_1/3, m ↦ ι_0⟧
S: (x,t) ↦ (R_(2pi/3)x,t+T/3)
M: (x,t) ↦ (m x,-t)
S³ = U,  M² = 1,  MSM = S⁻¹
```

Here `*3•` already supplies the standard spatial `D3` rosette. The two
decorations give its rotation and mirror the matching forward and reversing
phase actions.

### 8. C6 kinetic-iris time screw

```text
Proposed label: 6• ⟦r ↦ τ_1/6⟧
S: (x,t) ↦ (R_(pi/3)x,t+T/6)
S⁶ = (1,T) = U
```

This is the sixfold analogue of the `4•` time screw.

### 9. C5 wave-loom relay

```text
Proposed label: o ⟦a ↦ τ_1/5⟧
W: (x,t) ↦ (x+a,t+T/5)
W⁵: (x,t) ↦ (x+5a,t+T)
b ↦ τ_0
```

The wave loom lives on a two-directional translation lattice, so its standard
prefix is `o`. Only the `a`-direction participates in the five-phase relay.
The inert `b` generator has identity time monodromy and would normally be
omitted under the proposed convention; it is written above to make that fact
explicit.

### 10. D4 elastic-square choreography

```text
Proposed label: *4• ⟦r ↦ τ_1/4, m ↦ ι_0⟧
S: (x,t) ↦ (R_(pi/2)x,t+T/4)
M: (x,t) ↦ (m x,-t)
S⁴ = U,  M² = 1,  MSM = S⁻¹
```

The standard prefix gives the spatial `D4` rosette; the proposed monodromy
decoration records the quarter-period screw and playback-reversing mirror.

### 11. C2 centered-lattice liquid cells

```text
Proposed label: o ⟦ℓ_(a/2,b/2) ↦ τ_1/2⟧
L: (x,y,t) ↦ (x+a/2,y+b/2,t+T/2)
L² = XYU
```

The standard `o` prefix gives the translation-only spatial torus. The proposed
decoration singles out the diagonal centered-lattice lift that exchanges the
two animation phases.

## Limits and equivalences

These labels describe the selected mechanisms, but they are not a canonical
classification of space-time groups.

1. **A lattice basis is still required.** Vector subscripts change under a
   change of basis, and `o` alone does not choose generators `a` and `b`.
2. **Generator choices matter.** The same group can have different spatial
   presentations. Changing generators can change every displayed decoration
   without changing the underlying space-time group.
3. **Origins and reference phases matter.** Moving the spatial origin or the
   zero of time changes representatives of glide vectors and `iota_b` actions.
4. **Cocycle representatives can be equivalent.** Fractional affine and phase
   data should ultimately be compared modulo lattice shifts, coboundaries,
   origin changes, and automorphisms of the chosen spatial presentation.
5. **The prefix is the spatial projection.** It need not equal the pure spatial
   subgroup of a non-product space-time group. This distinction is essential
   for the diagonal and glide examples.
6. **Palette actions are absent.** Color permutations in the renderer are
   representation data for the motifs, not part of these geometric labels.
7. **Playback reversal is not automatically quantum time reversal.** In the
   GIFs, `iota` means the literal reversal of the phase coordinate. A quantum
   realization may additionally require an antiunitary action.

A canonical notation for all 275 groups in the 2+1-dimensional classification
would need, at minimum, a conventional space-time Bravais basis, a fixed
presentation for every spatial or magnetic point group, canonical cocycle
representatives, and explicit equivalence rules. The double-bracket notation
does not yet provide those choices and should not be advertised as doing so.

## References

- John H. Conway and Daniel H. Huson, [*The Orbifold Notation for
  Two-Dimensional Groups*](https://faculty.washington.edu/moishe/branko/Uniform%20polyhedrals/Conway%20Huson%20Orbifolds.pdf),
  *Structural Chemistry* **13** (2002), 247–257. This is the source for the
  standard orbifold characters and their geometric interpretation.
- Chenhang Ke and Congjun Wu, [*Two-Dimensional Space-Time Groups:
  Classification and Applications*](https://arxiv.org/abs/2604.05619), 2026.
  Their affine action `(R r + u, s t + tau)` and examples of time glides,
  glide time reversal, and time screws motivate the data recorded inside the
  proposed brackets.
- Vincent S. Liu, Brian K. VanLeeuwen, Jason M. Munro, Haricharan Padmanabhan,
  Ismaila Dabo, Venkatraman Gopalan, and Daniel B. Litvin,
  [*Spatio-temporal symmetry — crystallographic point groups with time
  translations and time inversion*](https://doi.org/10.1107/S2053273318004667),
  *Acta Crystallographica A* **74** (2018), 399–402. Their notation couples
  spatial operations to time translations and time inversion, providing an
  important crystallographic precedent distinct from the proposal here.
- Shenglong Xu and Congjun Wu, [*Space-time crystal and space-time
  group*](https://arxiv.org/abs/1703.03388), *Physical Review Letters* **120**
  (2018), 096401. This paper defines intertwined space-time groups, time-screw
  and time-glide operations, and glide time reversal.

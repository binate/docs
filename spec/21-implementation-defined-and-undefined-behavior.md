# 21. Implementation-defined, Unspecified, and Undefined Behavior

> **Status:** normative · **Maturity:** contracts Stable (one open GAP: byte order — §21.4)  
> **Rule-ID prefix:** `behavior`

This chapter is the **single collected catalogue** of every point where the
language deliberately leaves a behavior **unpinned, parameterized, or
unconstrained** — a reverse index in the spirit of the C standard's Annex J.
**Every item has its normative home in an earlier chapter**; this chapter does
not re-define them. It **classifies** each item and **points back** to its home
(rule-ID + section), so a reader can see the whole behavior-latitude surface in
one place and a conformance test can cite a single catalogue entry.

`behavior.catalogue` — Where this chapter and an item's home chapter could be
read to differ, **the home chapter governs** the precise rule; this chapter is
authoritative only for the **classification** and the cross-mode-agreement
constraint (§21.3).

## 21.1 The behavior-latitude taxonomy

`behavior.taxonomy` — Each catalogued behavior falls into one of these classes
(defined in Ch.3 and used consistently):

- **target-invariant** — the same on every target (e.g. a managed-slice is
  *exactly* four words; field order; the 16-byte by-value cutoff).
- **target-parameterized** — determined by the compilation target's `TargetInfo`
  (pointer/int width, alignment), fixed once the target is fixed (e.g. the
  *absolute* size of a managed-slice; struct offsets).
- **implementation-defined** — the implementation **shall** fix and document a
  choice; **both execution modes must agree** on it for a target (§21.3, §21.4).
- **unspecified** — the implementation may choose, need not document, and the
  choice is **not** a target-pinned promise (§21.5).
- **undefined** — outside the language's guarantees entirely; **user error**, not
  a promised trap (§21.6).
- **backend-private** — an internal realization detail observable by neither a
  conforming program's result nor the cross-mode contract (e.g. whether a
  reference-count adjustment is inlined or a library call).

The implementation-defined class carries the extra **cross-mode-agreement** axis
the dual-mode design needs: a target-parameterized-but-fixed choice on which the
two modes **must agree** is distinct from a truly **backend-private** one.

## 21.2 What is *not* here

`behavior.not-undefined` — Binate's **undefined** class is **deliberately narrow**
— essentially the raw-pointer / `unsafe_*` / `bit_cast` / refcount-aliasing escape
hatch (§21.6). In particular the following are **defined**, not undefined, and are
catalogued under §21.7–§21.8, **not** §21.6:

- integer `+`/`-`/`*` overflow → **two's-complement wraparound** (§13.3);
- division / remainder by zero and signed `MIN / -1` → **defined panics** (§13.4);
- index / slice out of bounds → a **defined panic** (§13.9);
- shift count ≥ width (or negative) → a **defined** result (§13.5);
- float operations including division by zero and `NaN` comparisons →
  **defined** IEEE-754 (§13.3, §13.6);
- out-of-range / `±Inf` / `NaN` float→integer conversion → **defined saturation**
  (§21.7).

## 21.3 The cross-mode agreement rule (the master ABI invariant)

`behavior.cross-mode` _(normative)_ — Where a target supports **both** execution
modes, the **compiled** and **interpreted** modes **shall** agree **exactly** on
the observable layout and behavior of every program on that target — including
every **implementation-defined** choice in §21.4 (notably **word size** and every
type's byte layout). This is the **master ABI invariant**; any layout divergence
is **silent data corruption** (§7.13.13 `type.layout.keystone`, §19.3
`exec.contract`).

`behavior.cross-mode.scope` — The agreement binds the **result** of every
**defined** operation. **Two** things lie outside it (and so **may** differ across
modes): an **undefined** operation (§21.6), which is unconstrained; and the
observable **form** of a **defined abort** whose form is mode/target-dependent
(§21.5, e.g. nil-interface dispatch) — there, the *fact* of the abort is
guaranteed but not its precise form. A divergence on the **defined** result of any
**defined** operation is a **non-conformance** (§21.9), never sanctioned latitude.

## 21.4 Implementation-defined behavior

`behavior.impl-defined` — The implementation **shall** fix and document each of
the following per target; **both modes shall agree** (§21.3). Structure is stated
**target-invariantly** (a managed-slice is *exactly* four words) while absolute
magnitudes are **parameterized** by `TargetInfo`.

| Item | Class | Home |
|------|-------|------|
| Pointer / `int` / `uint` width (the **word size** `W`) — 4 or 8 bytes | impl-defined (modes must agree) | §7.13.1 `type.layout.target-info`; §7.13.2 `type.layout.scalar` |
| Scalar alignment; `MaxAlign` clamp | target-parameterized | §7.13.1, §7.13.2 `type.layout.scalar` |
| Struct field **offsets** and total **size** (the field **order** and layout **algorithm** are target-invariant) | target-parameterized | §7.13.3 `type.layout.struct` |
| Raw slice = 2 words `{data, len}`; managed-slice = 4 words `{data, len, backing, backingLen}` | structure target-invariant; sizes parameterized | §7.13.5–7.13.6 `type.layout.slice-raw`, `type.layout.slice-managed` |
| Interface value = 2 words `{data, vtable}`; function value = 2 words `{vtable, data}` (**reverse** order) | structure target-invariant; sizes parameterized | §7.13.8 `type.layout.iface-value`, §7.13.9 `type.layout.func-value` |
| Management header = 2 words `{refcount, free_fn}` at a negative offset | structure target-invariant; size parameterized | §7.13.7 `type.layout.header` |
| By-value parameter cutoff (≤ 16 bytes by value, > 16 by reference) | target-invariant threshold | §7.13.11 `type.layout.byval-cutoff` |
| The **immortal sentinel** refcount value (a deeply-negative count) | impl-defined; currently unfinalized | §18.2 `mem.immortal`; §7.13.7 `type.layout.immortal` |
| Panic **message text**, **exit code**, and diagnostic **output stream** | impl-defined (modes must agree) | §17.4 `prog.terminate`; §17.5 `prog.panic.defined` |
| **Symbol decoration** / name mangling (observable in consequence; the scheme is informative) | impl-defined | §16.6 `pkg.identity`; Annex B |

`behavior.impl-defined.endianness` _(Draft — OPEN GAP)_ — The **byte order**
(endianness) of multi-byte scalars is observable through `bit_cast` and the
representation built-ins (Ch.15), yet the layout layer currently leaves it
**unconstrained** (`TargetInfo` carries no endianness field) — §7.13.12
`type.layout.byte-order`. The spec **must close** this gap. The recommended
resolution is to pin endianness as **implementation-defined** (so the two modes
**must agree** per target) and add an endianness field to `TargetInfo`, making
layout-dependent constant emission well-defined. **This is not yet ratified** — it
is one of two items in this chapter still awaiting a decision (`claude-todo.md`).

`behavior.impl-defined.optional-scalars` _(Draft — reconciliation gap)_ — The
design treats the **64-bit and floating-point** scalar types (`int64`, `uint64`,
`float32`, `float64`) as **optional**, available subject to target/hardware
support (the hosted-vs-freestanding conformance split, §2, §19.6). The authored
type chapter (§7.2) currently lists them among the predeclared scalars
**unconditionally**, with no availability caveat — so this latitude has **no
normative home** yet. The gap is to be closed by either adding a target-availability
caveat to §7.2 (recommended) or dropping the optionality from the design; **not
yet resolved** (`claude-todo.md`).

## 21.5 Unspecified behavior

`behavior.unspecified` — The following are **unspecified**: an implementation may
choose freely, need not document the choice, and the choice is **not** a
target-pinned promise. None is observable in the result of a conforming program.

| Item | Home |
|------|------|
| Cross-operand side-effect order in an assignment beyond "RHS before LHS designator" (which **is** pinned) | §14.4 `stmt.assign.eval-order` |
| The order in which a scope's managed locals are released at scope exit (not observable; the impl uses declaration order) | §18.4 `mem.scope-exit` |
| Whether a **move** is applied — only **intermediate** refcounts (as read by reflection) may differ; *when* an allocation is freed is identical | §18.6 `mem.move.optimization`; §18.5 `mem.return` |
| The observable **form** of a defined abort whose form is mode/target-dependent — nil-interface dispatch faults silently in compiled native code but diagnoses-and-exits under the VM (the *fact* of the abort is defined) | §19.5 `exec.divergence`; §17.5; §11.11 `iface.dispatch.nil` |
| The **contents** of inter-field **padding** bytes over a value's lifetime (distinct from allocation, where a fresh payload is **zero-initialized** — §18.2, §15.2) | §7.13.3; §18.2 `mem.header` |
| Whether a reference-count adjustment is **inlined** or realized as a runtime **call** (backend-private; the net effect is fixed) | §18.7 `mem.no-leak` |
| Whether identical **read-only static literals** share one storage location (sound because they cannot be mutated) | §13.10 `expr.composite`, `expr.composite.slice` |

## 21.6 Undefined behavior

`behavior.undefined` — The following are **undefined**: **user error**, outside
the language's guarantees, **not** a promised trap. Behavior is unconstrained and
**may differ** across modes and within a mode (§21.3 places undefined operations
outside the cross-mode agreement). An implementation **shall not** suppress a
reference-count release to "rescue" a use-after-free — doing so trades a
detectable fault for a silent leak, which is worse (§18.7).

| Item | Home |
|------|------|
| Using a **raw borrow** (`*T`, `*[]T`) after the managed value it borrows from is released — a **use-after-free** | §18.7 `mem.raw-uaf` |
| Dereferencing a **dangling** `*T`, or breaking refcount invariants through **raw aliasing** | §18.7 `mem.cycles`, `mem.determinism` |
| `bit_cast(T, x)` out of contract — reinterpreting between different sizes, or in a way that violates a type's invariants | §8.6 `conv.bit-cast`; §15.3 `builtin.bit-cast` |
| `unsafe_div` / `unsafe_rem` on a **zero** or signed **`MIN / -1`** divisor (the guard-free `/` and `%`) | §13.4 `expr.arith.unsafe`; §15.8 `builtin.internal` |
| `unsafe_index(c, i)` with an **out-of-range** index (the bounds-check-free indexed access) | §15.6 `builtin.unsafe-index`; §13.9 `expr.index.bounds` |
| Behavioral **mode-dependence** of a defined operation **beyond** the one-indirection cost of crossing modes (any such dependence is otherwise a defect, §21.9) | §19.4 `exec.interop.funcval` |

> _Note._ A reference **cycle** of managed values **leaks** — the one "leak" a
> conforming program may exhibit — and is **user error**, not undefined behavior
> (§18.7 `mem.cycles`). Raw pointers are the sanctioned escape hatch for breaking
> a cycle.

## 21.7 Explicitly well-defined carve-outs

`behavior.well-defined` — Two areas where a C-family language would leave behavior
implementation-specific or undefined are, in Binate, **pinned to a single defined
result identical across every backend and the VM** — deliberately closing a
hardware-divergence gap.

- **Out-of-range / `±Inf` / `NaN` float→integer conversion saturates**
  (`conv.cast.float-int-saturation`, §8.5). The ratified contract (2026-06-12):
  a value above the target integer type's range (including `+Inf`) → that type's
  **MAX**; below its range (including `-Inf`) → its **MIN** (`0` for unsigned);
  **`NaN` → 0**; an in-range value truncates toward zero. This is normalized once
  in shared IR-gen so every backend and the VM inherit it, refining Go (which
  leaves the result implementation-specific but panic-free). **Realized and
  conformant** in the current tree (`conformance/732_float_int_saturation`).
- **Defined arithmetic** (§13.3–§13.6): integer `+`/`-`/`*` **two's-complement
  wraparound**; integer `/` truncates toward zero and `%` takes the sign of the
  dividend; **defined** over-shift (`0` for logical, sign-fill for arithmetic
  `>>`; not hardware-masked); IEEE-754 float arithmetic (division by zero →
  `±Inf`/`NaN`, no panic) and **defined** `NaN` comparison (`<`/`==` false, `!=`
  true).

## 21.8 The closed set of defined panics

`behavior.panics` — A **small, closed set** of conditions are **defined,
non-recoverable runtime panics** — they are **not** undefined behavior, cannot be
caught, and abort the program with an implementation-defined diagnostic and exit
code (§17.4, §21.4). The set (normative home §17.5 `prog.panic`):

| Defined panic | Home |
|---------------|------|
| Index / slice out of bounds (on a length-carrying value) | §13.9 `expr.index.bounds` |
| Integer division / remainder by **zero** | §13.4 `expr.arith.divzero` |
| Signed **`MIN / -1`** overflow | §13.4 `expr.arith.minover` |
| `make_slice` with a **negative** length | §15.2 `builtin.make-slice` |
| Dispatch through a **nil interface value** — defined abort; observable *form* is mode/target-dependent (§21.5) | §11.11 `iface.dispatch.nil` |
| `panic(msg)` — defined abort; **currently realized inconsistently** (§21.9) | §15.7 `builtin.panic` |

A panic-triggering operand that is a **compile-time constant** is rejected at
compile time instead of producing a runtime panic (§17.5, §13.4).

## 21.9 Tracked non-conformances (defects ≠ unstable rules)

`behavior.defects` — A known **miscompile** makes the **implementation**
non-conformant; it does **not** make the **language rule** unstable. The spec
states each rule normatively in its home chapter; the catalogue of current
non-conformances — with `claude-todo.md` cross-references and per-mode xfail
status — lives in **Annex C**. These **shall not** be read as sanctioned
unspecified/undefined latitude. The principal current items (each
defined-in-intent, defective-in-realization) include:

- **`panic(msg)` realized inconsistently** across modes — the bytecode VM treats
  it as a **no-op** (no abort, no message; control falls through) and the compiled
  backend **aborts but discards the message**; the intended behavior is to abort
  **with** the message in both modes (§15.7, §17.5, §19.5; `builtin.panic.vm-noop`).
- **Taking the address of a literal** (`&5`) is **not diagnosed** — a
  *missing-diagnostic* defect, since a literal has no storage and the construct is
  **intended to be rejected** (§13.8 `expr.unary.addr-literal`). It is a
  constraint-not-enforced defect, **not** sanctioned undefined behavior.
- **Tagless-`switch` case expressions are not type-checked** to be boolean (a
  non-boolean `case` is wrongly accepted); the intended rule is boolean cases
  (§14.10 `stmt.switch.tagless-bool`).
- **Composite-literal defects**: indexed array-literal elements silently
  miscompiled; inferred-length `[...]T{}` unimplemented; positional struct
  elements not **assignability**-checked (§13.10). (Array and struct **over-count**
  — more elements than the length / field count — is now **rejected**.)
- `==`/`!=` on **struct/array** values rejected ("not yet implemented") though the
  intended rule is element-wise comparison (§13.6 `expr.compare.aggregate`). (Slices,
  interface values, and function values are **by design** never comparable — a
  Constraint, not a defect.)
- `make` / `sizeof` / `alignof` of an **opaque** type from another package not
  gated (§15.2 `builtin.opaque-gate`).
- The interpreter's **`_Package()` reflection accessor** for non-built-in packages
  (§20.3 `pkg0.reflect.vm-gap`) and a **cap** on the argument count of a cross-mode
  function-value call (the general cross-mode dispatch mechanism is in place,
  §19.5).
- The **float-`NaN`** corner of the canonical `Compare`/`Hash` impls
  (§20.1 `pkg0.lang.float-nan`).

> _Note (permanent carve-out, not a defect)._ The bytecode VM performs **no**
> foreign-function calls: `__c_call` is a **compiled-mode-only** facility and will
> not be interpreted (§16.9, §19.5). This is a deliberate, permanent boundary, not
> a pending fix.

# 20. Intrinsic (Tier-0) Packages

> **Status:** mixed · **Maturity:** lang Stable; rt Draft (gated); reflect Draft; testing Provisional  
> **Rule-ID prefix:** `pkg0`

A small set of **tier-0 intrinsic packages** are part of the **core language**:
they are bound to the language itself rather than layered on top of it, and this
specification defines their normative `.bni` surfaces. They are distinguished
from the **standard library** (tier 1), which is a separate, dependent *sibling*
specification — still in early design and **not** defined here; the core spec
only reserves a pointer to it (Ch.1). `pkg/bootstrap` is temporary scaffolding
and is **not** part of the language.

`pkg0.tier0` — The tier-0 packages are exactly four, each carrying its **own**
maturity status:

| Package | Role | Maturity |
|---------|------|----------|
| `pkg/builtins/lang` | canonical interfaces + primitive impls (§20.1) | fairly mature → mostly **Stable** |
| `pkg/builtins/rt` | the runtime contract (§20.2) | **Draft** — gated on the `pkg/rt` review |
| `pkg/builtins/reflect` | reflection / introspection (§20.3) | **Draft** — incomplete |
| `pkg/builtins/testing` | testing support + the `*_test.bn` convention (§20.4) | **Provisional** |

Because tier 0 is not uniformly mature, several sections below are **Draft** or
**Provisional** — specified-in-intent and marked honestly (§4.3).

> _Rationale (informative)._ Binate targets environments with no console, no
> filesystem, no process model, and no threads. A core specification free of
> standard-library and I/O assumptions stays implementable on a bare-metal
> target; the standard-library spec then layers selectively per target. This is
> why the spec separates **hosted** from **freestanding** conformance (Ch.2,
> §19.6) and why the bar for "belongs in the standard library, not the core" is
> high. See Annex D.

## 20.1 `pkg/builtins/lang` — canonical interfaces and primitive impls

`pkg0.lang.surface` — The package `pkg/builtins/lang` is the **canonical-interface
home** and the **primitive-impl carve-out**: it declares the language's four
canonical interfaces and ships the implementations of those interfaces for every
**universe primitive** type. It is the **normative home** for the canonical
interface signatures referenced from §11. Importing it is explicit
(`import "pkg/builtins/lang"`); there is no auto-import of the interface
**types** (but see `pkg0.lang.force-load` for the methods).

The four interfaces are:

```
interface Stringer  { String() @[]char }
interface Comparable { Compare(other Self) int }
interface Orderable : Comparable {}
interface Hashable  : Comparable { Hash() uint }
```

`pkg0.lang.stringer` — `Stringer` is the canonical "printable representation"
interface. A `String()` implementation returns a **freshly-allocated
managed-slice** (`@[]char`); the **caller owns** the result (it is not a borrow
of static storage). It is used by standard-library formatting paths and by user
code wanting polymorphic printing.

`pkg0.lang.comparable` — `Comparable.Compare(other Self)` returns `0` **iff** the
two values are considered equal, and a nonzero `int` otherwise. At this level the
**sign and magnitude** of a nonzero result carry **no** meaning — equality is the
only contract. (Total order is `Orderable`'s additional promise.)

`pkg0.lang.orderable` — `Orderable` is a **zero-method** extension of
`Comparable`. The extension **is** the assertion: declaring `impl T : Orderable`
asserts that `T`'s `Compare` satisfies a **total order** (transitivity,
antisymmetry, sign-consistency), which the compiler **cannot** verify. A consumer
wanting `<` writes `a.Compare(b) < 0` (and the analogous forms for the other
relations).

`pkg0.lang.hashable` — `Hashable` extends `Comparable` with `Hash() uint`. The
hash **shall** be consistent with `Compare`'s equality: if `a.Compare(b) == 0`
then `a.Hash() == b.Hash()`. It is intended for associative containers (Map, Set)
once those land in the standard library.

`pkg0.lang.carve-out` _(Constraint)_ — `pkg/builtins/lang` is the **only** package
permitted to declare methods (and thus interface implementations) whose receiver
is a **universe primitive** type (`int`, `bool`, the sized integers, the floats,
…). A method declaration with a universe-primitive receiver in any other package
**shall** be rejected. (The type-checker gates this with an internal
`AllowUniverseRecv` flag enabled only for this package.) A user **struct** opts
into a canonical interface the ordinary way, with an explicit bodyless
`impl Point : Comparable` (its methods declared separately, §11.3) — there is no
auto-derivation.

`pkg0.lang.force-load` — A program may call a **primitive's** canonical method
**without importing** `pkg/builtins/lang`: the compiler **force-loads** the
package so the carve-out impls attach to the primitive types, and so
`(42).String()` resolves with no import. Naming the **interface type** itself
(e.g. a `*Stringer` parameter or an `impl T : Comparable` clause) still **requires**
the explicit `import "pkg/builtins/lang"`. (Conformance: `654`–`656` exercise the
no-import method calls; `658` pins that naming the interface type without the
import is an error.)

`pkg0.lang.self-safety` — `Comparable.Compare(other Self)` mentions `Self` in a
**non-receiver** (parameter) position, so — per the object-safety rule of §11 —
it is callable **only through a generic constraint** (`[T Comparable]`, where `T`
is statically known), **not** through a `*Comparable` interface value (which would
require type-erased dispatch). Object-safety is **per method**: `Hashable.Hash()`
does **not** mention `Self`, so `Hash` **is** callable through a `*Hashable`
interface value even though `Compare` is not.

### Primitive implementations and the float-NaN total order

`pkg0.lang.primitives` — `pkg/builtins/lang` ships, for **all thirteen** universe
primitive scalar types (`int`, `int8`, `int16`, `int32`, `int64`, `uint`,
`uint8`, `uint16`, `uint32`, `uint64`, `bool`, `float32`, `float64`),
implementations of `Stringer`, `Comparable`, `Orderable`, and `Hashable`. For the
integer and `bool` types these are fully **Stable**: `Compare` yields `-1`/`0`/`1`
by natural ordering, and `Hash` is the (zero-extended) bit pattern.

`pkg0.lang.float-nan` _(Stable)_ — The **float** `Compare`/`Hash` impls realize a
self-consistent **total order** at `NaN`:

- `float32`/`float64` `Compare` is the **IEEE total order**: every `NaN` — any
  sign, any payload — sorts **above** every finite value **and** above `+Inf`, and
  all `NaN`s compare **equal** to one another, so a sequence `-Inf, …finites…,
  +Inf, NaN` is monotonic. Among non-`NaN` values the order is the IEEE-754
  `totalOrder` predicate on the bit pattern, which additionally distinguishes
  `-0.0 < +0.0`. This **deliberately differs** from the §13 **operator**
  comparison (IEEE-754 *ordered* for `<`/`==`, *unordered* for `!=`): a reader
  **shall not** assume `a.Compare(b) < 0` tracks `a < b` when a `NaN` is involved.
- Because `Compare` folds every `NaN` into one equivalence class, the float `Hash`
  **canonicalizes** any `NaN` to a single value (the hash of the canonical quiet-
  `NaN` bits), so distinct `NaN` bit patterns hash **identically** — satisfying
  `pkg0.lang.hashable`'s consistency requirement (`Compare(a, b) == 0` ⇒
  `Hash(a) == Hash(b)`). Non-`NaN` values still hash by bit pattern; the
  `-0.0 < +0.0` ordering keeps signed zeros consistent (their bits already differ).

> _Note._ The `Self` type, the canonical-interface signatures, the carve-out, and
> the float-`NaN` corner above are all DECIDED. The `cmd/bni` (bytecode-VM)
> compile path's force-loading of `pkg/builtins/lang` is a tracked follow-up
> (Annex C); the compiled path is conformant.

## 20.2 `pkg/builtins/rt` — the runtime contract

> _Draft — GATED. The normative member list is **not** authored here._

`pkg0.rt` — `pkg/builtins/rt` is the **runtime contract**: the minimal set of
runtime primitives a generated program may call — allocation and freeing,
reference-count increment/decrement (§18), `box`, bounds-checking, process exit,
managed-slice construction, and the **runtime function manifest** referenced from
§19.4. Its surface is **split hosted vs freestanding**, and the manifest is
**actively shrinking**.

Authoring its normative member list is **gated on the `pkg/rt` review** — a
prerequisite that **classifies** each current member as (a) genuine
language-runtime that stays, (b) standard-library material that moves out, or (c)
compiler-internal scaffolding with **no** `.bni` surface (the present `.bni`
mixes true runtime primitives with internal helpers explicitly marked "not a real
linkable symbol", e.g. the call-shims and destructor/free-fn trampolines). Until
that classification lands, §20.2 is a **placeholder**: the runtime's *observable*
contracts are stated where they are used — the management header and immortal
sentinel (§18.2, §7.13.7), the no-leak guarantee and cross-mode dtor handle
(§18.7, §19.4), and the defined-panic diagnostics (§17.5) — and this section will
enumerate the manifest once the review fixes it.

## 20.3 `pkg/builtins/reflect` — reflection and introspection

> _Draft — incomplete. The shape below is Stable; richer type metadata is a later
> phase._

`pkg0.reflect.surface` — `pkg/builtins/reflect` is **interface-only** (it has no
`.bn` body and, today, no exported functions of its own). It exposes a compiled
package's reflective metadata through three types:

```
type Package      struct { Name *[]readonly char; Functions *[]@FunctionInfo; Globals *[]@GlobalInfo }
type FunctionInfo struct { Pkg @Package; Name *[]readonly char; Value *uint8;
                           RetbufSize int; ParamSlots int; Sig *[]readonly char }
type GlobalInfo   struct { Name *[]readonly char; Addr *uint8 }
```

`Package.Name` is the package's **full import path** (not the last segment).
`Functions` lists one `FunctionInfo` per `.bni`-exported **non-extern** function
in declaration order, **followed by** the package's own synthesized `__Package`
accessor as the last entry (so a package is reflectable through its own table).
`Globals` lists one `GlobalInfo` per `.bni`-exported package-level `var`.
`FunctionInfo` carries **no** structured type information — only scalars plus the
**fully-qualified** name and an **opaque** mangled signature string (`Sig`), which
no consumer parses; `Value` points at the function-value handle, and `RetbufSize`
is the load-bearing scalar-vs-aggregate return discriminator — the aggregate
retbuf byte size (0 for a scalar/void return). `GlobalInfo.Addr`
is the global's raw storage cell.

`pkg0.reflect.accessor` — The compiler emits, for **every** compiled package, one
**immortal static-managed** `Package` descriptor (its management header carries
the immortal sentinel of §18.2, so acquiring/releasing it is a no-op and it is
never freed) and a synthesized accessor

```
func __Package() @reflect.Package
```

that returns it. The accessor is **not** declared in any `.bni`; the compiler
**force-loads** `reflect` for every package so the accessor exists even where
`reflect` is not explicitly imported. The descriptor's byte layout is a
**language-level contract** that every backend (general code generator and direct
native back-ends) **and** the interpreter encode identically (§7.13, §19.3).

`pkg0.reflect.scope` _(Draft)_ — What is introspectable **today** is exactly the
**function** and **global** binding tables above (the surface whose primary
consumer is **dual-mode interop**, not user-facing reflection). **Not** yet
present: types, fields, methods, impls, consts, and imports — richer **type
metadata** (a `TypeInfo` surface) is a **later phase**, and its opt-in granularity
(per-build flag, per-package, per-type, or always-on) is an **open** design
question. Pure-C **extern** functions are **not** introspectable (the descriptor
emitter skips them).

`pkg0.reflect.vm-gap` — Under the **bytecode VM**, the `__Package()` accessor is
reached only for a small fixed set of **built-in** packages (bound through
hardcoded externs); a user or standard-library package compiled to bytecode has
**no** native `__Package` symbol, so its `__Package()` is currently unavailable
under the interpreter. This is a **tracked, deferred** interpreter-backend defect
(Annex C, `claude-todo.md`): the conformance tests that pin `__Package().Name` ==
import path pass on the **compiled** modes and are **xfailed** on the VM modes.
The proper fix emits each package's `__Package()` and its descriptor as **bytecode**
(the VM equivalent of the compiled descriptor) rather than as hardcoded externs.

## 20.4 `pkg/builtins/testing` — testing support

> _Provisional — minimal by design; needs refinement._

`pkg0.testing.testresult` — `pkg/builtins/testing` declares exactly **one** type
and nothing else:

```
type TestResult = @[]char
```

A test **passes** by returning the **empty** managed-slice and **fails** by
returning a **non-empty** one whose contents are the **failure message**. The
result is a **managed-slice** (`@[]char`) because a failure message is typically
freshly allocated and owned by the test.

`pkg0.testing.testfunc` — A **test function** is recognized — identically by both
test runners — by **four** predicates: it is a function **with a body**; its name
has the prefix **`Test`**; it takes **zero** parameters; and it returns exactly
one result of type `testing.TestResult` (accepted spellings: the qualified
`testing.TestResult`, the bare `@[]char` shape, or — within the `testing` package's
own test file — an unqualified local alias resolving to `@[]char`). There is **no**
`T`-style parameter and **no** sub-tests. Matching functions are discovered
automatically; a `--run <substr>` plain-substring filter (and, under the VM,
`--skip <substr>`) selects which run.

`pkg0.testing.files` — Test functions live in **`*_test.bn`** files **alongside**
the package's ordinary `.bn` files under the **same** `package` clause (so they
may use unexported helpers). A `*_test.bn` file is **excluded** from a normal
build and enters a package **only** when that package is an explicit `--test`
target. The file-name reservation itself is normatively §16.1 (`pkg.files.test`);
this section specifies the **package surface** the convention uses.

`pkg0.testing.run` — Pass/fail is signaled **by the returned string**, never by a
panic: there is **no** panic/recover machinery to unwind (consistent with
errors-as-values, §14.14), which is what lets the convention work **identically**
in both modes. The compiled runner (`cmd/bnc --test`) generates a synthetic
`main` that imports the test packages, calls each discovered test, prints Go-style
`=== RUN` / `--- PASS` / `--- FAIL` lines and an `ok`/`FAIL` summary, and is then
linked and run as an ordinary program; the VM runner (`cmd/bni --test`) runs the
tests **in-process** in the bytecode VM, calling each test by its fully-qualified
name. Both read the returned `@[]char` and branch on `len(result) > 0`.

> _Note (known gaps, informative)._ A `Test`-prefixed function with the **wrong**
> signature is **silently skipped**, not diagnosed (the design notes' "warning"
> is not implemented, and is in any case in tension with the compiler's
> errors-only/no-warnings stance — any such diagnostic would be a test-runner
> advisory, not a build warning). The two runners' discovery predicates have
> **drifted** (the VM runner does not resolve an unqualified local `TestResult`
> alias), and `--skip` is honored only by the VM-based runners. These are
> Provisional-status rough edges to be reconciled (Annex C).

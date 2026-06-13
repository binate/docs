# 11. Interfaces, impl, and Self

> **Status:** mixed · **Maturity:** language rules Stable; implementation-conformance mixed (the CRITICAL dispatch defects are resolved; a MAJOR alias-receiver hold (§11.3) and the 32-bit-ARM platform gap (§11.11) remain)  
> **Rule-ID prefix:** `iface`

Binate interfaces are **nominal**: a type satisfies an interface only through an
explicit, separate `impl` declaration — there is no structural/duck typing. This
chapter covers interface declarations (§11.1), interface values (§11.2), `impl`
and satisfaction (§11.3), constructing an interface value (§11.4), `any`
(§11.5), interface extension (§11.6), aliases (§11.7), cross-package rules
(§11.8), the `Self` type (§11.9), the primitive-impl carve-out (§11.10), and
dynamic dispatch (§11.11).

## 11.1 Interface declarations

`iface.decl` — An interface is declared at **package scope** as `interface Name
{ method-signatures }`. There is **no** `type X interface { … }` form and **no**
anonymous interface type. Each element is a method **signature** — a name and a
`Signature` (§10), with no receiver and no body; method names must be unique. A
signature's parameter and result types may reference the interface being
declared and may use `Self` (§11.9). An empty body is allowed (§11.5).

```
InterfaceDecl    = "interface" identifier [ TypeParams ] [ ":" InterfaceList ] "{" { MethodSig ";" } "}"
                 | "interface" identifier "=" InterfaceName ;   (* alias — §11.7 *)
MethodSig        = identifier Signature ;
```

## 11.2 Interface values

`iface.value.spelling` — An interface used as a **value** is written `*Iface`
(raw) or `@Iface` (managed); a **bare interface name is not a usable value type**
(`var s Iface` is an error directing to `*Iface`/`@Iface`). A bare interface name
appears only in an interface-value type, an `impl` clause, an alias, or an
extension clause (§7.10).

`iface.value.repr` — Both forms are **two words** `{data, vtable}` (§7.13
`type.layout.iface-value`); the managed `@Iface`'s data pointer is
reference-counted (it needs destruction). Interface-value type identity is
**nominal** — two interface-value types agree iff they wrap the same interface
(same package and name) and have the same kind.

`iface.value.no-readonly-slot` — There is no inner `readonly` slot on an
interface value (no `*readonly Iface`). An outer `readonly @Iface` / `readonly
*Iface` is a read-only **handle** view of the whole value (the ordinary
`readonly` modifier wrapping the value type; §7.11); read-only **dispatch** is
expressed through `readonly` receivers in the impl (§11.3). A pointer *to* an
interface value (`@(*Iface)`, etc.) follows ordinary pointer rules.

## 11.3 `impl` declarations and nominal satisfaction

`iface.impl.form` — An `impl` declaration is `impl R : I, J, …` — the keyword, a
single receiver type `R`, a colon, and a non-empty comma-separated interface
list. It has **no body** and declares no methods (methods are declared
separately, Go-style); it is a relational assertion that the receiver shape `R`
satisfies each listed interface. `R` may be any of the five receiver shapes
(`T`, `*T`, `*readonly T`, `@T`, `@readonly T`; §10.4) and must reduce to a
**named** type (or, in `pkg/builtins/lang`, a universe primitive; §11.10).

`iface.impl.nominal` _(Constraint)_ — Satisfaction is **nominal and explicit**: a
type satisfies an interface **only** if a matching `impl` is declared. Having all
the right methods is never sufficient on its own — there is no duck typing. (The
sole universal interface is `any`, which needs no impl; §11.5.)

`iface.impl.coverage` _(Constraint)_ — For each listed interface `I`, `R`'s named
type must provide a method of the same name for **every** method in `I`'s full
method set (its own methods plus all inherited from extended parents; §11.6).
The provided method matches iff, after dropping its leading receiver, the
non-receiver parameter and result counts are equal and each type is **identical**
to the interface method's corresponding type with `Self` substituted by `R`'s
named type (§11.9). The impl method's declared receiver kind must be reachable
from `R`'s declared receiver kind by the same safe-direction smoothing as a
method call (§10.5).

> _Open / known gap (MAJOR)._ An `impl` whose receiver is a **type alias** (e.g.
> `type AB = *Box; impl AB : Getter`) is **rejected** ("impl receiver must be (a
> wrapper around) a named type"). This is a deliberate hold, not merely a missing
> peel: peeling the alias so the impl type-checks currently produces a **runtime
> SIGSEGV** at dispatch (the vtable/closure lowering does not peel the alias), so
> rejecting is the safe behavior until that is fixed (`iface.impl.alias-receiver`,
> `claude-todo.md`). A parallel hold applies to **method values** on an alias
> receiver (Ch.10); the two are the same underlying alias-peeling gap, not an
> `impl`-only case.

## 11.4 Constructing an interface value

`iface.construct.no-implicit` — Constructing an interface value from a
non-interface source admits **no implicit conversions** — no implicit copy, no
implicit address-of, no implicit `box`. The source must already be
pointer-shaped (`*T` or `@T`), with any required conversion written explicitly.
(Rationale: an interface value can outlive its source, so the language refuses to
silently capture a reference or copy.) Whether `*T`/`@T` may construct a given
`*Iface`/`@Iface` is **impl-gated** (§11.3).

`iface.construct.managed` — A `@T` constructing a `@Iface` takes its **own**
reference (the interface value's data slot is reference-counted; Ch.18). A `@T`
may instead construct a raw `*Iface` (a borrow — no reference taken). A **raw
`*T` cannot construct a `@Iface`** (it would invent a reference count).

`iface.construct.box` — A **value**-typed source must be made pointer-shaped
first: write `&t` (a `*T` borrow) to construct a `*Iface`, or `box(t)` (which
heap-allocates a managed copy, yielding `@T`; §15) to construct a `@Iface`.

## 11.5 The empty interface `any`

`iface.any` — `any` is the single predeclared **universal** interface (an
interface with empty package and name and no methods). It is used only as `*any`
or `@any` (a two-word interface value, **not** `void*` — the opaque byte pointer
is `*uint8`; §7.8). Bare `any` is rejected as a value type, except in a generic
constraint position, where it means **no constraint** (§12).

`iface.any.universal` — `any` is satisfied by **every** type with **no `impl`
required**, and any interface value upcasts to `*any`/`@any`. A *user-declared*
empty interface (`interface Empty {}`) is, by contrast, a **distinct nominal**
interface that **still requires an explicit `impl`** — zero methods does not mean
"anything fits" (Binate interfaces are nominal, not structural; `iface.impl.nominal`).

## 11.6 Interface extension

`iface.extend` — An interface may **extend** one or more others:
`interface X : P1, P2 { own-methods }`. `X` is a **distinct** interface whose full
method set is the recursive concatenation of each parent's full method set
(preorder, declaration order) followed by `X`'s own methods, deduplicated by
name. The ancestor graph must be acyclic (self-extension is an error), and a
method appearing in two ancestors with **conflicting** signatures is an error
(same-name, same-signature through a common ancestor is allowed — a harmless
diamond). Every interface implicitly extends `any`.

`iface.extend.transitive` — A single `impl R : Child` **transitively** satisfies
all of `Child`'s ancestors: `*R`/`@R` may be used wherever an ancestor interface
value is expected, and ancestor methods dispatch.

`iface.extend.upcast` — A descendant interface value **upcasts** to an ancestor
interface value (`*Child` → `*Parent`, `@Child` → `@Parent`) as a static,
compile-time-known, nominal relation (Binate has no runtime type query). The
upcast preserves the data pointer and adjusts only the vtable pointer to the
ancestor's nested sub-vtable. Upcasting is admitted only when the source
interface is a (transitive) descendant of the target.

## 11.7 Interface aliases

`iface.alias` — `interface X = Y` declares `X` as an **alias** that is the
**same** interface as `Y` (the same interface object, method set, and identity);
`impl T : X` is indistinguishable from `impl T : Y`, and a method dispatches
through either name. This is distinct from `interface X : Y {}` (§11.6), which
declares a **new** interface extending `Y`. A regular `type X = Y` alias may not
name an interface on its right-hand side; `interface X = Y` is the only
interface-aliasing form.

## 11.8 Cross-package interfaces and impl placement

`iface.crosspkg.no-orphan` — There is **no orphan rule**: an `impl R : I` may be
declared in **any** package that has both `R` and `I` in scope — `R`'s package,
`I`'s package, or a third package. Duplicate `impl R : I` declarations across
packages are permitted; each emits a vtable under a canonical name keyed on the
`(R, I)` pair (with `weak_odr` linkage), and the linker keeps one. (This nominal
+ explicit model with vtable deduplication is what stands in for an orphan rule.)

`iface.crosspkg.method-package` _(Constraint)_ — A **method** may be declared
only in the package that defines its receiver's named type ("cannot define
methods on types from other packages"; §7.3). This is independent of where an
`impl` lives — the `impl` may be in any package, but the methods it relies on
must have been declared in `R`'s defining package.

`iface.construct.visible-impl` _(Constraint)_ — At each interface-value
construction site the checker requires a **visible** matching `impl` (in the
current package or transitively imported); otherwise it is a compile error.

## 11.9 The `Self` type

`iface.self` — Within an interface method signature, **`Self`** denotes the
implementing type. It is valid **only** there (in parameter and result types,
including inside composite types such as `*Self`, `@[]Self`, `(Self, Self)`) — not
in the receiver position, not in an extension parent list, and nowhere outside an
interface declaration. At impl time every `Self` is substituted by the
implementing named type, and the impl method's signature must match after
substitution (§11.3).

`iface.self.object-safety` _(Constraint)_ — A method whose interface signature
mentions `Self` in any non-receiver position is **object-unsafe**: it **cannot be
called through an interface value** (a compile error directing to a generic
constraint). `Self`-using methods are a generic-only capability — reachable only
where the concrete type is statically known, so the constraint-method call can
substitute `Self` (§12). An interface value of such an interface may still be
held, stored, and passed; only the `Self`-using method cannot be dispatched
through it.

## 11.10 The primitive-impl carve-out and canonical interfaces

`iface.canonical.carveout` — Exactly one package, **`pkg/builtins/lang`** (§20.1),
may declare methods and impls on the universe primitives (`int`, the sized
integers, `bool`, `float32`, `float64`); no other package may. It provides the
**canonical interfaces**:

| Interface | Methods |
|-----------|---------|
| `Stringer` | `String() @[]char` |
| `Comparable` | `Compare(other Self) int` |
| `Orderable : Comparable` | (adds none — asserts a total order) |
| `Hashable : Comparable` | `Hash() uint` |

Each of the 13 primitive scalar types implements `Stringer`, `Orderable`, and
`Hashable` (and `Comparable` transitively). The table above is the normative
statement of these signatures until §20.1 is authored — §20.1 (`pkg/builtins/lang`)
will become the normative home for the canonical-interface signatures, with this
section naming them and the carve-out. (Verified against
`ifaces/core/pkg/builtins/lang.bni`.)

`iface.canonical.auto-available` — Calling a canonical **method** on a primitive
(`x.String()`, `x.Compare(y)`) requires **no import** — the compiler force-loads
`pkg/builtins/lang` so the impls attach to the primitive types. Naming the
interface **type** (`*lang.Stringer`) still requires importing the package.

> _Open items (§20.1)._ The canonical floating-point `Compare` does not implement
> IEEE total order (NaN compares equal to itself), and `float` `Hash` uses raw
> bits (so distinct NaN bit patterns hash inconsistently with `Compare`-equality).
> Tracked for §20.1.

## 11.11 Dynamic dispatch

`iface.dispatch` — A method called through an interface value is dispatched
**dynamically**: the method's slot is resolved at compile time, and the
implementation is loaded from the value's vtable at run time and called with the
value's data pointer as the receiver. Vtable slot 0 is the type's destructor;
methods occupy the following slots in declaration order. There is no receiver
smoothing on this path (it was validated when the `impl` was declared); a
`readonly` wrapper on the interface value is peeled before dispatch. The
observable result is normative; the vtable layout is informative (Annex B).

`iface.dispatch.nil` — Dispatching a method through a **nil** interface value (one
that was never given a concrete value, so its vtable word is null) is a **defined
non-recoverable abort** — one of the closed set of runtime panics (§17.5). Its
*observable form* is target-dependent: the bytecode VM detects it and aborts with
a diagnostic, while a compiled backend faults on the null-vtable dereference (and
on a target with no memory protection the dereference may not fault at all). Use
`present` (§15.5) to test an interface value before dispatching through it.

> _Implementation-conformance note._ The interface dispatch machinery — including
> **multi-return interface methods** (the idiomatic `(T, @Error)`), transitively
> re-exported interfaces, and sub-word multi-return — was the subject of several
> CRITICAL defects that are now **resolved**: the machinery is mode-agnostic and
> verified XPASS on the dev-host-runnable conformance modes (LLVM, the bytecode VM,
> and the native aarch64/x64 backends). Two residuals remain. (1) The 32-bit
> **ARM** backend has not yet been verified to conform for multi-return / sub-word
> interface dispatch (a separate 32-bit ABI issue, not runnable on the dev host;
> `conformance/matrix/abi/iface-multi-return/*/*.xfail.builder-comp_arm32_*`). (2)
> The transitive-re-export test is additionally blocked on the `builder-comp-int-int`
> mode by an **unrelated** multi-package double-interpretation crash — not an
> interface-dispatch defect (`conformance/665_transitive_iface_reexport.xfail.builder-comp-int-int`).
> The language rules above are Stable; these are platform/mode-conformance gaps
> (tracked in `claude-todo.md`; to be recorded in Annex C once that ledger is
> authored).

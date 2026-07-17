# 11. Interfaces, impl, and Self

> **Status:** mixed · **Maturity:** language rules Stable (except two Draft rules — §11.4 `iface.construct.value-borrow` and §11.12 `iface.assert.slice`, both design-ratified, not yet implemented); implementation-conformance mixed (the CRITICAL dispatch defects are resolved; a MAJOR alias-receiver hold (§11.3), the name-less-box crash (§11.12), and the 32-bit-ARM platform gap (§11.11) remain)  
> **Rule-ID prefix:** `iface`

Binate interfaces are **nominal**: a type satisfies an interface only through an
explicit, separate `impl` declaration — there is no structural/duck typing. This
chapter covers interface declarations (§11.1), interface values (§11.2), `impl`
and satisfaction (§11.3), constructing an interface value (§11.4), `any`
(§11.5), interface extension (§11.6), aliases (§11.7), cross-package rules
(§11.8), the `Self` type (§11.9), the primitive-impl carve-out (§11.10),
dynamic dispatch (§11.11), and type assertions and type switches (§11.12).

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
**named** type (or, in `pkg/builtins/lang`, a universe primitive; §11.10). For a
**generic** type, `R` **binds** the type's parameters and the interface list may
reference them — a **parameterized-receiver impl** (`impl *Cursor[T] :
Iterator[T]`; §12.1 `gen.impl.generic-recv`).

`iface.impl.nominal` _(Constraint)_ — Satisfaction is **nominal and explicit**: a
type satisfies an interface **only** if a matching `impl` is declared. Having all
the right methods is never sufficient on its own — there is no duck typing. (The
sole universal interface is `any`, which needs no impl; §11.5.)

`iface.impl.coverage` _(Constraint)_ — For each listed interface `I`, `R`'s named
type must provide a method of the same name for **every** method in `I`'s full
method set (its own methods plus all inherited from extended parents; §11.6).
The provided method matches iff, after dropping its leading receiver, the
non-receiver parameter and result counts are equal, each type is **identical**
to the interface method's corresponding type with `Self` substituted by `R`'s
named type (§11.9), and both agree on whether the final non-receiver parameter is
**variadic** (§10.3 `func.variadic.identity`). The impl method's declared receiver kind must be reachable
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
non-interface source admits **no implicit copy** and **no implicit `box`**; the
source must be pointer-shaped (`*T` or `@T`), with any required conversion written
explicitly. (Rationale: an interface value can outlive its source, so the language
refuses to silently capture a reference or copy.) Whether `*T`/`@T` may construct a
given `*Iface`/`@Iface` is **impl-gated** (§11.3). The **one** relaxation is an
implicit *address-of* when a **value** source constructs a **raw** `*Iface`
(`iface.construct.value-borrow`, Draft); a **managed** `@Iface` is never
constructed implicitly (the source must be `@T`, or an explicit `box(t)`).

`iface.construct.managed` — A `@T` constructing a `@Iface` takes its **own**
reference (the interface value's data slot is reference-counted; Ch.18). A `@T`
may instead construct a raw `*Iface` (a borrow — no reference taken). A **raw
`*T` cannot construct a `@Iface`** (it would invent a reference count).

`iface.construct.box` — A **value**-typed source must be made pointer-shaped
first: write `&t` (a `*T` borrow) to construct a `*Iface`, or `box(t)` (which
heap-allocates a managed copy, yielding `@T`; §15) to construct a `@Iface`. For a
raw `*Iface`, the `&t` may be left **implicit** in the positions
`iface.construct.value-borrow` (Draft) permits; the `box(t)` for a `@Iface` is
always explicit.

`iface.construct.value-borrow` — A **value**-typed source (not `*T`/`@T`)
constructing a **raw** `*Iface` (including `*any`) is admitted via an **implicit
borrow** — so `fmt.Print("hi", 42)` and `Opts{Any: v}` need no explicit `&`. It
applies only to a genuinely value-typed source; a `*T`/`@T` source is unchanged
(`iface.construct.managed` — a borrow, no reference taken). Two cases:

- An **addressable** source (an lvalue — a variable, field, or element) borrows by
  an implicit **address-of**: `Opts{Any: x}` is exactly `Opts{Any: &x}` — the same
  `*T` borrow, lifetime, and use-after-free contract (§18.7 `mem.raw-uaf`), in
  **any** position an explicit `&x` is permitted.
- A **non-addressable** source (a literal, an expression, or a call result) is
  **materialized into a temporary** and borrowed. Because a temporary is released
  at the **end of its statement** (§18.4 `mem.temporary`), this is permitted
  **only** where the borrow cannot outlive it: an **argument** position, or a
  **`var`/`:=` initializer** (the temporary co-scopes with the new binding). In a
  position that stores into a **pre-existing** location outliving the statement — an
  **assignment**, a **field or element store**, or a **`return`** — it is a
  **compile error** (a stack temporary would dangle at the statement's end); such a
  store must name a longer-lived source, or `box(t)` for a heap copy.

Construction **borrows; it does not copy** (unlike Go's interface conversion): a
stored raw interface value observes later mutations of its source and — being a raw
borrow — dangles if it outlives that source (§18.7). A **managed** `@Iface` from a
value is **never** implicit; it requires explicit `box(t)` (`iface.construct.box`),
since an implicit managed box would be a hidden heap allocation.

> _Draft — ratified, not yet implemented (`proposal-implicit-any-borrow`)._ The
> enabling "boxing" half of the `...*any` `fmt` direction (`builtin.print`, §15.7);
> its dual is the slice/scalar **recovery** in a type switch (§11.12
> `iface.assert.slice`). Because the implicit lvalue borrow carries **no visible
> `&`**, an escaping raw interface value built from a local is a use-after-free that
> reads like value construction — a `bnlint` rule should flag it (the compiler emits
> no such diagnostic; unused/dangling detection is a lint concern, not a compiler
> one).

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
compile-time-known, nominal relation (the **upcast** needs no runtime query; the
opposite **downcast** direction — narrowing a value back to a descendant
interface or a concrete type — is a runtime **type assertion**, §11.12). The
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

> _§20.1._ The canonical floating-point `Compare` implements the IEEE total order
> — every `NaN` sorts above `+Inf` and all `NaN` compare equal, and `-0.0 < +0.0`
> — and `float` `Hash` canonicalizes `NaN`, so it is consistent with
> `Compare`-equality.

## 11.11 Dynamic dispatch

`iface.dispatch` — A method called through an interface value is dispatched
**dynamically**: the method's slot is resolved at compile time, and the
implementation is loaded from the value's vtable at run time and called with the
value's data pointer as the receiver. The vtable's offset-0 **any-block** holds
the type's destructor and its `*TypeInfo` (§7.13.8, §7.13.14 `type.layout.typeinfo`);
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

## 11.12 Type assertions and type switches

A **type assertion** recovers a concrete type — or a narrower interface — from an
interface value at run time (the **downcast** direction; the static upcast is
§11.6 `iface.extend.upcast`). Binate stays **nominally and openly** typed: no sum
types, no exhaustiveness checking; an assertion is an **explicit, opt-in** runtime
query, not an implicit one.

`iface.assert` — A **type assertion** applies to an interface-value operand `x`
(`*I`/`@I`, including `*any`/`@any`; asserting a non-interface value is an error)
and names a target — either a **nameable** type with a mandatory recovery kind, or
a **slice** type (`iface.assert.kind`, `iface.assert.slice`; a func / array /
struct / `Self` target is a compile error). The **dynamic type** of `x` is the concrete named type recorded when `x`
was constructed (§11.4): the boxed value's type with its `*`/`@`/outer-`readonly`
stripped and aliases peeled, but **named-distinct wrappers preserved** (a boxed
`Celsius` records `Celsius`, not `float64`; §7.3). A target matches as follows:
- **Concrete target** `T`: succeeds iff `x`'s dynamic type is **exactly** `T` —
  nominal type identity, not assignability (a stored `Celsius` matches `.(Celsius)`
  and **not** `.(float64)`). Each generic instantiation is a distinct type with its
  own identity (`List[int]` ≠ `List[float]`; §12). The match is on the base type,
  independent of the recovery kind and of any `readonly`.
- **Interface target** `J`: succeeds iff `x`'s dynamic type **satisfies** `J` — it
  has a visible `impl … : J`, **or** an `impl` for any (transitive) **descendant**
  of `J`, since a descendant impl transitively satisfies its ancestors
  (`iface.impl.nominal`, `iface.extend.transitive`). Recovers a `*J`/`@J`. `any` is
  satisfied by every present `x`.

The two syntactic forms differ only in how a **miss** is handled:
- As an **expression**, `x.(K T)` yields the recovered value; a miss is a
  **non-recoverable abort** (a defined runtime panic, §17.5). Binate has no
  `recover`, so — unlike Go's catchable panic — this ends the program; use it only
  where the type is a guaranteed invariant.
- In a **two-target** short declaration or assignment, `v, ok := x.(K T)` is the
  **comma-ok** form — the single assertion expression yields **two** values,
  reusing the multi-value-RHS machinery of a two-result call: a miss sets
  `ok = false` and leaves `v` the zero/unset value, and never aborts. This is the
  errors-as-values form and the one to prefer.

`iface.assert.kind` _(Constraint)_ — The recovery kind (`@`, `*`, or a bare value)
is **mandatory** in every assertion and type-switch case, and its legality follows
the managed→raw ownership direction (§7.6 `type.slice.ownership` /
`type.slice.decay`: you may borrow from anything but may never fabricate a
reference count):

| `x` is | `x.(@T)` | `x.(*T)` | `x.(T)` (value copy) |
|--------|----------|----------|----------------------|
| `@I`   | ✓ retain (RefInc) | ✓ borrow (no refcount churn) | ✓ copy out |
| `*I`   | ✗ (no reference to share) | ✓ borrow | ✓ copy out |

The same table governs interface targets (`@J`/`*J`). Recovering `*T` from a `@I`
is a **borrow** with no refcount traffic — the intended low-churn path — valid
only for the **lifetime of the box** it was taken from (bounded by `x`'s own
reference for a `@I`, or by whatever keeps the referent alive for a `*I`); using it
after that is a use-after-free (§18.7 `mem.raw-uaf`). A `@`-recovery from a raw
`*I` is rejected at compile time. A **value** recovery (`x.(T)`) copies the pointee
out field-wise, acquiring any managed fields (Axiom 3, §18.3 `mem.copy`); a value
recovery from a **typed-nil** box (`iface.assert.absent`) would dereference a nil
pointer, so use a `*T`/`@T` recovery plus `present` to inspect a possibly-nil box.
On the recovered handle, **element-level** `readonly` may be **added** but not
**dropped** (a one-way capability, §7.11 `type.readonly.lattice-element`); an
outer/handle `readonly` is freely choosable.

`iface.assert.slice` — A **slice** type is admitted as an assertion /
type-switch target — `x.(*[]char)`, `case @[]readonly char:` — even though a slice
is unnamed. It is the **one** composite target admitted; a func / array / struct /
`Self` target stays a compile error (`iface.assert`). A slice
target matches by **structural identity**: the identity of a slice type is the
tuple `{ managed | raw, element-readonly?, element-type }`, applied **recursively**
to the element (so `@[]@[]char` is distinct from `@[]char`). Thus `@[]char`,
`*[]char`, `@[]readonly char`, and `*[]readonly char` are **four distinct**
identities, and a box of one matches **only** its own spelling. The match is
**exact**, not by assignability: a `@[]char` box does **not** match `case
@[]readonly char:` (adding element-`readonly` is an implicit *conversion*, §8.3,
not a change of the boxed value's dynamic type), exactly as a stored `Celsius`
does not match `.(float64)`. Because a slice value is multi-word — a raw slice 2
words (`type.layout.slice-raw`), a managed-slice 4 (`type.layout.slice-managed`) —
it cannot occupy the one-word interface `data` slot (§7.13.8): a slice is boxed as
a **pointer to its header**, and recovery reads that pointer and copies the slice
out **by value** (acquiring a managed-slice's backing per Axiom 3, `mem.copy`). The
managed/raw distinction is therefore carried by the **slice type spelling itself**
— the leading `@`/`*` on a slice target is the slice's own managed/raw marker, not
a separate recovery-kind prefix, and a slice target's recovery is always by value.
The `TypeInfo` backing a slice's structural identity reuses the ordinary record
layout (§7.13.14 `type.layout.typeinfo`), its **name** field carrying the
structural spelling and its **destructor** the slice's element-drop.

> _Draft — ratified, not yet implemented._ The **design** of `iface.assert.slice`
> is **ratified** (`proposal-slice-type-identity`): both the **exact-match**
> identity — element-`readonly` and managed-vs-raw are *distinct* (the sound choice;
> collapsing them would silently drop/add `readonly` or confuse the 2-word/4-word
> representations) — and the **grammar** are settled, and the `AssertTarget`
> production (§11.12 grammar; canonical `binate.ebnf`) now carries the slice-type
> alternative. The rule is **Draft** on the stability axis (§4.4) only because it is
> **not yet implemented** — Axis-2 non-conformant, tracked by
> `explorations/plan-slice-type-identity.md` and gated behind the name-less-box
> crash fix (Annex C / `claude-todo.md`). The enabling use is fmt's `...*any`
> fast-path (`builtin.print`, §15.7; `claude-notes.md:252`): a string is a raw
> char-slice, so recovering a string operand needs a slice target. Because the four
> string spellings are distinct identities, a formatter enumerates one `case` per
> spelling it accepts — a library concern, not a language one.

`iface.assert.absent` — An interface value has two "empty" states (§15.5
`builtin.present`), and neither is a `nil` case — interface values are **not
nil-comparable** (§13.6 `expr.compare.incomparable`):
- **unset** (`present(x)` is `false`; the **vtable** word — word 1, §7.13.8 — was
  never filled, so there is no vtable and hence no reachable `*TypeInfo`): it has
  **no dynamic type**. An assertion tests the **vtable word first**; a null vtable
  short-circuits to a miss (comma-ok → `ok = false`; the expression form aborts)
  and a type switch runs the `default`. Only a **non-null** vtable is then
  dereferenced to read the any-block `*TypeInfo` (matching `iface.dispatch.nil`).
- **typed-nil** (`present(x)` is `true`; a nil pointer was boxed, so the dynamic
  type *is* set): it **has** a dynamic type and matches that type normally,
  recovering a value whose data is nil (Go's typed-nil; the caller re-tests with
  `present`).

There is **no `case nil`** and no `x == nil`; absence is a `present(x)` concern —
guard with `present` before or around a switch to handle the unset case
distinctly from an unlisted type.

`iface.typeswitch` — A **type switch** dispatches on the **dynamic type** of an
interface value:

```
SwitchStmt     = … | "switch" [ identifier ":=" ] PostfixExpr "." "(" "type" ")"
                   "{" { TypeCaseClause } "}" ;
TypeCaseClause = ( "case" AssertTargetList | "default" ) ":" { Statement ";" } ;
AssertTarget   = ( [ "*" | "@" ] [ "readonly" ] TypeName )   (* nameable-type target *)
               | ( ( "*" | "@" ) "[" "]" Type ) ;            (* slice-type target — iface.assert.slice *)
```

Each `case` lists one or more **assert targets** (`iface.assert.kind` — a recovery
kind plus a nameable type, or a slice type, `iface.assert.slice`), each legal for
the scrutinee (a `*I` switch admits no `@T` case). A concrete-type case matches by
exact dynamic-type identity (a slice case by structural identity); an
interface-type case matches by satisfaction — the same criteria as `iface.assert`.
The **first** matching case runs; there is **no fallthrough** and no duplicate-case
check (§14.10 `stmt.switch.no-fallthrough`). Because interface cases can **overlap**
(a type may satisfy several) and the first match wins, order cases
**most-specific first**; no reachability diagnostic is performed. `default` runs
when none matches and also catches an **unset** scrutinee (`iface.assert.absent`).
An optional `v :=` binds the recovered value **per case**: in a single-target case
`v` has that case's type and kind; in a **multi-target** case (`case @A, @B:`) or
the `default`, `v` keeps the scrutinee's interface type (as in Go). Without a
binder the switch is a pure dispatch. There is **no `case nil`**.

`iface.rtti` — Every interface value can recover its dynamic type at run time
through a per-type **`TypeInfo`** record reached from the vtable — the `TypeInfo`
pointer lives in the vtable's offset-0 "any-block" alongside the destructor
(layout §7.13.14 `type.layout.typeinfo`). A **concrete** assertion compares the
scrutinee's `TypeInfo` against the target type's (an identity test). An
**interface** assertion `x.(K J)` instead consults the **distributed satisfaction
registry** (§7.13.14 `type.layout.satisfaction`), keyed on `(dynamic-type, J)`, and
on a hit forms `{data, vtable(T, J)}`. It is **not** a per-type table inside
`TypeInfo`: because `impl` may live in any package (no orphan rule, §11.8
`iface.crosspkg.no-orphan`), no single translation unit sees a type's complete impl
set, so satisfaction entries are emitted **per `impl` site** — one for the impl'd
interface and each of its transitive ancestors (`iface.extend.transitive`) — and
`weak_odr`-deduplicated like the vtables they reference. Type **identity** is a
per-type token whose observable **equality result** — not any particular address —
is the normative, cross-mode-agreeing quantity (`conf.cross-mode.scope`, §2.4):
each engine compares its own `TypeInfo` (pointer-equality *within* a mode, like
vtable/function-value handles, §19.4), and both the identity test and the registry
lookup yield the same result in compiled and interpreted execution. The observable
result is normative; the record/registry layout is informative (Annex B), and the
`TypeInfo` is the record a future **reflection** type-metadata surface is intended
to expose (§20.3, a later phase).

> _Implemented._ Type assertions (`x.(K T)` and the comma-ok form), type switches,
> and the `TypeInfo` RTTI record are implemented and conformance-green in every
> execution mode — the `iface.assert*` / `iface.typeswitch` / `iface.rtti` rules
> and `type.layout.typeinfo`, including the cross-mode agreement of every
> assertion result (a value produced by a compiled package and asserted in the
> bytecode VM resolves to the same result). **Two exceptions:** `iface.assert.slice`
> is Draft — its design is ratified but it is **not yet implemented** (see its
> note); and boxing a **name-less** dynamic type (such as a slice) into `any`
> currently emits a malformed box, so a match over it crashes instead of falling to
> `default` — a tracked MAJOR non-conformance (§7.13.14 name-less-types note; Annex
> C / `claude-todo.md`) whose fix is independent of, and forward-compatible with,
> the slice extension.

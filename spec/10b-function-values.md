# 10.8–10.12 Function Values, Closures, and Method Values

> **Status:** mixed · **Maturity:** Provisional (recently landed)  
> **Rule-ID prefix:** `func`  
> Part of Ch.10 ([Functions, Methods, and Function Values](10-functions-methods-function-values.md)).

A **function value** is a callable value: a `*func`/`@func` carrying a function
(possibly with captured state). This block specifies function-value types and
representation (§10.8), non-capturing literals and function references (§10.9),
closures (§10.10), method expressions and method values (§10.11), and equality,
indirect calls, and dual-mode dispatch (§10.12). The whole feature is **recent
and Provisional**; known implementation gaps are flagged inline.

## 10.8 Function-value types

`func.value.spelling` — A function-value type is written `*func(P…) R` (raw) or
`@func(P…) R` (managed). Parameters are types only (no names); a single result
is bare, multiple results parenthesized. A bare `func(…)` is **not** a usable
type — the `*`/`@` prefix is mandatory (paralleling `*[]T`/`@[]T` and
`*Iface`/`@Iface`).

`func.value.repr` — A function value of either kind is **two words**
`{vtable, data}` (§7.13 `type.layout.func-value`): the vtable is a `{dtor, call}`
record (slot 0 destructor — null when nothing to destruct; slot 1 the call
shim), and the data word points at the closure record (null for a non-capturing
value). The concrete shim/trampoline mechanics are in Annex B.

`func.value.identity` — Two function-value types are identical iff they have the
**same kind** (raw vs managed — `*func(…)` and `@func(…)` are never identical)
and structurally identical signatures (equal parameter and result counts,
pairwise-identical types; names ignored).

`func.value.smoothing` — A managed `@func(S)` is implicitly convertible to a raw
`*func(S)` of identical signature — a refcount-neutral **borrow** (the `*func`
borrows the `@func`'s record, owning nothing; §8.4). The reverse `*func → @func`
is **never** implicit.

`func.value.nillable` — Both function-value kinds are **nillable for assignment**
(a nil function value is both words zero; it is the default for a function-value
variable). A managed `@func` needs destruction; a raw `*func` does not. (Nil-ness
is not testable with `==`/`!=`; use `present` — §10.12.)

`func.value.named-nominal` — Named function-value types are **nominal** (§7.3):
a value of one function-value type does not implicitly assign into a distinct
named function-value type. A named function-value type is constructed from a
function *reference* (§10.9) — **not** from a method expression, nor by assigning
an already-bound `*func`/`@func` value (both are of function-value kind, which
this nominal rule rejects). (Construction from a function *literal* is intended
but not yet implemented — §10.9.)

## 10.9 Non-capturing function literals and function references

`func.ref.decay` — A reference to a named top-level function decays to a function
value of matching signature, assignable to a `*func` or `@func` destination —
including a **named** function-value type (`var f Fn = add`). The destination's
alias/named/`readonly` wrappers are peeled for the match; parameter names are
ignored.

`func.lit.noncapturing` — A function literal `func(P…) R { … }` in expression
position evaluates to a function value. A **non-capturing** literal (one that
references no enclosing local) carries a null data word and works in all
execution modes.

`func.lit.inferred-default` — Where no destination type is supplied, a function
literal's (and a bare function reference's) default type is the **managed**
`@func(…)`, mirroring the `@[]T` default. A destination that hints a `*func` slot
of matching signature pins the literal to the raw `*func` form (a stack-allocated
closure borrowed by the destination; §10.10).

> _Known gap._ Constructing a **named** function-value type from a function
> *literal* (`var f Fn = func(…){…}`) is rejected in all modes; only the function
> *reference* form (`var f Fn = add`) works (§7.3, `claude-todo.md`).

## 10.10 Closures

`func.closure.capture` — A function literal that references an enclosing local is
a **closure**. Capture is **always by value** — a snapshot taken when the literal
is evaluated. There are no capture lists; captured variables are inferred by
free-variable analysis. Writes to a captured name inside the body affect only the
closure's copy, and later writes to the original variable are not visible to the
closure. **Shared mutable state is expressed by capturing a pointer** (the
pointer is snapshotted; the pointee is shared).

`func.closure.captured` — Only ordinary local variables are captured. References
to package-level functions, constants, types, packages, and interfaces are not
captured (they are static entities). A captured managed value (`@T`, `@[]T`,
`@func`) acquires its own reference, released when the closure is destroyed.

`func.closure.allocation` — A capturing **`*func`** literal stack-allocates its
closure record in the enclosing frame (lifetime tied to that frame); a capturing
**`@func`** literal heap-allocates it (reference-counted). `*func` does **not**
auto-promote to `@func` — a closure that must outlive its frame shall be typed
`@func` directly.

`func.closure.escape-lint` — Escape of a stack-bound capturing `*func` is a
**lint warning** (`func-value-escape`), not a hard type error: `*func` is an
opt-in escape hatch whose lifetime is the programmer's responsibility, and the
warning steers toward `@func`. Detection is best-effort (it covers `return`,
file-scope initializers, and assignment through a pointer-/managed-rooted
destination, not every escape path). Separately, an `@func` literal
that captures a **raw pointer** is flagged `managed-func-raw-capture` (the
`@func` can outlive the raw pointer's source).

`func.closure.recursion` — A recursive **anonymous** closure is unsupported:
because capture is by value, a closure that refers to its own binding would
snapshot a pre-binding (nil/stale) value. The single-binding forms
(`var g = func(){…g…}`, `g := func(){…g…}`) are hard compile errors (`g` is not
in scope within its own initializer); the reassignment form
(`g = func(){…g…}`) is flagged by the lint warning `recursive-closure-capture`.
The idiom for recursion is a named top-level function.

## 10.11 Method expressions and method values

`func.method-expr` — A **method expression** `T.M` (`T` a named type — including
a named-distinct scalar such as `type Celsius int` — with method `M`) is a
function value whose signature is `M`'s **full** signature *including* the
receiver as the first parameter (in `M`'s declared receiver kind). Its type is a
raw `*func(recv, args…) results`. It is a non-capturing function reference.

`func.method-value` — A **method value** `x.M` (`x` a value whose base type has
method `M`, with no same-named field — fields take precedence) is a function
value whose signature is `M`'s signature **minus** the receiver, which is
captured at the selector site. Its type is a raw `*func(args…) results` (even when
the captured receiver is managed). The receiver base is the type **as written**
(a named-distinct type uses its own method set; §7.3).

`func.method-value.capture` — The receiver is captured in the form `M` declares,
bridging `x`'s shape to `M`'s receiver shape: a value receiver captures a copy; a
`*T` receiver captures `&x` (mutations visible); a `@T` receiver captures the
managed pointer (reference-counted). Capturing a value receiver via the managed/
raw form takes a snapshot.

## 10.12 Equality, indirect calls, and dual-mode dispatch

`func.value.equality` — Function values **cannot be compared** with `==` or `!=`
against anything, **including `nil`** (this differs from pointers, where
`p == nil` is allowed). Test a function value's presence with `present(fv)`
(§15) — the same idiom slices use (§7.6).

`func.value.indirect-call` — Calling **through** a function value invokes the
function it holds; the callee signature comes from the function-value type. An
indirect call is reached when the callee is a function-value-typed variable,
field, or element (routed ahead of method dispatch; §10.7). (Lowering: Annex B.)

`func.value.dual-mode` — An indirect call through a function value is
**mode-transparent**: the same call site dispatches correctly whether the target
is compiled or interpreted code, in either direction, through the value's call
shim. This is the mechanism by which compiled and interpreted code call each
other (Ch.19); a function value carries its own interpreter handle inline.

> _Implementation-conformance gaps (Annex C)._ The function-value feature has
> known backend-specific gaps that do not change the language rules: a VM-mediated
> indirect call is currently limited to 7 argument words, and capturing closures /
> method values with certain floating-point return or register-overflow shapes
> fail on the native backends. These are tracked, test-pinned defects
> (`claude-todo.md`), not design holes.
